"""Bill-of-material PDFs (bom_system / bom_cylinder / bom_spares / bom_valve_stand).

All sample BOMs share one A4-landscape template (ELECON and SMS): a title block, then a table with the
columns  HIPL T.P.No. | Customer T.P.No. | Rev. | Part No. | Description / Model Code | Make | Qty. | Remarks
whose vertical rules sit at the same x on every file (COL_EDGES). Header row repeats on each page,
footer is "Page n of m".

Row rules (see scope.md §5):
  * A row STARTS on the line that carries a Qty (or a part no. + description). Every other line is a
    continuation of the previous row: it wraps the description, make ("Shridhan" / "Automation"), remarks,
    part no. ("2103-01-18.00" / "HDN") or the second half of an item range.
  * Item ranges are glued from their fragments: "002.01~0" + "02.02", "005.01" + "~" + "005.02".
  * Never guess: a row we cannot make sense of is kept and a warning is recorded.

Lessons from circuit.py apply (pdfium text, runs = cells, keep index order); the page is not rotated here.
"""
from __future__ import annotations

import re

import pypdfium2 as pdfium

from .aliases import part_no_canon
from .pdfium_text import Run, group_lines, page_chars, runs

COLS = ["item_no", "customer_item_no", "rev", "part_no", "description", "make", "qty", "remarks"]
# x of the table's vertical rules (identical on all 38 sample BOMs); a header check warns if a file differs
COL_EDGES = [24, 66, 126, 156, 228, 624, 708, 738, 822]
HEADER_X = {"Rev.": 2, "Part No.": 3, "Description / Model Code": 4, "Make": 5, "Qty.": 6, "Remarks": 7}

# "001.00", "002.01~002.02", "023.03&023.04", "063.01~63.02" (the end of a range sometimes drops its leading 0)
_ITEM_OK = re.compile(r"^\d{3}\.\d{2}(?:[~&,]\d{1,3}\.\d{2})?$")
_FOOTER = re.compile(r"^Page (\d+) of (\d+)$")
_REV_CELL = re.compile(r"^([0-9a-z])\s*[-,]")

# "Ø160 x 100 x 360 mm"; pdfium renders the Ø as U+FFFD, so accept any single non-digit char before the bore
_DIMS = re.compile(r"[^\d\s]?\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*mm", re.I)
_APPLICATION = re.compile(r"\bfor\s+(.+?)\s*(?=\bwith\b|:|$)", re.I)
_OPTIONS = re.compile(r"\bwith\s+(.+?)\s*:", re.I)
_MAKE = re.compile(r"Make-\s*([A-Za-z0-9][A-Za-z0-9 &.]*?)\s*$")
_CODE = r"(?:PP|HAS|HA|HQ|HV)\d+"
_REUSED = re.compile(rf"\(\s*({_CODE}(?:\s*/\s*(?:{_CODE}|\d+))*)\s*\)")
_RESERVOIR = re.compile(r"(\d+(?:\.\d+)?)\s*Ltrs?\b", re.I)

# which title-derived properties each category gets
CYLINDER_PROPS = ("bore_mm", "rod_mm", "stroke_mm", "application", "options", "make", "reused_on")


def expand_reused_on(text: str) -> list[str]:
    """'PP60050 / 53 / 56' -> ['PP60050', 'PP60053', 'PP60056'] (a short number replaces the trailing
    digits of the first code). The strongest reuse signal in the data."""
    parts = [p.strip() for p in text.split("/")]
    first = parts[0]
    out = [first]
    for p in parts[1:]:
        out.append(p if not p.isdigit() else first[: len(first) - len(p)] + p)
    return out


def col_of(x0: float) -> int | None:
    """Column index for a run starting at x0, or None if it is outside the table."""
    if x0 < COL_EDGES[0] - 2 or x0 > COL_EDGES[-1]:
        return None
    for i in range(len(COLS) - 1, -1, -1):
        if x0 >= COL_EDGES[i] - 2:
            return i
    return None


def _union(boxes: list[list[float]]) -> list[float]:
    return [round(min(b[0] for b in boxes), 1), round(min(b[1] for b in boxes), 1),
            round(max(b[2] for b in boxes), 1), round(max(b[3] for b in boxes), 1)]


def _span_bbox(run: Run, a: int, b: int) -> list[float]:
    """bbox of characters a..b of the run's raw text (chars include pdfium's spaces)."""
    cs = [c for c in run.chars[a:b] if not c.t.isspace()]
    return _union([[c.x0, c.y0, c.x1, c.y1] for c in cs])


def _spec(run: Run, m: re.Match, group: int, value: str, **kw) -> dict:
    a, b = m.span(group)
    return {"value": value, "page": 1, "bbox": _span_bbox(run, a, b), **kw}


def parse_title(run: Run, category: str) -> dict:
    """Title-block specs (page 1). Regexes run on the raw character stream so bboxes line up."""
    raw = "".join(c.t for c in run.chars)
    specs: dict[str, dict] = {}

    if category == "bom_cylinder":
        m = _DIMS.search(raw)
        if m:
            for g, key in ((1, "bore_mm"), (2, "rod_mm"), (3, "stroke_mm")):
                n = float(m.group(g))
                specs[key] = _spec(run, m, g, f"{m.group(g)} mm", numbers=[n], unit="mm")
            head = raw[: m.start()]
            a = _APPLICATION.search(head)       # head is a prefix of raw, so group spans index into raw
            if a:
                specs["application"] = _spec(run, a, 1, " ".join(a.group(1).split()))
            o = _OPTIONS.search(head)
            if o:
                specs["options"] = _spec(run, o, 1, " ".join(o.group(1).split()))
        mk = _MAKE.search(raw)
        if mk:
            specs["make"] = _spec(run, mk, 1, mk.group(1))

    if category in ("bom_cylinder", "bom_spares"):
        r = _REUSED.search(raw)
        if r:
            codes = expand_reused_on(" ".join(r.group(1).split()))
            specs["reused_on"] = _spec(run, r, 1, ", ".join(codes), extra={"codes": codes})
    return specs


