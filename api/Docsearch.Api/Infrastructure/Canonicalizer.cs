using System.Text.RegularExpressions;

namespace Docsearch.Api.Infrastructure;

/// <summary>
/// Mirrors ingest/docsearch_ingest/aliases.py so a typed query lands on the same value_canon / part_no_canon the
/// loader stored. Keep the two in step (CANON_VERSION there); the unit tests on both sides share their cases.
/// </summary>
public static partial class Canonicalizer
{
    [GeneratedRegex(@"\s+")] private static partial Regex Ws();
    [GeneratedRegex(@"\s*\(([^()]*)\)\s*$")] private static partial Regex Remark();
    [GeneratedRegex(@"\bminerial\b")] private static partial Regex Minerial();
    [GeneratedRegex(@"\biso vg[\s-]*(\d+)")] private static partial Regex IsoVg();
    [GeneratedRegex(@"(\d)\s*(bar|lpm|kw|rpm|ltrs?|mm|hz)\b")] private static partial Regex UnitSpacing();
    [GeneratedRegex(@"(?<=\d)\s*/\s*(?=\d)")] private static partial Regex Slash();
    [GeneratedRegex(@"(?<=\d)\s*\+\s*(?=\d)")] private static partial Regex Plus();
    [GeneratedRegex(@"^(?:n[./\s]?a\.?|-+|nil)$")] private static partial Regex NotApplicable();
    [GeneratedRegex(@"[^A-Z0-9]")] private static partial Regex NonAlnum();

    public static string Canon(string text)
    {
        var s = Remark().Replace(Ws().Replace(text, " ").Trim(), "").Trim().ToLowerInvariant();
        s = Minerial().Replace(s, "mineral");
        s = IsoVg().Replace(s, "iso vg$1");
        s = UnitSpacing().Replace(s, "$1 $2");
        s = Slash().Replace(s, "/");
        s = Plus().Replace(s, "+");
        return NotApplicable().Replace(s, "na");
    }

    /// <summary>Part-number search key: case/dashes/spaces/dots ignored, O/0 and I/1 folded (as part_no_canon).</summary>
    public static string PartNo(string text) =>
        NonAlnum().Replace(text.ToUpperInvariant(), "").Replace('O', '0').Replace('I', '1');

    /// <summary>
    /// A query that looks like a part number: one token with a digit, 3+ chars ("TPN00041", "2103-01-18.00", "4WE6").
    /// Returns its part-number key, or null for ordinary words ("ball valve"), which would be mangled by the O/I folding.
    /// </summary>
    public static string? AsPartNo(string query)
    {
        var q = query.Trim();
        if (q.Length < 3 || q.Any(char.IsWhiteSpace) || !q.Any(char.IsDigit)) return null;
        var key = PartNo(q);
        return key.Length >= 3 ? key : null;
    }
}
