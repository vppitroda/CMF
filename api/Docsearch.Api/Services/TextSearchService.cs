using Dapper;
using Docsearch.Api.Contracts;
using Docsearch.Api.Infrastructure;
using Npgsql;

namespace Docsearch.Api.Services;

public class TextSearchService(NpgsqlDataSource db) : ITextSearchService
{
    // trigram word-similarity needed for a typo'd hit; an exact substring always scores 1.0
    private const double MinSimilarity = 0.5;
    // a part number off by a character is a different part: such near-misses must rank well below real matches
    private const double MinPartNoSimilarity = 0.5;

    private class Row
    {
        public long DocumentId { get; set; }
        public string FileName { get; set; } = "";
        public string RelPath { get; set; } = "";
        public string Category { get; set; } = "";
        public string? ProjectCode { get; set; }
        public string? Revision { get; set; }
        public bool IsLatest { get; set; }
        public string? Application { get; set; }
        public string Kind { get; set; } = "";
        public string Label { get; set; } = "";
        public string MatchedText { get; set; } = "";
        public double Score { get; set; }
        public int MatchCount { get; set; }
        public string? PropKey { get; set; }
        public int? Page { get; set; }
        public string? Bbox { get; set; }
    }

    // Each source yields (document, kind, label, text, score, page, bbox); the best hit per document wins.
    // @ql = lowercased query, @qc = canonical query (as value_canon), @pn = part-number key (null unless the query looks like one).
    private const string Sql = @"
WITH hits AS (
  SELECT b.document_id, 'PartNo'::text AS kind, 'Part no.'::text AS label, b.part_no AS matched_text, NULL::text AS prop_key,
         (CASE WHEN b.part_no_canon = @pn THEN 1.0 WHEN strpos(b.part_no_canon, @pn) > 0 THEN 0.9
               ELSE similarity(b.part_no_canon, @pn) END)::float8 AS score,
         b.page, b.bbox::text AS bbox, 1 AS prio
  FROM bom_lines b
  WHERE @pn::text IS NOT NULL AND b.part_no_canon IS NOT NULL
    AND (strpos(b.part_no_canon, @pn) > 0 OR similarity(b.part_no_canon, @pn) >= @minPn)
  UNION ALL
  SELECT b.document_id, 'BomLine', 'BOM line', concat_ws('  ', b.item_no, b.part_no, b.description), NULL,
         (CASE WHEN strpos(lower(b.description), @ql) > 0 THEN 1.0 ELSE word_similarity(@ql, lower(b.description)) END)::float8,
         b.page, b.bbox::text, 3
  FROM bom_lines b
  WHERE b.description IS NOT NULL AND (strpos(lower(b.description), @ql) > 0 OR word_similarity(@ql, lower(b.description)) >= @min)
  UNION ALL
  SELECT f.document_id, 'Spec', coalesce(p.label, f.prop_key), f.value_text, f.prop_key,
         (CASE WHEN strpos(f.value_canon, @qc) > 0 THEN 1.0 ELSE word_similarity(@qc, f.value_canon) END)::float8,
         f.page, f.bbox::text, 2
  FROM spec_fields f
  JOIN documents d0 ON d0.id = f.document_id
  LEFT JOIN properties p ON p.category = d0.category AND p.prop_key = f.prop_key
  WHERE strpos(f.value_canon, @qc) > 0 OR word_similarity(@qc, f.value_canon) >= @min
  UNION ALL
  SELECT n.document_id, 'Note', 'Note ' || coalesce(n.no, ''), n.text, NULL,
         (CASE WHEN strpos(lower(n.text), @ql) > 0 THEN 1.0 ELSE word_similarity(@ql, lower(n.text)) END)::float8,
         n.page, NULL, 4
  FROM notes n
  WHERE strpos(lower(n.text), @ql) > 0 OR word_similarity(@ql, lower(n.text)) >= @min
  UNION ALL
  SELECT d1.id, 'FileName', 'File name', d1.file_name, NULL,
         (CASE WHEN strpos(lower(d1.file_name), @ql) > 0 THEN 1.0 ELSE word_similarity(@ql, lower(d1.file_name)) END)::float8,
         NULL::int, NULL::text, 5
  FROM documents d1
  WHERE strpos(lower(d1.file_name), @ql) > 0 OR word_similarity(@ql, lower(d1.file_name)) >= @min
), ranked AS (
  SELECT h.*, d.file_name, d.rel_path, d.category, d.project_code, d.revision, d.is_latest, d.application, d.rev_rank,
         row_number() OVER (PARTITION BY h.document_id ORDER BY h.score DESC, h.prio) AS rn,
         count(*) OVER (PARTITION BY h.document_id) AS match_count
  FROM hits h
  JOIN documents d ON d.id = h.document_id
  WHERE d.duplicate_of IS NULL AND (@includeOld OR d.is_latest) AND (@category::text IS NULL OR d.category = @category)
)
SELECT document_id, file_name, rel_path, category, project_code, revision, is_latest, application,
       kind, label, matched_text, score, match_count::int AS match_count, prop_key, page, bbox
FROM ranked
WHERE rn = 1
ORDER BY score DESC, prio, is_latest DESC, rev_rank DESC, file_name
LIMIT @limit";

    public async Task<TextSearchResponse> SearchAsync(TextSearchRequest req, CancellationToken ct)
    {
        var q = (req.Q ?? "").Trim();
        if (q.Length < 3) throw ApiException.BadRequest("'q' needs at least 3 characters.");
        var limit = Math.Clamp(req.Limit, 1, 100);

        await using var conn = await db.OpenConnectionAsync(ct);
        var rows = (await conn.QueryAsync<Row>(new CommandDefinition(Sql, new
        {
            ql = string.Join(' ', q.ToLowerInvariant().Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries)),
            qc = Canonicalizer.Canon(q),
            pn = Canonicalizer.AsPartNo(q),
            min = MinSimilarity,
            minPn = MinPartNoSimilarity,
            includeOld = req.IncludeOld,
            category = string.IsNullOrWhiteSpace(req.Category) ? null : req.Category,
            limit,
        }, cancellationToken: ct))).ToList();

        var siblings = await SqlHelpers.GetSiblingsAsync(conn, rows.Select(r => r.DocumentId).ToList(), ct);
        return new TextSearchResponse(rows.Select(r => new TextSearchResultDto(
            r.DocumentId, r.FileName, r.RelPath, r.Category, CategoryLabels.For(r.Category), r.ProjectCode, r.Revision,
            r.IsLatest, r.Application, Enum.Parse<MatchKind>(r.Kind), r.Label, r.MatchedText, Math.Round(r.Score, 3),
            r.MatchCount, r.PropKey, r.Page, SqlHelpers.ParseBbox(r.Bbox), siblings[r.DocumentId].ToList())).ToList());
    }
}