def _cells(line: list[Run]) -> dict[int, list[Run]]:
    cells: dict[int, list[Run]] = {}
    for r in line:
        c = col_of(r.x0)
        if c is not None:
            cells.setdefault(c, []).append(r)
    return cells


def _text(cells: dict[int, list[Run]], col: int) -> str:
    return " ".join(r.text for r in cells.get(col, []))


def _finish(lines: list[dict[int, list[Run]]], page: int) -> dict:
    item = re.sub(r"\s+", "", "".join(_text(c, 0) for c in lines))
    row = {
        "item_no": item,
        "customer_item_no": " ".join(t for t in (_text(c, 1) for c in lines) if t),
        "rev": " ".join(t for t in (_text(c, 2) for c in lines) if t),
        "part_no": " ".join(t for t in (_text(c, 3) for c in lines) if t),
        "description": " ".join(t for t in (_text(c, 4) for c in lines) if t),
        "make": " ".join(t for t in (_text(c, 5) for c in lines) if t),
        "qty": _text(lines[0], 6),
        "remarks": " ".join(t for t in (_text(c, 7) for c in lines) if t),
        "page": page,
    }
    rs = [r for c in lines for rl in c.values() for r in rl]
    row["bbox"] = _union([[r.x0, r.y0, r.x1, r.y1] for r in rs])
    desc = row["description"]
    row["model_code"] = desc.split(":", 1)[1].strip() if ":" in desc and desc.split(":", 1)[1].strip() else None
    row["part_no_canon"] = part_no_canon(row["part_no"])
    return row


def extract_bom(pdf_path: str, category: str) -> dict:
    """-> {pages, meta:{part_no,rev,title}, specs:{key:{value,page,bbox,...}}, lines:[...], warnings:[...]}"""
    doc = pdfium.PdfDocument(pdf_path)
    n_pdf_pages = len(doc)
    warnings: list[str] = []
    meta: dict = {"part_no": None, "rev": None, "title": None}
    specs: dict[str, dict] = {}
    rows: list[dict] = []
    cur: list[dict[int, list[Run]]] = []
    cur_page = 1
    footer_total = None

    def close():
        nonlocal cur
        if cur:
            rows.append(_finish(cur, cur_page))
        cur = []

    try:
        for pi in range(len(doc)):
            # drop_small=False: text added in a later revision (e.g. "046.00 4/3 Direction Control Valve" in the
            # rev-a system BOMs) is stored at a different font-size scale and would be filtered out as "small".
            # The size filter is only for the circuit drawings' revision-marker letters.
            lines = group_lines(runs(page_chars(doc[pi], drop_small=False)), tol=3.0)
            hdr_y = None
            for ln in lines:
                txt = {r.text: r for r in ln}
                if pi == 0:
                    first = ln[0].text
                    if first.startswith("Part No :") and len(ln) >= 3:
                        meta["part_no"], meta["title"] = ln[1].text, ln[2].text
                        specs.update(parse_title(ln[2], category))
                    elif first.startswith("Rev :") and len(ln) >= 2:
                        m = _REV_CELL.match(ln[1].text)
                        meta["rev"] = m.group(1) if m else None   # blank on rev-0 files: caller uses the filename
                for label, ci in HEADER_X.items():              # layout guard: header text must sit in its column
                    if label in txt and col_of(txt[label].x0) != ci and col_of(txt[label].x0 + 25) != ci:
                        warnings.append(f"p{pi + 1}: header '{label}' not in expected column (layout differs)")
                if any(r.text.startswith("T.P.No.") and r.x0 < 60 for r in ln):
                    hdr_y = ln[0].yc

            if hdr_y is None:
                warnings.append(f"p{pi + 1}: table header not found")
                continue
            cur_page = pi + 1
            for ln in lines:
                if ln[0].yc <= hdr_y + 4:
                    continue
                if len(ln) == 1 and (f := _FOOTER.match(ln[0].text)):
                    footer_total = int(f.group(2))
                    continue
                cells = _cells(ln)
                starts = 6 in cells or (3 in cells and 4 in cells)
                if starts:
                    close()
                    cur_page = pi + 1
                    cur = [cells]
                elif cur:
                    cur.append(cells)
                else:
                    warnings.append(f"p{pi + 1}: text before the first row ignored: {' | '.join(r.text for r in ln)[:60]}")
        close()
    finally:
        doc.close()

    if footer_total is not None and footer_total != n_pdf_pages:
        warnings.append(f"footer says {footer_total} pages but the PDF has {n_pdf_pages}")
    for i, r in enumerate(rows):
        if not _ITEM_OK.match(r["item_no"]):
            warnings.append(f"row {i + 1} (p{r['page']}): odd item no '{r['item_no']}'")
        if not r["qty"]:
            warnings.append(f"row {r['item_no']} (p{r['page']}): no quantity")

    if category == "bom_system":
        for r in rows:
            m = re.match(r"Oil Reservoir\b", r["description"]) and _RESERVOIR.search(r["description"])
            if m:
                specs["reservoir_litres"] = {"value": f"{m.group(1)} Ltrs", "numbers": [float(m.group(1))],
                                             "unit": "Ltrs", "page": r["page"], "bbox": r["bbox"]}
                break
    if not meta["part_no"]:
        warnings.append("title block 'Part No :' not found")
    return {"page": 1, "pages": n_pdf_pages, "meta": meta, "specs": specs, "lines": rows, "warnings": warnings}
