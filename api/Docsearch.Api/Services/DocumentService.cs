using System.Text.Json;
using Dapper;
using Docsearch.Api.Contracts;
using Docsearch.Api.Infrastructure;
using Microsoft.AspNetCore.StaticFiles;
using Microsoft.Extensions.Options;
using Npgsql;

namespace Docsearch.Api.Services;

public class DocumentService(NpgsqlDataSource db, IOptions<DocsearchOptions> options) : IDocumentService
{
    private static readonly FileExtensionContentTypeProvider ContentTypes = new();

    private class DocRow
    {
        public long Id { get; set; }
        public string FileName { get; set; } = "";
        public string RelPath { get; set; } = "";
        public string Ext { get; set; } = "";
        public string Kind { get; set; } = "";
        public string Category { get; set; } = "";
        public string? SourceFolder { get; set; }
        public string? ProjectCode { get; set; }
        public string? Revision { get; set; }
        public bool IsLatest { get; set; }
        public string? Application { get; set; }
        public int? PageCount { get; set; }
        public string ParseStatus { get; set; } = "";
        public string ParseWarnings { get; set; } = "[]";
        public string FamilyKey { get; set; } = "";
    }

    private class SpecRow
    {
        public string PropKey { get; set; } = "";
        public string? Label { get; set; }
        public string ValueText { get; set; } = "";
        public string? Unit { get; set; }
        public string? ListSep { get; set; }
        public decimal[]? Numbers { get; set; }
        public string? Extra { get; set; }
        public int? Page { get; set; }
        public string? Bbox { get; set; }
    }

    private class TermRow
    {
        public string? Tbl { get; set; }
        public string? Name { get; set; }
        public string? Size { get; set; }
        public string? Connection { get; set; }
        public string? TubePipe { get; set; }
        public int? Page { get; set; }
        public string? Bbox { get; set; }
    }

    private class NoteRow { public string? No { get; set; } public string? Text { get; set; } public int? Page { get; set; } }

    private class RevRow { public long Id { get; set; } public string FileName { get; set; } = ""; public string? Revision { get; set; } public bool IsLatest { get; set; } }

    public async Task<DocumentDetailDto> GetAsync(long id, CancellationToken ct)
    {
        await using var conn = await db.OpenConnectionAsync(ct);
        var d = await conn.QuerySingleOrDefaultAsync<DocRow>(new CommandDefinition(
            @"SELECT id, file_name, rel_path, ext, kind, category, source_folder, project_code, revision, is_latest,
                     application, page_count, parse_status, parse_warnings::text AS parse_warnings, family_key
              FROM documents WHERE id = @id", new { id }, cancellationToken: ct))
            ?? throw ApiException.NotFound($"Document {id} not found.");

        var specs = await conn.QueryAsync<SpecRow>(new CommandDefinition(
            @"SELECT f.prop_key, p.label, f.value_text, f.unit, f.list_sep, f.extra::text AS extra, f.page, f.bbox::text AS bbox,
                     (SELECT array_agg(n.num ORDER BY n.ord) FROM spec_numbers n WHERE n.field_id = f.id) AS numbers
              FROM spec_fields f LEFT JOIN properties p ON p.category = @category AND p.prop_key = f.prop_key
              WHERE f.document_id = @id ORDER BY p.sort_order NULLS LAST, f.prop_key",
            new { id, category = d.Category }, cancellationToken: ct));
        var terms = await conn.QueryAsync<TermRow>(new CommandDefinition(
            "SELECT tbl, name, size, connection, tube_pipe, page, bbox::text AS bbox FROM terminations WHERE document_id = @id ORDER BY id",
            new { id }, cancellationToken: ct));
        var notes = await conn.QueryAsync<NoteRow>(new CommandDefinition(
            "SELECT no, text, page FROM notes WHERE document_id = @id ORDER BY id", new { id }, cancellationToken: ct));
        var revs = await conn.QueryAsync<RevRow>(new CommandDefinition(
            @"SELECT id, file_name, revision, is_latest FROM documents
              WHERE family_key = @family AND duplicate_of IS NULL AND ext = @ext ORDER BY rev_rank, file_name",
            new { family = d.FamilyKey, ext = d.Ext }, cancellationToken: ct));
        var siblings = await SqlHelpers.GetSiblingsAsync(conn, [id], ct);

        return new DocumentDetailDto(
            d.Id, d.FileName, d.RelPath, d.Ext, d.Kind, d.Category, d.SourceFolder, d.ProjectCode, d.Revision, d.IsLatest,
            d.Application, d.PageCount, d.ParseStatus, JsonDocument.Parse(d.ParseWarnings).RootElement.Clone(),
            specs.Select(s => new SpecDto(s.PropKey, s.Label ?? s.PropKey, s.ValueText, s.Unit, s.ListSep, s.Numbers ?? [],
                s.Extra is null ? null : JsonDocument.Parse(s.Extra).RootElement.Clone(), s.Page, SqlHelpers.ParseBbox(s.Bbox))).ToList(),
            terms.Select(t => new TerminationDto(t.Tbl, t.Name, t.Size, t.Connection, t.TubePipe, t.Page, SqlHelpers.ParseBbox(t.Bbox))).ToList(),
            notes.Select(n => new NoteDto(n.No, n.Text, n.Page)).ToList(),
            siblings[id].ToList(),
            revs.Select(r => new RevisionDto(r.Id, r.FileName, r.Revision, r.IsLatest)).ToList());
    }

    public async Task<DocumentFile> GetFileAsync(long id, CancellationToken ct)
    {
        await using var conn = await db.OpenConnectionAsync(ct);
        var rel = await conn.QuerySingleOrDefaultAsync<string>(new CommandDefinition(
            "SELECT rel_path FROM documents WHERE id = @id", new { id }, cancellationToken: ct))
            ?? throw ApiException.NotFound($"Document {id} not found.");

        var root = Path.GetFullPath(options.Value.Root);
        var full = Path.GetFullPath(Path.Combine(root, rel));
        // rel_path comes from our own scan, but never serve anything outside the root
        if (!full.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
            || !File.Exists(full))
            throw ApiException.NotFound($"File for document {id} is not available.");

        if (!ContentTypes.TryGetContentType(full, out var type)) type = "application/octet-stream";
        return new DocumentFile(full, type);
    }
}
