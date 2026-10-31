namespace Docsearch.Api.Infrastructure;

public class DocsearchOptions
{
    /// <summary>Folder with the source files (DOCSEARCH_ROOT). Read-only.</summary>
    public string Root { get; set; } = "";
    /// <summary>postgresql:// URL or Npgsql connection string (DOCSEARCH_DB).</summary>
    public string Db { get; set; } = "";
}
