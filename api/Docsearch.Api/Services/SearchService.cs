using System.Globalization;
using Dapper;
using Docsearch.Api.Contracts;
using Docsearch.Api.Infrastructure;
using Npgsql;

namespace Docsearch.Api.Services;

public class SearchService(NpgsqlDataSource db) : ISearchService
{
    private class ResultRow
    {
        public long DocumentId { get; set; }
        public string FileName { get; set; } = "";
        public string RelPath { get; set; } = "";
        public string? ProjectCode { get; set; }
        public string? Revision { get; set; }
        public bool IsLatest { get; set; }
        public string? Application { get; set; }
        public string MatchedValue { get; set; } = "";
        public int? Page { get; set; }
        public string? Bbox { get; set; }
        public decimal? MatchedNumber { get; set; }
        public decimal? Delta { get; set; }
        public double? Similarity { get; set; }
    }

    private class ReusedRow { public long DocumentId { get; set; } public string ValueText { get; set; } = ""; }

    private const string Select = @"SELECT d.id AS document_id, d.file_name, d.rel_path, d.project_code, d.revision,
        d.is_latest, d.application, f.value_text AS matched_value, f.page, f.bbox::text AS bbox";

    public async Task<SearchResponse> SearchAsync(SearchRequest req, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(req.Value)) throw ApiException.BadRequest("'value' is required.");
        var limit = Math.Clamp(req.Limit, 1, 200);

        await using var conn = await db.OpenConnectionAsync(ct);
        var dataType = await SqlHelpers.GetDataTypeAsync(conn, req.Category, req.Property, ct);
        var exact = req.Mode == SearchMode.Exact;

        IEnumerable<ResultRow> rows;
        if (dataType == "number")
        {
            // Value is compared as printed in the document: no unit conversion.
            if (!decimal.TryParse(req.Value, NumberStyles.Float, CultureInfo.InvariantCulture, out var target))
                throw ApiException.BadRequest($"'{req.Value}' is not a number; property '{req.Property}' is numeric.");

            // delta = MIN(ABS(num - target)) over the field's numbers, so any value in "250/300" can match.
            rows = await conn.QueryAsync<ResultRow>(new CommandDefinition(
                Select + @", m.num AS matched_number, m.delta
                  FROM documents d
                  JOIN spec_fields f ON f.document_id = d.id AND f.prop_key = @property
                  JOIN LATERAL (SELECT n.num, abs(n.num - @target) AS delta FROM spec_numbers n
                                WHERE n.field_id = f.id ORDER BY abs(n.num - @target), n.ord LIMIT 1) m ON true
                  WHERE d.category = @category AND d.duplicate_of IS NULL AND (@includeOld OR d.is_latest)
                    AND (@exact = false OR m.delta = 0)
                  ORDER BY m.delta, d.rev_rank DESC, d.file_name
                  LIMIT @limit",
                new { category = req.Category, property = req.Property, target, includeOld = req.IncludeOld, exact, limit },
                cancellationToken: ct));
        }
        else
        {
            // exact value_canon match first, then "contains" (a code inside a list), then pg_trgm similarity >= 0.3
            var canon = Canonicalizer.Canon(req.Value);
            rows = await conn.QueryAsync<ResultRow>(new CommandDefinition(
                Select + @", similarity(f.value_canon, @canon)::float8 AS similarity
                  FROM documents d
                  JOIN spec_fields f ON f.document_id = d.id AND f.prop_key = @property
                  WHERE d.category = @category AND d.duplicate_of IS NULL AND (@includeOld OR d.is_latest)
                    AND (f.value_canon = @canon
                         OR (@exact = false AND (strpos(f.value_canon, @canon) > 0 OR similarity(f.value_canon, @canon) >= 0.3)))
                  ORDER BY (f.value_canon = @canon) DESC, (strpos(f.value_canon, @canon) > 0) DESC,
                           similarity(f.value_canon, @canon) DESC, d.rev_rank DESC, d.file_name
                  LIMIT @limit",
                new { category = req.Category, property = req.Property, canon, includeOld = req.IncludeOld, exact, limit },
                cancellationToken: ct));
        }

        var list = rows.ToList();
        var ids = list.Select(r => r.DocumentId).ToList();
        var siblings = await SqlHelpers.GetSiblingsAsync(conn, ids, ct);
        // reused_on is a text spec holding "PP60050, PP60053, PP60056": the strongest reuse signal, shown on each result
        var reused = (await conn.QueryAsync<ReusedRow>(new CommandDefinition(
            "SELECT document_id, value_text FROM spec_fields WHERE prop_key = 'reused_on' AND document_id = ANY(@ids)",
            new { ids = ids.ToArray() }, cancellationToken: ct))).ToDictionary(r => r.DocumentId, r => r.ValueText);
        return new SearchResponse(list.Select(r => new SearchResultDto(
            r.DocumentId, r.FileName, r.RelPath, r.ProjectCode, r.Revision, r.IsLatest, r.Application,
            r.MatchedValue, r.MatchedNumber, r.Delta, r.Similarity, r.Page, SqlHelpers.ParseBbox(r.Bbox),
            siblings[r.DocumentId].ToList(),
            reused.TryGetValue(r.DocumentId, out var v) ? v.Split(", ", StringSplitOptions.RemoveEmptyEntries) : [])).ToList());
    }
}
