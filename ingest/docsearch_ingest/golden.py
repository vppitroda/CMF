"""Accuracy of the hyd_circuit extractor against the hand-read golden set (tests/golden/circuits.json).

The golden values were transcribed by eye from rendered crops of each drawing, BEFORE looking at the extractor's output
for that drawing (see tests/golden/README.md). This module re-runs the extractor live and scores it.

Scoring rules (documented because "accuracy" means nothing without them):
  * Spec field: correct when the extracted value equals the golden text ignoring ALL whitespace (pdfium drops the space in
    mixed fractions and glyph gaps; whitespace is never what an engineer filters on). Case and punctuation must match.
    A field the drawing does not carry must be absent from the extraction.
  * Port row: correct when name, size, connection and tube/pipe all match (same whitespace rule). Rows are matched as a
    multiset, so row order does not matter; extractor-only rows are counted as false positives.
  * Note: correct when the text for the same note number matches; "polluted" when the golden text is a prefix of what
    was extracted (right words, junk appended), which is reported separately and not counted as correct.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .circuit import extract_circuit

GOLDEN = Path(__file__).resolve().parents[1] / "tests" / "golden" / "circuits.json"
COLS = ("name", "size", "connection", "tube_pipe")


def squash(s: str | None) -> str:
    return re.sub(r"\s+", "", s or "")


@dataclass
class DrawingScore:
    file: str
    sheet: str
    customer: str
    field_ok: dict[str, bool] = field(default_factory=dict)         # golden-present fields only
    field_detail: dict[str, tuple[str, str]] = field(default_factory=dict)    # key -> (golden, extracted) for misses
    false_present: list[str] = field(default_factory=list)          # extracted although the drawing has none
    ports_golden: int = 0
    ports_extracted: int = 0
    ports_ok: int = 0
    port_misses: list[tuple[str, str]] = field(default_factory=list)  # (golden row, closest extracted row or '')
    port_extra: list[str] = field(default_factory=list)
    notes_golden: int = 0
    notes_ok: int = 0
    notes_polluted: int = 0
    notes_missing: list[str] = field(default_factory=list)
    notes_extra: int = 0


def _row(d: dict) -> tuple[str, ...]:
    return tuple(squash(d.get(c)) for c in COLS)


def _row_text(d: dict) -> str:
    return " | ".join(d.get(c) or "" for c in COLS)


def score_drawing(g: dict, root: Path) -> DrawingScore:
    r = extract_circuit(str(root / g["file"]))
    sc = DrawingScore(g["file"], g["sheet"], g["file"].split("/")[0])

    got = {k: v["value"] for k, v in r["specs"].items()}
    for key, want in g["specs"].items():
        ok = squash(got.get(key)) == squash(want)
        sc.field_ok[key] = ok
        if not ok:
            sc.field_detail[key] = (want, got.get(key, "<missing>"))
    sc.false_present = [k for k in got if k not in g["specs"] and k != "project_name"]

    want_rows = Counter(_row(t) for t in g["terminations"])
    got_rows = Counter(_row(t) for t in r["terminations"])
    sc.ports_golden, sc.ports_extracted = len(g["terminations"]), len(r["terminations"])
    sc.ports_ok = sum((want_rows & got_rows).values())
    missed = list((want_rows - got_rows).elements())
    extra = list((got_rows - want_rows).elements())
    texts = {_row(t): _row_text(t) for t in g["terminations"] + r["terminations"]}
    for m in missed:
        # pair each miss with an unmatched extracted row that shares its name, for a readable report
        pair = next((e for e in extra if e[0] == m[0]), None)
        if pair:
            extra.remove(pair)
        sc.port_misses.append((texts[m], texts[pair] if pair else ""))
    sc.port_extra = [texts[e] for e in extra]

    sc.notes_golden = len(g["notes"])
    ext = {n.get("no"): n.get("text") or "" for n in r["notes"]}
    for n in g["notes"]:
        e = ext.get(n["no"])
        if e is None:
            sc.notes_missing.append(f"{n['no']}. {n['text'][:50]}")
        elif squash(e) == squash(n["text"]):
            sc.notes_ok += 1
        elif squash(e).startswith(squash(n["text"])):
            sc.notes_polluted += 1
        else:
            sc.notes_missing.append(f"{n['no']}. {n['text'][:50]}  (extracted differently: {e[:50]})")
    sc.notes_extra = len([k for k in ext if k not in {n["no"] for n in g["notes"]}])
    return sc


def score_all(root: Path, golden: Path = GOLDEN) -> list[DrawingScore]:
    data = json.loads(golden.read_text(encoding="utf-8"))["drawings"]
    return [score_drawing(g, root) for g in data]


def summarise(scores: list[DrawingScore]) -> dict:
    per_field: dict[str, list[bool]] = defaultdict(list)
    for s in scores:
        for k, ok in s.field_ok.items():
            per_field[k].append(ok)
    n_fields = sum(len(v) for v in per_field.values())
    ok_fields = sum(sum(v) for v in per_field.values())
    return {
        "drawings": len(scores),
        "fields": n_fields, "fields_ok": ok_fields,
        "per_field": {k: (sum(v), len(v)) for k, v in per_field.items()},
        "false_present": sum(len(s.false_present) for s in scores),
        "drawings_all_fields_ok": sum(all(s.field_ok.values()) for s in scores),
        "ports": sum(s.ports_golden for s in scores), "ports_ok": sum(s.ports_ok for s in scores),
        "ports_extra": sum(len(s.port_extra) for s in scores),
        "notes": sum(s.notes_golden for s in scores), "notes_ok": sum(s.notes_ok for s in scores),
        "notes_polluted": sum(s.notes_polluted for s in scores), "notes_extra": sum(s.notes_extra for s in scores),
    }


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f} %" if b else "n/a"


def markdown(scores: list[DrawingScore]) -> list[str]:
    sm = summarise(scores)
    out = [f"## Accuracy against the golden set ({sm['drawings']} circuit drawings)", "",
           "Golden values were read by eye from rendered crops (see `ingest/tests/golden/README.md`); scoring rules are in "
           "`docsearch_ingest/golden.py`.", "",
           "| measure | correct / total | accuracy |", "|---|---|---|",
           f"| spec fields (all drawings) | {sm['fields_ok']} / {sm['fields']} | {pct(sm['fields_ok'], sm['fields'])} |",
           f"| drawings with every field correct | {sm['drawings_all_fields_ok']} / {sm['drawings']} | "
           f"{pct(sm['drawings_all_fields_ok'], sm['drawings'])} |",
           f"| fields extracted that the drawing does not have | {sm['false_present']} | |",
           f"| port rows (exact on all 4 columns) | {sm['ports_ok']} / {sm['ports']} | {pct(sm['ports_ok'], sm['ports'])} |",
           f"| port rows extracted that are not on the drawing | {sm['ports_extra']} | |",
           f"| notes (exact text) | {sm['notes_ok']} / {sm['notes']} | {pct(sm['notes_ok'], sm['notes'])} |",
           f"| notes with the right words but junk appended | {sm['notes_polluted']} | |", "",
           "### Per field", "", "| field | correct / present | accuracy |", "|---|---|---|"]
    out += [f"| {k} | {a} / {b} | {pct(a, b)} |" for k, (a, b) in sorted(sm["per_field"].items(), key=lambda kv: kv[0])]

    def group(title: str, key) -> list[str]:
        g: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
        for s in scores:
            a = g[key(s)]
            a[0] += sum(s.field_ok.values()); a[1] += len(s.field_ok); a[2] += s.ports_ok; a[3] += s.ports_golden
        return ["", f"### By {title}", "", f"| {title} | fields | port rows |", "|---|---|---|"] + [
            f"| {k} | {a[0]} / {a[1]} ({pct(a[0], a[1])}) | {a[2]} / {a[3]} ({pct(a[2], a[3])}) |" for k, a in sorted(g.items())]

    out += group("customer", lambda s: s.customer) + group("sheet size", lambda s: s.sheet)

    misses = [(s, k, w, e) for s in scores for k, (w, e) in s.field_detail.items()]
    out += ["", "### Field mismatches", ""]
    out += [f"- `{s.file.split('/')[-1]}` **{k}**: golden `{w}` / extracted `{e}`" for s, k, w, e in misses] or ["none"]
    pm = [(s, a, b) for s in scores for a, b in s.port_misses]
    out += ["", "### Port-row mismatches", ""]
    out += [f"- `{s.file.split('/')[-1]}`: golden `{a}` / extracted `{b or '(no row with that name)'}`" for s, a, b in pm] or ["none"]
    nm = [(s, n) for s in scores for n in s.notes_missing]
    out += ["", "### Notes missing or wrong", ""] + [f"- `{s.file.split('/')[-1]}`: {n}" for s, n in nm] or ["none"]
    return out
