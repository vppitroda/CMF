"""value_canon: the grouping / fuzzy key for a printed value (scope.md §6 "Canonicalisation").

lowercase; collapse whitespace; strip trailing remarks in parentheses; apply the typo alias map.
The original text always stays in spec_fields.value_text. Unknown values are kept, never dropped.
"""
from __future__ import annotations

import re

# Bump when ALIASES / canon() change: load folds it into the extraction hash, so every document is
# re-canonicalised on the next `load` even though its extraction did not change. Keep Canonicalizer.cs in step.
CANON_VERSION = "2"

# (pattern, replacement) applied in order to the lowercased text
ALIASES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bminerial\b"), "mineral"),                         # typo found in the sample
    (re.compile(r"\biso vg[\s-]*(\d+)"), r"iso vg\1"),                # ISO VG 68 / ISO VG-68 / ISO VG68
    (re.compile(r"(\d)\s*(bar|lpm|kw|rpm|ltrs?|mm|hz)\b"), r"\1 \2"),  # 230Bar -> 230 bar
    (re.compile(r"(?<=\d)\s*/\s*(?=\d)"), "/"),                       # 250 / 300 -> 250/300
    (re.compile(r"(?<=\d)\s*\+\s*(?=\d)"), "+"),                      # 215 + 215 -> 215+215
    (re.compile(r"^(?:n[./\s]?a\.?|-+|nil)$"), "na"),                 # NA / N.A. / N/A / - : "not applicable"
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


def part_no_canon(text: str) -> str:
    """Search key for part numbers: case/dashes/spaces/dots ignored, and the O/0 and I/1 mix-ups folded
    (drawings and typed queries confuse them). Apply the same function to a typed query."""
    s = re.sub(r"[^A-Z0-9]", "", text.upper())
    return s.replace("O", "0").replace("I", "1")


def canon(text: str) -> str:
    body, _ = split_remark(text)
    out = body.lower()
    for pat, rep in ALIASES:
        out = pat.sub(rep, out)
    return out
