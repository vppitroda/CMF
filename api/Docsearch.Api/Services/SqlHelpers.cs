using System.Text.Json;
using Dapper;
using Docsearch.Api.Contracts;
using Docsearch.Api.Infrastructure;
using Npgsql;

namespace Docsearch.Api.Services;

internal static class SqlHelpers
{
    public static double[]? ParseBbox(string? json) =>
        json is null ? null : JsonSerializer.Deserialize<double[]>(json);

    /// <summary>Data type ('number' | 'text') of a registered property; 404 if category/property is unknown.</summary>
    public static async Task<string> GetDataTypeAsync(NpgsqlConnection conn, string category, string property, CancellationToken ct)
    {
        var type = await conn.QuerySingleOrDefaultAsync<string>(new CommandDefinition(
            "SELECT data_type FROM properties WHERE category = @category AND prop_key = @property",
            new { category, property }, cancellationToken: ct));
        return type ?? throw ApiException.NotFound($"Unknown property '{property}' for category '{category}'.");
    }

    private class SiblingRow
    {
        public long FromId { get; set; }
        public long Id { get; set; }
        public string FileName { get; set; } = "";
        public string Ext { get; set; } = "";
    }

    /// <summary>Linked CAD files (the editable source) for each document id.</summary>
    public static async Task<ILookup<long, SiblingDto>> GetSiblingsAsync(NpgsqlConnection conn, IEnumerable<long> ids, CancellationToken ct)
    {
        var rows = await conn.QueryAsync<SiblingRow>(new CommandDefinition(
            @"SELECT l.from_id, t.id, t.file_name, t.ext
              FROM doc_links l JOIN documents t ON t.id = l.to_id
              WHERE l.link_type = 'cad_sibling' AND l.from_id = ANY(@ids) AND t.duplicate_of IS NULL
              ORDER BY t.file_name",
            new { ids = ids.ToArray() }, cancellationToken: ct));
        return rows.ToLookup(r => r.FromId, r => new SiblingDto(r.Id, r.FileName, r.Ext.TrimStart('.')));
    }
}
