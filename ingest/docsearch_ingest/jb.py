"""Junction-box document (03-…-JB.Doc.pdf): the cover page carries enclosure size, supply voltage and control voltage.

Cover rows look like  label | value  but the value baseline sits a few points off the label's, so rows are
grouped with a wider tolerance than the table extractors use. Revision-marker letters ("a") sit in value cells:
single lowercase runs are dropped (lesson 8). The cylinder JBs print "Enclosures" with no value at all, which is a
legitimate absence (no warning), as is an empty supply voltage.

POC scope: enclosure size, supply voltage, control voltage. The 20-30 pages behind the cover are not parsed.
"""
from __future__ import annotations

import re

import pypdfium2 as pdfium

from .circuit import norm, parse_numeric
from .pdfium_text import Run, group_lines, page_chars, runs

_ENCLOSURE = re.compile(r"(\d+)\s*\(\s*W\s*\)\s*[xX]\s*(\d+)\s*\(\s*H\s*\)\s*[xX]\s*(\d+)\s*\(\s*D\s*\)")
_CONTROL = re.compile(r"Control Voltage\s*:\s*(.+)$", re.I)


def _bbox(rs: list[Run]) -> list[float]:
    return [round(min(r.x0 for r in rs), 1), round(min(r.y0 for r in rs), 1),
            round(max(r.x1 for r in rs), 1), round(max(r.y1 for r in rs), 1)]


def _voltage(text: str) -> dict:
    out = parse_numeric(re.sub(r"(\d)(?=[A-Za-z])", r"\1 ", text))      # "220VAC" -> "220 VAC"
    out["unit"] = "V" if out["numbers"] else None
    m = re.search(r"\b(AC|DC)\b|V\s*(AC|DC)", text, re.I)
    if m:
        out["current"] = (m.group(1) or m.group(2)).upper()
    return out


def extract_jb(pdf_path: str, category: str = "jb_doc") -> dict:
    doc = pdfium.PdfDocument(pdf_path)
    rs = [r for r in runs(page_chars(doc[0], drop_small=False)) if not (len(r.text) == 1 and r.text.islower())]
    lines = group_lines(rs, tol=6.0)
    specs: dict[str, dict] = {}
    warnings: list[str] = []

    for ln in lines:
        lab = ln[0]
        if lab.x0 > 200:                      # label column only (the value cells start near x=270)
            continue
        key = norm(lab.text)
        rest = ln[1:]
        text = " ".join(r.text for r in rest)
        if key == "enclosures" and text:
            m = _ENCLOSURE.search(text)
            if m:
                specs["enclosure_size"] = {"value": " ".join(text.split()), "page": 1, "bbox": _bbox([lab, *rest]),
                                           "numbers": [float(g) for g in m.groups()], "unit": "mm"}
            else:
                warnings.append(f"enclosure size not understood: '{text}'")
        elif key == "supplyvoltage" and text:
            v = _voltage(text)
            if v["numbers"]:
                specs["supply_voltage"] = {"value": text, "page": 1, "bbox": _bbox([lab, *rest]), **v}
        elif key == "controlvoltage" and text:
            m = _CONTROL.search(text)       # "Instrumentation Voltage : 24 V DC, Control Voltage: 220 VAC"
            if m:
                v = _voltage(m.group(1))
                if v["numbers"]:
                    specs["control_voltage"] = {"value": " ".join(m.group(1).split()), "page": 1,
                                                "bbox": _bbox([lab, *rest]), **v}
    if not specs:
        warnings.append("no cover-page values found")
    return {"page": 1, "specs": specs, "lines": [], "warnings": warnings}
