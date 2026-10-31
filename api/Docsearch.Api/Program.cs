using System.Text.Json.Serialization;
using Dapper;
using Docsearch.Api.Contracts;
using Docsearch.Api.Infrastructure;
using Docsearch.Api.Services;
using Npgsql;

// DOCSEARCH_ROOT / DOCSEARCH_DB come from environment variables (or appsettings.json)
var builder = WebApplication.CreateBuilder(args);
builder.Services.Configure<DocsearchOptions>(o =>
{
    o.Root = builder.Configuration["DOCSEARCH_ROOT"] ?? "";
    o.Db = builder.Configuration["DOCSEARCH_DB"] ?? "";
});
var opts = new DocsearchOptions { Root = builder.Configuration["DOCSEARCH_ROOT"] ?? "", Db = builder.Configuration["DOCSEARCH_DB"] ?? "" };
if (opts.Db == "") throw new InvalidOperationException("DOCSEARCH_DB is not configured.");

DefaultTypeMap.MatchNamesWithUnderscores = true;   // file_name -> FileName
builder.Services.AddSingleton(NpgsqlDataSource.Create(ConnectionStrings.ToNpgsql(opts.Db)));
builder.Services.AddScoped<ICatalogService, CatalogService>();
builder.Services.AddScoped<ISearchService, SearchService>();
builder.Services.AddScoped<IDocumentService, DocumentService>();

builder.Services.AddControllers().AddJsonOptions(o =>
    o.JsonSerializerOptions.Converters.Add(new JsonStringEnumConverter()));   // mode=near|exact
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<ApiExceptionHandler>();
builder.Services.AddOpenApiDocument(c => c.Title = "Docsearch API");          // NSwag generates the Angular client from this
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.WithOrigins("http://localhost:4200").AllowAnyHeader().AllowAnyMethod()
     .WithExposedHeaders("Content-Range", "Accept-Ranges", "Content-Length")));

var app = builder.Build();
app.UseExceptionHandler();
app.UseCors();
app.UseOpenApi();
app.UseSwaggerUi();            // /swagger
app.MapControllers();
app.Run();

// lets WebApplicationFactory<Program> see the entry point
public partial class Program;
