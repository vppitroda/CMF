"""Accuracy gate for the hydraulic-circuit extractor against the hand-read golden set (scope §10: >= 98 % of fields)."""
import os
from collections import Counter
from pathlib import Path

import pytest

from docsearch_ingest import golden

SAMPLE = Path(os.environ.get("DOCSEARCH_ROOT", r"D:\CMF\sample"))
needs_sample = pytest.mark.skipif(not SAMPLE.exists(), reason="sample folder not available")


def test_golden_set_covers_both_customers_and_all_three_sheet_sizes():
    import json
    d = json.loads(golden.GOLDEN.read_text(encoding="utf-8"))["drawings"]
    assert len(d) >= 20                                                  # scope: at least 20 drawings
    assert Counter(g["file"].split("/")[0] for g in d).keys() == {"ELECON", "SMS"}
    assert {g["sheet"] for g in d} == {"A0", "A1", "A2"}
    assert len({g["file"] for g in d}) == len(d)
    assert all(set(g["specs"]) <= set(golden_fields()) for g in d)


def golden_fields():
    from docsearch_ingest.circuit import LABELS
    return [k for k in LABELS if k != "project_name"]


@pytest.fixture(scope="module")
def scores():
    return golden.score_all(SAMPLE)


@needs_sample
def test_field_accuracy_meets_the_scope_target(scores):
    sm = golden.summarise(scores)
    assert sm["fields_ok"] / sm["fields"] >= 0.98, golden.markdown(scores)
    assert sm["false_present"] == 0                                      # never invents a field the drawing lacks
    for key, (ok, n) in sm["per_field"].items():                         # and no single field is weak
        assert ok / n >= 0.95, (key, ok, n)


@needs_sample
def test_port_rows_and_notes(scores):
    sm = golden.summarise(scores)
    assert sm["ports_ok"] / sm["ports"] >= 0.98 and sm["ports_extra"] == 0
    assert sm["notes_ok"] / sm["notes"] >= 0.95 and sm["notes_extra"] == 0


@needs_sample
def test_notes_regressions_found_by_the_golden_set(scores):
    by = {s.file.split("/")[-1]: s for s in scores}
    # the notes block runs past the "Termination details" heading: 5 notes on PP60058-c, 4 on the SMS drawings
    assert by["01-PP60058-e-Hyd.Ckt (E+T).pdf"].notes_ok == 5
    assert by["01-HV11495-d-Hyd.Ckt (As Built).pdf"].notes_ok == 4
    # the title block (dates, initials, "Anz./ gepr. am ...") must not be glued onto the last note
    assert all(s.notes_polluted == 0 for s in scores)
