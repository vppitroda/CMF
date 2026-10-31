namespace Docsearch.Api.Contracts;

/// <summary>Steps 1-3 of the cascading filter: categories, properties, distinct values.</summary>
public interface ICatalogService
{
    Task<IReadOnlyList<CategoryDto>> GetCategoriesAsync(CancellationToken ct);
    Task<IReadOnlyList<PropertyDto>> GetPropertiesAsync(string category, CancellationToken ct);
    Task<IReadOnlyList<ValueDto>> GetValuesAsync(string category, string property, string? q, CancellationToken ct);
}

/// <summary>Step 4: nearest-value search (scope.md §6 "Near-match rules").</summary>
public interface ISearchService
{
    Task<SearchResponse> SearchAsync(SearchRequest request, CancellationToken ct);
}

public interface IDocumentService
{
    Task<DocumentDetailDto> GetAsync(long id, CancellationToken ct);
    Task<DocumentFile> GetFileAsync(long id, CancellationToken ct);
}
