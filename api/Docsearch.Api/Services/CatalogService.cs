using Dapper;
using Docsearch.Api.Contracts;
using Docsearch.Api.Infrastructure;
using Npgsql;

namespace Docsearch.Api.Services;

public class CatalogService(NpgsqlDataSource db) : ICatalogService
{
    private class CategoryRow { public string Key { get; set; } = ""; public int DocCount { get; set; } }
    private class PropertyRow { public string Key { get; set; } = ""; public string Label { get; set; } = ""; public string DataType { get; set; } = ""; public int DocCount { get; set; } }
    private class ValueRow { public string Display { get; set; } = ""; public string Canon { get; set; } = ""; public int DocCount { get; set; } }

    // Only categories that have a property registry are searchable; counts are latest, non-duplicate documents.
    public async Task<IReadOnlyList<CategoryDto>> GetCategoriesAsync(CancellationToken ct)
    {
        await using var conn = await db.OpenConnectionAsync(ct);
        var rows = await conn.QueryAsync<CategoryRow>(new CommandDefinition(
            @"SELECT d.category AS key, count(*)::int AS doc_count
              FROM documents d
              WHERE d.is_latest AND d.duplicate_of IS NULL
                AND d.category IN (SELECT DISTINCT category FROM properties)
              GROUP BY d.category ORDER BY d.category", cancellationToken: ct));
        return rows.Select(r => new CategoryDto(r.Key, CategoryLabels.For(r.Key), r.DocCount)).ToList();
    }

    // Properties that exist for the category AND have data in at least one latest document.
    public async Task<IReadOnlyList<PropertyDto>> GetPropertiesAsync(string category, CancellationToken ct)
    {
        await using var conn = await db.OpenConnectionAsync(ct);
        if (!await conn.ExecuteScalarAsync<bool>(new CommandDefinition(
                "SELECT EXISTS (SELECT 1 FROM properties WHERE category = @category)", new { category }, cancellationToken: ct)))
            throw ApiException.NotFound($"Unknown category '{category}'.");

        var rows = await conn.QueryAsync<PropertyRow>(new CommandDefinition(
            @"SELECT p.prop_key AS key, p.label, p.data_type, count(DISTINCT f.document_id)::int AS doc_count
              FROM properties p
              JOIN spec_fields f ON f.prop_key = p.prop_key
              JOIN documents d ON d.id = f.document_id AND d.category = p.category
                              AND d.is_latest AND d.duplicate_of IS NULL
              WHERE p.category = @category
              GROUP BY p.prop_key, p.label, p.data_type, p.sort_order
              ORDER BY p.sort_order", new { category }, cancellationToken: ct));
        return rows.Select(r => new PropertyDto(r.Key, r.Label, r.DataType, r.DocCount)).ToList();
    }

    // Numeric properties are ordered by their first number; q filters by substring or trigram similarity.
    public async Task<IReadOnlyList<ValueDto>> GetValuesAsync(string category, string property, string? q, CancellationToken ct)
    {
        await using var conn = await db.OpenConnectionAsync(ct);
        await SqlHelpers.GetDataTypeAsync(conn, category, property, ct);
        var canonQ = string.IsNullOrWhiteSpace(q) ? null : Canonicalizer.Canon(q);

        var rows = await conn.QueryAsync<ValueRow>(new CommandDefinition(
            @"SELECT mode() WITHIN GROUP (ORDER BY f.value_text) AS display,
                     f.value_canon AS canon,
                     count(DISTINCT f.document_id)::int AS doc_count
              FROM spec_fields f
              JOIN documents d ON d.id = f.document_id
              LEFT JOIN spec_numbers first ON first.field_id = f.id AND first.ord = 0
              WHERE d.category = @category AND f.prop_key = @property
                AND d.is_latest AND d.duplicate_of IS NULL
                AND (@canonQ::text IS NULL OR f.value_canon LIKE '%' || @canonQ || '%' OR similarity(f.value_canon, @canonQ) >= 0.3)
              GROUP BY f.value_canon
              ORDER BY min(first.num) NULLS LAST, f.value_canon",
            new { category, property, canonQ }, cancellationToken: ct));
        return rows.Select(r => new ValueDto(r.Display, r.Canon, r.DocCount)).ToList();
    }
}
