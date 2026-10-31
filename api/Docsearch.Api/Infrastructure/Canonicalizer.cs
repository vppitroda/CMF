using System.Text.RegularExpressions;

namespace Docsearch.Api.Infrastructure;

/// <summary>
/// Mirrors ingest/docsearch_ingest/aliases.py so a typed query lands on the same value_canon the loader stored.
/// Keep the two in step.
/// </summary>
public static partial class Canonicalizer
{
    [GeneratedRegex(@"\s+")] private static partial Regex Ws();
    [GeneratedRegex(@"\s*\(([^()]*)\)\s*$")] private static partial Regex Remark();
    [GeneratedRegex(@"\bminerial\b")] private static partial Regex Minerial();
    [GeneratedRegex(@"\biso vg\s*(\d+)")] private static partial Regex IsoVg();
    [GeneratedRegex(@"^(?:n\.?\s?a\.?|-+|nil)$")] private static partial Regex NotApplicable();

    public static string Canon(string text)
    {
        var s = Remark().Replace(Ws().Replace(text, " ").Trim(), "").Trim().ToLowerInvariant();
        s = Minerial().Replace(s, "mineral");
        s = IsoVg().Replace(s, "iso vg$1");
        return NotApplicable().Replace(s, "na");
    }
}
