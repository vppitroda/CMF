using Docsearch.Api.Contracts;
using Microsoft.AspNetCore.Mvc;

namespace Docsearch.Api.Controllers;

[ApiController]
[Route("api/search")]
public class SearchController(ISearchService search) : ControllerBase
{
    /// <summary>
    /// Step 4: documents whose value is nearest to <c>value</c> (numeric: smallest |difference|; text: trigram similarity).
    /// A non-number for a numeric property returns 400.
    /// </summary>
    [HttpGet(Name = "Search")]
    public async Task<ActionResult<SearchResponse>> Search(
        [FromQuery] string category, [FromQuery] string property, [FromQuery] string value,
        [FromQuery] SearchMode mode = SearchMode.Near, [FromQuery] int limit = 20, [FromQuery] bool includeOld = false,
        CancellationToken ct = default) =>
        Ok(await search.SearchAsync(new SearchRequest(category, property, value, mode, limit, includeOld), ct));
}
