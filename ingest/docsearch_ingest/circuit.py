"""Hydraulic-circuit drawing: extract the bottom-left spec box.

Layout (same template on ELECON + SMS drawings):
  left panel  : rows 01-10  (label | value [| label | value])
  middle panel: rows 11-12  (label, value on lines above/below) + "Termination details" table
  right of it : "Note :" list
Everything is label-driven (not coordinate-driven) so it survives A0/A1/A2 page sizes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pypdfium2 as pdfium

from .pdfium_text import Run, group_lines, page_chars, runs

# key -> normalized label text (lowercase alnum only)
LABELS = {
    "project_name": "projectname",
    "customer_drawing_no": "customercircuitdrawingno",
    "design_pressure": "designpressure",
    "working_pressure": "workingpressure",
    "test_pressure": "testpressure",
    "working_fluid": "workingfluid",
    "main_pump_flow": "mainpumpflow",
    "rec_pump_flow": "recpumpflow",
    "open_loop_flow": "openloopflow",
    "solenoid_voltage": "controlvoltageforsolenoid",
    "instrumentation_voltage": "instrumentationvoltage",
    "supply_voltage": "supplyvoltage",
    "tank_material": "tankmaterial",
    "piping_material": "pipingmaterial",
    "fittings_flanges_material": "fittingsflangesmaterial",
    "pipe_dim_standard": "tubepipedimensionalstandard",
    "pipe_material_standard": "tubepipematerialstandard",
    "connection_type": "typeofconnection",
}
NORM2KEY = {v: k for k, v in LABELS.items()}
MULTILINE = {"pipe_dim_standard", "pipe_material_standard", "connection_type"}
NUMERIC = {"design_pressure", "working_pressure", "test_pressure", "main_pump_flow",
           "rec_pump_flow", "open_loop_flow", "solenoid_voltage", "instrumentation_voltage", "supply_voltage"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


@dataclass
class Hit:
    key: str
    i: int
    j: int
    line: list


def _find_labels(line: list[Run]) -> list[Hit]:
    hits: list[Hit] = []
    i = 0
    while i < len(line):
        found = None
        for j in range(i, min(i + 4, len(line))):
            s = norm("".join(r.text for r in line[i:j + 1])).lstrip("0123456789")
            if s in NORM2KEY:
                found = (j, NORM2KEY[s])
                break
        if found:
            hits.append(Hit(found[1], i, found[0], line))
            i = found[0] + 1
        else:
            i += 1
    return hits


def _bbox(rs: list[Run]):
    return [round(min(r.x0 for r in rs), 1), round(min(r.y0 for r in rs), 1),
            round(max(r.x1 for r in rs), 1), round(max(r.y1 for r in rs), 1)]


_NUM = re.compile(r"\d+(?:\.\d+)?")


def parse_numeric(text: str) -> dict:
    """numbers + unit as printed. '250/300 Bar' -> [250,300] 'Bar'."""
    t = text.strip()
    if not t or norm(t) in ("na", "nil", ""):
        return {"numbers": [], "unit": None}
    m = re.match(r"^[~<>]?\s*(\d+(?:\.\d+)?(?:\s*[/+]\s*\d+(?:\.\d+)?)*)\s*([A-Za-z]+)?", t)
    if not m:
        return {"numbers": [], "unit": None}
    nums = [float(x) for x in _NUM.findall(m.group(1))]
    unit = m.group(2)
    sep = "+" if "+" in m.group(1) else ("/" if "/" in m.group(1) else None)
    return {"numbers": nums, "unit": unit, "list_sep": sep}


def fix_inch_fraction(s: str) -> str:
    """pdfium drops the space in mixed fractions: 21/2" -> 2 1/2"; 11/2"SAE6000 -> 1 1/2" SAE6000."""
    s = re.sub(r'(?<![\d/.])(\d)(\d)/(\d)(?=")', r"\1 \2/\3", s)
    return re.sub(r'(")(?=[A-Za-z])', r'\1 ', s)


def extract_circuit(pdf_path: str, page_index: int = 0) -> dict:
    pdf = pdfium.PdfDocument(pdf_path)
    page = pdf[page_index]
    W, H = page.get_size()
    out: dict = {"page": page_index + 1, "page_size": [round(W), round(H)], "specs": {},
                 "terminations": [], "notes": [], "warnings": []}

    chars = [c for c in page_chars(page) if c.y0 > H * 0.60 and c.x0 < W * 0.80]
    hs = sorted(c.y1 - c.y0 for c in chars if not c.t.isspace())
    mh = hs[len(hs) // 2] if hs else 8.9           # median glyph height of this sheet
    s = mh / 8.9                                      # 8.9 = A1 reference sheet
    out["text_height"] = round(mh, 1)
    all_runs = runs(chars)
    lines = group_lines(all_runs, tol=0.4 * mh)
    # pass 2: find the spec box, then drop everything left of it (vertical frame text chains rows)
    pn = next((h for ln in lines for h in _find_labels(ln) if h.key == "project_name"), None)
    if pn:
        lx = pn.line[pn.i].x0 - 40 * s
        # revision-marker triangles contribute lone lowercase letters (a/b/c/d): not data
        keep = [r for r in all_runs if r.x0 >= lx and not (len(r.text) == 1 and r.text.islower())]
        lines = group_lines(keep, tol=0.4 * mh)

    # --- locate labels -------------------------------------------------------
    all_hits: list[Hit] = []
    for ln in lines:
        all_hits += _find_labels(ln)
    by_key: dict[str, Hit] = {}
    for h in all_hits:
        by_key.setdefault(h.key, h)
    if "project_name" not in by_key:
        out["warnings"].append("spec box not found (no 'Project Name' label)")
        return out

    # panel split: middle panel starts left of its first label
    mid_anchor = by_key.get("pipe_material_standard") or by_key.get("connection_type")
    anchor_run = mid_anchor.line[mid_anchor.i] if mid_anchor else None
    split = (anchor_run.x0 - 40 * s) if anchor_run else W * 0.26
    left_x0 = by_key["project_name"].line[by_key["project_name"].i].x0 - 40 * s
    top_y = by_key["project_name"].line[by_key["project_name"].i].y0 - 12 * s

    note_x = None
    for ln in lines:
        for r in ln:
            if norm(r.text) == "note" and r.x0 >= split:
                note_x = r.x0
    mid_hi = (note_x - 3 * s) if note_x else 1e9

    def panel_runs(ln: list[Run], panel: str) -> list[Run]:
        if panel == "L":
            return [r for r in ln if left_x0 <= r.x0 < split]
        return [r for r in ln if split <= r.x0 < mid_hi]

    # --- single-line values (left panel + any labelled row) ------------------
    def label_panel(h: Hit) -> str:
        return "L" if h.line[h.i].x0 < split else "M"

    for key, h in by_key.items():
        ln = panel_runs(h.line, label_panel(h))
        # indices shift after filtering; rebuild using identity
        lab_runs = h.line[h.i:h.j + 1]
        after = [r for r in ln if r.x0 > lab_runs[-1].x1 - 0.5 * s and r not in lab_runs]
        # stop at next label on the same line
        nxt = [hh for hh in _find_labels(ln) if hh.line[hh.i].x0 > lab_runs[-1].x1]
        if nxt:
            stop_x = min(hh.line[hh.i].x0 for hh in nxt)
            after = [r for r in after if r.x0 < stop_x - 0.5]
        if key in MULTILINE:
            after = []
        if after:
            text = " ".join(r.text for r in after)
            out["specs"][key] = {"value": text, "bbox": _bbox(lab_runs + after)}

    # --- multi-line (label centred between value lines) ----------------------
    for key in MULTILINE:
        h = by_key.get(key)
        if not h:
            continue
        lab = h.line[h.i:h.j + 1]
        panel = label_panel(h)
        yc = sum(r.yc for r in lab) / len(lab)
        vals: list[Run] = []
        for ln in lines:
            pr = [r for r in panel_runs(ln, panel) if abs(r.yc - yc) <= 9.5 * s]
            if not pr:
                continue
            if _find_labels(pr):          # a different labelled row
                continue
            cand = [r for r in pr if r.x0 >= lab[-1].x1 - 2 * s and r not in lab]
            # skip the label line itself
            if any(r in lab for r in pr) and not cand:
                continue
            vals += cand
        if vals:
            vals.sort(key=lambda r: (round(r.yc / 4), r.x0))
            text = " ".join(r.text for r in vals)
            out["specs"][key] = {"value": text, "bbox": _bbox(lab + vals)}
        else:
            out["warnings"].append(f"no value found for {key}")

    out["specs"].pop("project_name", None)      # not wanted as a field (customer/job label)
    for key, spec in out["specs"].items():
        spec["value"] = " ".join(spec["value"].split())
        if key in NUMERIC:
            spec.update(parse_numeric(spec["value"]))
            if key.endswith("voltage") and spec["numbers"]:
                spec["unit"] = "V"
                m = re.search(r"\b(AC|DC)\b|V\s*(AC|DC)", spec["value"])
                if m:
                    spec["current"] = m.group(1) or m.group(2)
                f = re.search(r"(\d+(?:\.\d+)?)\s*Hz", spec["value"])
                if f:
                    spec["frequency_hz"] = float(f.group(1))

    # --- termination table --------------------------------------------------
    hdr_line = None
    for ln in lines:
        mp = [r for r in ln if r.x0 >= split]
        names = [r for r in mp if norm(r.text) == "name"]
        if names:
            hdr_line = [r for r in mp]
            break
    if hdr_line:
        cols = []  # (table, colname, x0)
        names = [r for r in hdr_line if norm(r.text) == "name"]
        for t, nm in enumerate(names):
            nxt_name_x = names[t + 1].x0 if t + 1 < len(names) else 1e9
            grp = [r for r in hdr_line if nm.x0 <= r.x0 < nxt_name_x]
            m = {norm(r.text): r for r in grp}
            for cname, cnorm in (("name", "name"), ("size", "size"),
                                 ("connection", "typeofconnection"), ("tube_pipe", "tubepipe")):
                if cnorm in m:
                    cols.append((t, cname, m[cnorm].x0))
        hdr_y = hdr_line[0].yc
        tables = sorted({c[0] for c in cols})
        rows: dict[tuple, dict] = {}
        for ln in lines:
            if ln[0].yc <= hdr_y + 3 * s:
                continue
            mp = [r for r in ln if r.x0 >= split]
            if not mp:
                continue
            for t in tables:
                tc = sorted([c for c in cols if c[0] == t], key=lambda c: c[2])
                if len(tc) < 4:
                    continue
                lo = tc[0][2] - 25 * s
                nxt = [c for c in cols if c[0] == t + 1]
                hi = (tc[-1][2] + nxt[0][2]) / 2 if nxt else tc[-1][2] + 130 * s
                cells = [r for r in mp if lo <= r.x0 < hi]
                if not cells:
                    continue
                if all(re.fullmatch(r"\d", r.text) for r in cells):
                    continue                       # frame grid labels
                row = {c[1]: [] for c in tc}
                bounds = [(tc[k][2] + tc[k + 1][2]) / 2 for k in range(3)]
                for r in cells:
                    k = sum(r.x0 >= b for b in bounds)
                    row[tc[k][1]].append(r)
                if not row["name"] or not (row["size"] or row["connection"]):
                    continue
                rec = {k: " ".join(r.text for r in v) for k, v in row.items()}
                rec["connection"] = fix_inch_fraction(rec["connection"])
                rec["size"] = fix_inch_fraction(rec["size"])
                rec["table"] = "AB"[t] if t < 2 else str(t)
                rec["bbox"] = _bbox([r for v in row.values() for r in v])
                out["terminations"].append(rec)

    # --- notes ---------------------------------------------------------------
    note_run = None
    for ln in lines:
        for r in ln:
            if norm(r.text) == "note" and r.x0 >= split:
                note_run = r
                break
        if note_run:
            break
    if note_run:
        term_title_y = None
        for ln in lines:
            for r in ln:
                if norm(r.text) == "terminationdetails":
                    term_title_y = r.y0
        y_lim = (term_title_y - 2 * s) if term_title_y else H
        cur = None
        for ln in lines:
            for r in ln:
                if r.x0 >= note_run.x0 - 3 and note_run.y1 - 1 <= r.y0 < y_lim and r is not note_run \
                        and norm(r.text) != "":
                    pass
            nr = [r for r in ln if r.x0 >= note_run.x0 - 3 * s and note_run.y1 - s <= r.yc < y_lim
                  and r is not note_run and r.text != ":"]
            if not nr:
                continue
            first = nr[0]
            txt = " ".join(r.text for r in nr)
            if re.fullmatch(r"\d+\.", first.text):
                cur = {"no": first.text.rstrip("."), "text": " ".join(r.text for r in nr[1:])}
                out["notes"].append(cur)
            elif cur:
                cur["text"] += " " + txt
        for n in out["notes"]:
            n["text"] = " ".join(n["text"].split())

    return out
