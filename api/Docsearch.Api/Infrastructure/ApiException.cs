using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace Docsearch.Api.Infrastructure;

/// <summary>Thrown by services for expected failures; mapped to a ProblemDetails response.</summary>
public class ApiException(int statusCode, string message) : Exception(message)
{
    public int StatusCode { get; } = statusCode;
    public static ApiException BadRequest(string message) => new(StatusCodes.Status400BadRequest, message);
    public static ApiException NotFound(string message) => new(StatusCodes.Status404NotFound, message);
}

public class ApiExceptionHandler(IProblemDetailsService problems) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(HttpContext ctx, Exception ex, CancellationToken ct)
    {
        if (ex is not ApiException api) return false;   // anything else stays a 500
        ctx.Response.StatusCode = api.StatusCode;
        return await problems.TryWriteAsync(new ProblemDetailsContext
        {
            HttpContext = ctx,
            ProblemDetails = new ProblemDetails { Status = api.StatusCode, Detail = api.Message },
        });
    }
}
