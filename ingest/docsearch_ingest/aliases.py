"""value_canon: the grouping / fuzzy key for a printed value (scope.md §6 "Canonicalisation").

lowercase; collapse whitespace; strip trailing remarks in parentheses; apply the typo alias map.
The original text always stays in spec_fields.value_text. Unknown values are kept, never dropped.
"""
from __future__ import annotations

import re

# (pattern, replacement) applied in order to the lowercased text
ALIASES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bminerial\b"), "mineral"),
    (re.compile(r"\biso vg\s*(\d+)"), r"iso vg\1"),
    (re.compile(r"^(?:n\.?\s?a\.?|-+|nil)$"), "na"),        # NA / N.A. / - all mean "not applicable"
]

_WS = re.compile(r"\s+")
_REMARK = re.compile(r"\s*\(([^()]*)\)\s*$")


def ws(text: str) -> str:
    """Whitespace-normalised, as stored in value_text."""
    return _WS.sub(" ", text).strip()


def split_remark(text: str) -> tuple[str, str | None]:
    """'315 Bar ( By External Source )' -> ('315 Bar', 'By External Source')."""
    text = ws(text)
    m = _REMARK.search(text)
    if not m:
        return text, None
    return text[: m.start()].strip(), ws(m.group(1))


def canon(text: str) -> str:
    body, _ = split_remark(text)
    out = body.lower()
    for pat, rep in ALIASES:
        out = pat.sub(rep, out)
    return out
