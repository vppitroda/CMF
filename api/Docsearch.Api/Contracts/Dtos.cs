namespace Docsearch.Api.Contracts;

public record CategoryDto(string Key, string Label, int DocCount);

public record PropertyDto(string Key, string Label, string DataType, int DocCount);

/// <summary>A distinct value found in the indexed documents (step 3 of the UI).</summary>
public record ValueDto(string Display, string Canon, int DocCount);

public record SiblingDto(long Id, string FileName, string Kind);

public record SearchResultDto(
    long DocumentId, string FileName, string RelPath, string? ProjectCode, string? Revision, bool IsLatest,
    string? Application, string MatchedValue, decimal? MatchedNumber, decimal? Delta, double? Similarity,
    int? Page, double[]? Bbox, IReadOnlyList<SiblingDto> Siblings, IReadOnlyList<string> ReusedOn);

public record SearchResponse(IReadOnlyList<SearchResultDto> Results);

public record SpecDto(
    string Key, string Label, string Value, string? Unit, string? ListSep, decimal[] Numbers,
    System.Text.Json.JsonElement? Extra, int? Page, double[]? Bbox);

public record TerminationDto(string? Table, string? Name, string? Size, string? Connection, string? TubePipe, int? Page, double[]? Bbox);

public record NoteDto(string? No, string? Text, int? Page);

public record BomLineDto(
    string? ItemNo, string? PartNo, string? Description, string? Make, string? Qty, string? Remarks, int? Page, double[]? Bbox);

public record RevisionDto(long Id, string FileName, string? Revision, bool IsLatest);

public record DocumentDetailDto(
    long Id, string FileName, string RelPath, string Ext, string Kind, string Category, string? SourceFolder,
    string? ProjectCode, string? Revision, bool IsLatest, string? Application, int? PageCount,
    string ParseStatus, System.Text.Json.JsonElement ParseWarnings,
    IReadOnlyList<SpecDto> Specs, IReadOnlyList<TerminationDto> Terminations, IReadOnlyList<NoteDto> Notes,
    IReadOnlyList<BomLineDto> BomLines, IReadOnlyList<SiblingDto> Siblings, IReadOnlyList<RevisionDto> Revisions);

public enum SearchMode { Near, Exact }

public record SearchRequest(string Category, string Property, string Value, SearchMode Mode = SearchMode.Near,
                            int Limit = 20, bool IncludeOld = false);

/// <summary>A file resolved inside DOCSEARCH_ROOT (never exposed to clients as a path).</summary>
public record DocumentFile(string PhysicalPath, string ContentType);
