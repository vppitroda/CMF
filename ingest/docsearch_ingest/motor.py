"""Motor datasheet (CG Power "DATA SHEET OF 3 PHASE INDUCTION MOTOR"): a two-column key/value grid on page 1.

Each grid line reads  label | value [| label | value]. Label-driven, like circuit.py: find the label run, the value is
the next run to its right on the same line. The POC keeps only the properties an engineer filters on
(power, speed, poles, frame, voltage, efficiency class, protection); everything else on the sheet is ignored.
Customer / project / enquiry lines are deliberately not extracted (scope §1).
"""
from __future__ import annotations

import re

import pypdfium2 as pdfium

from .circuit import norm, parse_numeric
from .pdfium_text import Run, group_lines, page_chars, runs

# key -> (normalised label, unit for numeric fields or None)
FIELDS: dict[str, tuple[str, str | None]] = {
    "rated_output_kw": ("ratedoutputkw", "kW"),
    "rated_speed_rpm": ("ratedspeedrpm", "rpm"),
    "poles": ("noofpoles", ""),
    "frame": ("frame", None),
    "voltage_v": ("voltagev", "V"),
    "efficiency_class": ("efficiency", None),       # "IE3 - 95.4 %" -> IE3
    "protection_ip": ("degreeofprotection", None),
}
NUMERIC = {k for k, (_, u) in FIELDS.items() if u is not None}
_LABEL_TO_KEY = {lab: k for k, (lab, _) in FIELDS.items()}
_IE = re.compile(r"\bIE\s?\d\b", re.I)


def _bbox(rs: list[Run]) -> list[float]:
    return [round(min(r.x0 for r in rs), 1), round(min(r.y0 for r in rs), 1),
            round(max(r.x1 for r in rs), 1), round(max(r.y1 for r in rs), 1)]


def extract_motor(pdf_path: str, category: str = "motor_datasheet") -> dict:
    doc = pdfium.PdfDocument(pdf_path)
    try:
        # drop_small=False: see bom.py (font-size scale is arbitrary per text object)
        lines = group_lines(runs(page_chars(doc[0], drop_small=False)), tol=3.0)
    finally:
        pass
    specs: dict[str, dict] = {}
    warnings: list[str] = []
    for ln in lines:
        for i, r in enumerate(ln[:-1]):
            key = _LABEL_TO_KEY.get(norm(r.text))
            if key is None or key in specs:
                continue
            val = ln[i + 1]
            text = val.text
            spec: dict = {"value": text, "page": 1, "bbox": _bbox([r, val])}
            if key == "efficiency_class":
                m = _IE.search(text)
                if not m:
                    warnings.append(f"efficiency '{text}' has no IE class")
                    continue
                spec["value"] = m.group(0).upper().replace(" ", "")
            elif key in NUMERIC:
                parsed = parse_numeric(text)
                if not parsed["numbers"]:
                    warnings.append(f"{key}: no number in '{text}'")
                    continue
                unit = FIELDS[key][1] or None
                spec.update(numbers=parsed["numbers"], unit=unit)
                if unit:                      # the unit is in the label "Rated Output (kW)", not in the cell
                    spec["value"] = f"{text} {unit}"
            specs[key] = spec
    missing = [k for k in FIELDS if k not in specs]
    if missing:
        warnings.append("missing: " + ", ".join(missing))
    return {"page": 1, "specs": specs, "lines": [], "warnings": warnings}
