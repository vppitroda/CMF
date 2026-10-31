import pytest

from docsearch_ingest.aliases import canon, split_remark, ws


@pytest.mark.parametrize("raw,expected", [
    ("Minerial ISO VG68", "mineral iso vg68"),          # known typo in the sample
    ("Mineral ISO VG 68", "mineral iso vg68"),
    ("Mineral ISO VG46", "mineral iso vg46"),
    ("315 Bar ( By External Source )", "315 bar"),      # trailing remark stripped
    ("250/300  Bar", "250/300 bar"),
    ("NA", "na"), ("N.A.", "na"), ("-", "na"),
    ("IS 2062 Gr.A", "is 2062 gr.a"),                   # unknown values are kept as-is (lowercased)
    ("Mineral ISO VG-68", "mineral iso vg68"),
    ("230Bar", "230 bar"), ("230  bar", "230 bar"), ("105+105lpm", "105+105 lpm"),
    ("250 / 300 Bar", "250/300 bar"), ("215 + 215 lpm", "215+215 lpm"),
    ("N/A", "na"), ("n.a", "na"), ("NA", "na"),
    ("415 +/-10% V AC, 50Hz", "415 +/-10% v ac, 50 hz"),  # "+/-" is not a list separator
])
def test_canon(raw, expected):
    assert canon(raw) == expected


def test_split_remark():
    assert split_remark("315 Bar ( By External Source )") == ("315 Bar", "By External Source")
    assert split_remark("250/300 Bar") == ("250/300 Bar", None)


def test_ws():
    assert ws("  a \n b\t c ") == "a b c"
