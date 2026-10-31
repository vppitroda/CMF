using Docsearch.Api.Contracts;
using Microsoft.AspNetCore.Mvc;

namespace Docsearch.Api.Controllers;

[ApiController]
[Route("api/categories")]
public class CategoriesController(ICatalogService catalog) : ControllerBase
{
    /// <summary>Step 1: searchable categories with the number of latest, non-duplicate documents.</summary>
    [HttpGet(Name = "GetCategories")]
    public async Task<ActionResult<IReadOnlyList<CategoryDto>>> GetCategories(CancellationToken ct) =>
        Ok(await catalog.GetCategoriesAsync(ct));

    /// <summary>Step 2: properties that exist (and have data) for a category.</summary>
    [HttpGet("{category}/properties", Name = "GetProperties")]
    public async Task<ActionResult<IReadOnlyList<PropertyDto>>> GetProperties(string category, CancellationToken ct) =>
        Ok(await catalog.GetPropertiesAsync(category, ct));

    /// <summary>Step 3: distinct values found for a property, with document counts. <c>q</c> filters them.</summary>
    [HttpGet("{category}/properties/{property}/values", Name = "GetValues")]
    public async Task<ActionResult<IReadOnlyList<ValueDto>>> GetValues(string category, string property, [FromQuery] string? q, CancellationToken ct) =>
        Ok(await catalog.GetValuesAsync(category, property, q, ct));
}
