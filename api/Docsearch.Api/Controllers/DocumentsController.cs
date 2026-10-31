using Docsearch.Api.Contracts;
using Microsoft.AspNetCore.Mvc;

namespace Docsearch.Api.Controllers;

[ApiController]
[Route("api/documents")]
public class DocumentsController(IDocumentService documents) : ControllerBase
{
    /// <summary>A document with all extracted specs, ports, notes, CAD siblings and its other revisions.</summary>
    [HttpGet("{id:long}", Name = "GetDocument")]
    public async Task<ActionResult<DocumentDetailDto>> Get(long id, CancellationToken ct) =>
        Ok(await documents.GetAsync(id, ct));

    /// <summary>Streams the source file from DOCSEARCH_ROOT (HTTP Range supported, for the PDF viewer).</summary>
    [HttpGet("{id:long}/file", Name = "GetDocumentFile")]
    [ProducesResponseType(typeof(FileResult), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetFile(long id, CancellationToken ct)
    {
        var f = await documents.GetFileAsync(id, ct);
        return PhysicalFile(f.PhysicalPath, f.ContentType, enableRangeProcessing: true);
    }
}
