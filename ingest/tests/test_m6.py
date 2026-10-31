import os
from pathlib import Path

import pytest

from docsearch_ingest.cylbook import extract_cylbook
from docsearch_ingest.jb import extract_jb
from docsearch_ingest.motor import extract_motor

SAMPLE = Path(os.environ.get("DOCSEARCH_ROOT", r"D:\CMF\sample"))
needs_sample = pytest.mark.skipif(not SAMPLE.exists(), reason="sample folder not available")
E = SAMPLE / "ELECON"


# --- motor datasheet -------------------------------------------------------------------------------

@needs_sample
def test_motor_110kw():
    r = extract_motor(str(E / "PP60056-0-AC Motor Datasheet (110kW, CGL).pdf"))
    s = r["specs"]
    assert r["warnings"] == []
    assert s["rated_output_kw"]["numbers"] == [110.0] and s["rated_output_kw"]["value"] == "110 kW"
    assert s["rated_speed_rpm"]["numbers"] == [1490.0]
    assert s["poles"]["numbers"] == [4.0] and "unit" in s["poles"] and s["poles"]["unit"] is None
    assert s["voltage_v"]["numbers"] == [415.0] and s["voltage_v"]["value"].startswith("415 +-10%")
    assert (s["frame"]["value"], s["efficiency_class"]["value"], s["protection_ip"]["value"]) == ("ND315M", "IE3", "IP55")
    assert all(v["page"] == 1 and len(v["bbox"]) == 4 for v in s.values())


@needs_sample
def test_every_motor_datasheet_gives_all_seven_properties():
    files = sorted(E.glob("*Motor Datasheet*.pdf"))
    assert len(files) == 11
    for f in files:
        r = extract_motor(str(f))
        assert len(r["specs"]) == 7 and r["warnings"] == [], f.name
    assert extract_motor(str(E / "PP60056-0-AC Motor Datasheet (18.5kW, CGL).pdf"))["specs"]["rated_output_kw"]["numbers"] == [18.5]


# --- JB cover --------------------------------------------------------------------------------------

@needs_sample
def test_jb_enclosure_changes_between_revisions():
    d0 = extract_jb(str(E / "03-PP60056-0-JB.Doc.pdf"))["specs"]
    da = extract_jb(str(E / "03-PP60056-a-JB.Doc.pdf"))["specs"]
    assert d0["enclosure_size"]["numbers"] == [600.0, 760.0, 210.0]
    assert da["enclosure_size"]["numbers"] == [600.0, 760.0, 350.0]
    assert da["supply_voltage"]["numbers"] == [220.0] and da["supply_voltage"]["current"] == "AC"
    assert da["control_voltage"]["numbers"] == [220.0]      # from "Instrumentation Voltage : 24 V DC, Control Voltage: 220 VAC"


@needs_sample
def test_jb_spelling_variants_and_absent_enclosure():
    assert extract_jb(str(E / "03-PP60057-0-JB.Doc.pdf"))["specs"]["enclosure_size"]["numbers"] == [600.0, 600.0, 210.0]   # "600(W) X 600(H) X 210(D)"
    cyl = extract_jb(str(E / "03-HAS90544-0-JB.Doc.pdf"))
    assert "enclosure_size" not in cyl["specs"] and cyl["warnings"] == []       # cylinder JB: legitimately blank
    assert cyl["specs"]["supply_voltage"]["numbers"] == [110.0]
    assert extract_jb(str(E / "03-HAS90544-a-JB.Doc.pdf"))["specs"]["supply_voltage"]["numbers"] == [220.0]   # "a" marker dropped


@needs_sample
def test_jb_bbox_matches_pdfplumber_positions():
    import pdfplumber
    f = E / "03-PP60056-0-JB.Doc.pdf"
    spec = extract_jb(str(f))["specs"]["enclosure_size"]
    with pdfplumber.open(f) as pdf:
        top = next(w["top"] for w in pdf.pages[0].extract_words() if w["text"] == "Enclosures")
    assert abs(spec["bbox"][1] - top) < 6


# --- cylinder GA book ------------------------------------------------------------------------------

@needs_sample
def test_cylinder_book_index():
    r = extract_cylbook(str(E / "Cylinder GA drawings for C.009132-DBGVL-Rev.c.pdf"))
    assert r["warnings"] == [] and r["page"] == 2 and len(r["lines"]) == 10
    assert [ln["part_no"] for ln in r["lines"][:4]] == ["HA90314", "HA90315", "HAS90264", "HAS90265"]
    assert r["lines"][0]["model_code"] == "ZX11566307" and r["lines"][0]["remarks"] == "PP60056"      # project heading above
    assert next(ln for ln in r["lines"] if ln["part_no"] == "HAS90544")["remarks"] == "PP60057"
    s = r["specs"]
    assert s["bore_mm"]["numbers"] == [32.0, 40.0, 80.0, 125.0, 140.0, 160.0, 180.0]
    assert s["projects"]["extra"]["codes"] == ["PP60056", "PP60057", "PP60058"]


@needs_sample
def test_every_cylinder_book_parses():
    files = sorted(E.glob("Cylinder GA*.pdf"))
    assert len(files) == 5
    for f in files:
        r = extract_cylbook(str(f))
        assert len(r["lines"]) == 10 and r["warnings"] == [], f.name
