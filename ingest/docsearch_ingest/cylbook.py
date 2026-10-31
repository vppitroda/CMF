"""Cylinder GA book ("Cylinder GA drawings for C.009132-DBGVL-Rev.c.pdf"): a drawing book with an INDEX page.

Page 2 lists the cylinders in the book, grouped under project headings:
    SL.NO. | PART NO. | DESCRIPTION (… : Ø<bore> x <rod> x <stroke> mm Stroke) | MATERIAL CODE (ZX…)
The part no. is sometimes its own text object and sometimes glued to the description, so a row is read as
"everything between the serial number and the material code".

POC properties (deliberately coarse): the bores found in the book (any of them can match a search) and the projects it
covers. Each index row is also stored as a parts-list line so it shows in the viewer and in the later text search.
"""
from __future__ import annotations

import re

import pypdfium2 as pdfium

from .aliases import part_no_canon
from .bom import _DIMS
from .pdfium_text import Run, group_lines, page_chars, runs

_PART = re.compile(r"^((?:HAS|HA|HQ|HV|PP)\d+)\s*(.*)$")
_PROJECT = re.compile(r"\((PP\d+)\)\s*$")
_MATERIAL = re.compile(r"^ZX\d+$")


def _union(boxes: list[list[float]]) -> list[float]:
    return [round(min(b[0] for b in boxes), 1), round(min(b[1] for b in boxes), 1),
            round(max(b[2] for b in boxes), 1), round(max(b[3] for b in boxes), 1)]


def _box(rs: list[Run]) -> list[float]:
    return _union([[r.x0, r.y0, r.x1, r.y1] for r in rs])


def extract_cylbook(pdf_path: str, category: str = "cylinder_ga_book") -> dict:
    doc = pdfium.PdfDocument(pdf_path)
    warnings: list[str] = []
    rows: list[dict] = []
    headings: list[tuple[str, list[float]]] = []
    page_no = None
    try:
        for pi in range(min(len(doc), 4)):                     # the index is on page 2; look a little further to be safe
            text = doc[pi].get_textpage().get_text_range()
            if "INDEX" not in text or "PART NO" not in text:
                continue
            page_no = pi + 1
            project = None
            for ln in group_lines(runs(page_chars(doc[pi], drop_small=False)), tol=3.0):
                first = ln[0]
                if len(ln) == 1 and (m := _PROJECT.search(first.text)):
                    project = m.group(1)
                    headings.append((project, _box(ln)))
                    continue
                if not (re.fullmatch(r"\d{1,3}", first.text) and first.x0 < 70) or len(ln) < 2:
                    continue
                code = ln[-1].text if _MATERIAL.match(ln[-1].text) else None
                body = ln[1:-1] if code else ln[1:]
                joined = " ".join(" ".join(r.text for r in body).split())
                p = _PART.match(joined)
                if not p:
                    warnings.append(f"index row {first.text}: no part number in '{joined[:50]}'")
                    continue
                d = _DIMS.search(p.group(2))
                if not d:
                    warnings.append(f"index row {first.text} ({p.group(1)}): no bore x rod x stroke")
                rows.append({
                    "item_no": first.text, "part_no": p.group(1), "part_no_canon": part_no_canon(p.group(1)),
                    "description": p.group(2), "model_code": code, "make": "", "qty": "", "customer_item_no": "",
                    "rev": "", "remarks": project or "", "page": page_no, "bbox": _box(ln),
                    "dims": [float(d.group(i)) for i in (1, 2, 3)] if d else None,
                })
            break
    finally:
        doc.close()

    specs: dict[str, dict] = {}
    if rows:
        bores = sorted({r["dims"][0] for r in rows if r["dims"]})
        if bores:
            shown = ", ".join(f"{b:g}" for b in bores)
            specs["bore_mm"] = {"value": f"{shown} mm", "numbers": bores, "unit": "mm", "page": page_no,
                                "bbox": _union([r["bbox"] for r in rows])}
        if headings:
            codes = list(dict.fromkeys(h[0] for h in headings))
            specs["projects"] = {"value": ", ".join(codes), "page": page_no, "extra": {"codes": codes},
                                 "bbox": _union([h[1] for h in headings])}
    else:
        warnings.append("index page with part rows not found")
    for r in rows:
        r.pop("dims")
    return {"page": page_no or 1, "specs": specs, "lines": rows, "warnings": warnings}
