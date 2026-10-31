import glob
import os
from pathlib import Path

import pytest

from docsearch_ingest.aliases import part_no_canon
from docsearch_ingest.bom import COL_EDGES, col_of, expand_reused_on, extract_bom

SAMPLE = Path(os.environ.get("DOCSEARCH_ROOT", r"D:\CMF\sample"))
needs_sample = pytest.mark.skipif(not SAMPLE.exists(), reason="sample folder not available")


def bom(rel: str, category: str) -> dict:
    return extract_bom(str(SAMPLE / rel), category)


# --- pure helpers ---------------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("PP60050 / 53 / 56", ["PP60050", "PP60053", "PP60056"]),     # short numbers replace the trailing digits
    ("PP60053 / 56", ["PP60053", "PP60056"]),
    ("PP60056", ["PP60056"]),
    ("PP60050 / PP60061", ["PP60050", "PP60061"]),                # a full code is kept as is
    ("PP60098 / 101", ["PP60098", "PP60101"]),
])
def test_expand_reused_on(text, expected):
    assert expand_reused_on(text) == expected


def test_columns_follow_the_vertical_rules():
    # x of run starts seen in the sample -> column index
    assert col_of(30) == 0 and col_of(54) == 0          # item no, and the "~" of a range
    assert col_of(72) == 1 and col_of(136) == 2         # customer T.P.No, rev
    assert col_of(162) == 3                              # part no is left-aligned just right of the 156 rule
    assert col_of(235) == 4 and col_of(631) == 5 and col_of(723) == 6 and col_of(745) == 7
    assert col_of(5) is None and col_of(COL_EDGES[-1] + 30) is None


@pytest.mark.parametrize("raw,canon", [
    ("2103-01-18.00 HDN", "2103011800HDN"),
    ("TPN00041", "TPN00041"),
    ("tpn 0004l", "TPN0004L"),                           # only O/0 and I/1 are folded; L is left alone
    ("RM-IOO1", "RM1001"),                                                         # I->1, O->0
])
def test_part_no_canon(raw, canon):
    assert part_no_canon(raw) == canon


# --- real files -----------------------------------------------------------------------------------

@needs_sample
def test_cylinder_title_specs_and_rows():
    r = bom("ELECON/01-HAS90265-a-BOM (Side Clamp Upper Cyl).pdf", "bom_cylinder")
    s = r["specs"]
    assert (s["bore_mm"]["numbers"], s["rod_mm"]["numbers"], s["stroke_mm"]["numbers"]) == ([160.0], [100.0], [360.0])
    assert s["application"]["value"] == "Side Clamp-Upper"
    assert s["options"]["value"] == "MB + JB"
    assert s["make"]["value"] == "Hydac"
    assert s["reused_on"]["extra"]["codes"] == ["PP60050", "PP60053", "PP60056"]
    assert all(len(v["bbox"]) == 4 and v["page"] == 1 for v in s.values())
    assert r["meta"]["part_no"] == "HAS90265" and r["meta"]["rev"] == "a"
    assert len(r["lines"]) == 12 and r["warnings"] == []
    # wrapped part number: "2103-01-18.00" / "HDN"; item range "129.01 ~ 129.02"
    wrapped = [ln for ln in r["lines"] if ln["part_no"].startswith("2103-01-18.00")]
    assert wrapped and wrapped[0]["part_no"] == "2103-01-18.00 HDN"
    assert "129.01~129.02" in [ln["item_no"] for ln in r["lines"]]


@needs_sample
def test_cylinder_title_without_make_or_reuse_list():
    s = bom("ELECON/01-HA90471-a-BOM (Wheel Stopper for E+T).pdf", "bom_cylinder")["specs"]
    assert s["bore_mm"]["numbers"] == [80.0] and s["rod_mm"]["numbers"] == [56.0]
    assert s["application"]["value"] == "Rail Wheel Stopper for Traverser"      # nested "for" kept
    assert "make" not in s and "reused_on" not in s and "options" not in s


@needs_sample
def test_blank_revision_cell_is_not_guessed():
    assert bom("ELECON/01-HAS90543-0-BOM (Top Clamp for WC).pdf", "bom_cylinder")["meta"]["rev"] is None


@needs_sample
def test_rows_wrap_over_lines_and_item_ranges_are_glued():
    r = bom("ELECON/01-PP60056-a-BOM (WT+WC+WG).pdf", "bom_system")
    rows = {(ln["item_no"], ln["part_no"]): ln for ln in r["lines"]}
    assert rows[("001.00", "TPN00041")]["remarks"] == "Pressurise upto 0.2 bar"             # remark wrapped
    assert rows[("005.01~005.02", "TPN00284")]["make"] == "Shridhan Automation"              # make wrapped
    assert ("002.01~002.02", "315219") in rows                                               # "002.01~0" + "02.02"
    assert ("023.03&023.04", "RM23661") in rows                                              # ampersand range
    assert r["specs"]["reservoir_litres"]["numbers"] == [2000.0]


@needs_sample
def test_text_added_in_a_later_revision_is_not_dropped():
    # Regression: pdfium reports the rev-a additions at a different font-size scale; the circuit
    # extractor's "drop small glyphs" filter used to delete them (blank part no. + description).
    r = bom("ELECON/01-PP60056-a-BOM (WT+WC+WG).pdf", "bom_system")
    row = next(ln for ln in r["lines"] if ln["item_no"] == "046.00")
    assert row["part_no"] == "4715862"
    assert row["description"].startswith("4/3 Direction Control Valve")


@needs_sample
def test_bboxes_are_where_the_text_is_on_a_page_with_an_inherited_mediabox():
    # Regression: these BOMs inherit their MediaBox from the /Pages node, pypdfium2 then reports a Letter-sized
    # box and every y was 197 pt too low, so highlights landed below the table. pdfplumber is the oracle.
    import pdfplumber
    rel = "ELECON/01-HAS90264-a-BOM (Platen gripper cyl for WC).pdf"
    r = bom(rel, "bom_cylinder")
    with pdfplumber.open(SAMPLE / rel) as pdf:
        words = pdf.pages[0].extract_words()
        title_y = next(w["top"] for w in words if w["text"] == "HAS90264")          # the "Part No :" line
        row_y = next(w["top"] for w in words if w["text"] == "HA90320")             # first BOM row
    assert abs(r["specs"]["bore_mm"]["bbox"][1] - title_y) < 4
    assert abs(r["lines"][0]["bbox"][1] - row_y) < 4
    assert r["lines"][0]["part_no"] == "HA90320"


@needs_sample
def test_every_sample_bom_parses_cleanly():
    files = sorted(glob.glob(str(SAMPLE / "**" / "*BOM*.pdf"), recursive=True))
    assert len(files) == 38
    from docsearch_ingest.classify import classify
    total = 0
    for f in files:
        c = classify(os.path.relpath(f, SAMPLE))
        r = extract_bom(f, c.category)
        assert r["lines"], f
        assert r["warnings"] == [], (f, r["warnings"])
        assert all(ln["qty"] and ln["part_no"] and ln["description"] for ln in r["lines"]), f
        total += len(r["lines"])
    assert total == 2179
