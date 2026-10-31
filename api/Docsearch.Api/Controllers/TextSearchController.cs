using Docsearch.Api.Contracts;
using Microsoft.AspNetCore.Mvc;

namespace Docsearch.Api.Controllers;

[ApiController]
[Route("api/text-search")]
public class TextSearchController(ITextSearchService textSearch) : ControllerBase
{
    /// <summary>
    /// Fuzzy keyword search (typos tolerated) over part numbers, BOM descriptions, extracted spec values, notes and file
    /// names. One result per document, best match first; <c>q</c> needs at least 3 characters.
    /// </summary>
    [HttpGet(Name = "TextSearch")]
    public async Task<ActionResult<TextSearchResponse>> Search(
        [FromQuery] string q, [FromQuery] string? category, [FromQuery] int limit = 20, [FromQuery] bool includeOld = false,
        CancellationToken ct = default) =>
        Ok(await textSearch.SearchAsync(new TextSearchRequest(q, category, limit, includeOld), ct));
}
