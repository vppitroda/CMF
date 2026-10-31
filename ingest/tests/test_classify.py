import pytest

from docsearch_ingest.classify import classify, is_junk, resolve, rev_rank

# rel_path -> (category, project_code, revision, application, family_key)
CASES = {
    "ELECON/01-PP60056-d-Hyd.Ckt (WT+WC+WG).pdf": ("hyd_circuit", "PP60056", "d", "WT+WC+WG", "hyd_circuit:PP60056"),
    "ELECON/01-PP60058-d-Hyd.Ckt (E+T) - Copy.pdf": ("hyd_circuit", "PP60058", "d", "E+T", "hyd_circuit:PP60058"),
    "SMS/01-HV11452-c-Hyd.Ckt.pdf": ("hyd_circuit", "HV11452", "c", None, "hyd_circuit:HV11452"),
    "ELECON/01-PP60056-d-BOM (WT+WC+WG).pdf": ("bom_system", "PP60056", "d", "WT+WC+WG", "bom_system:PP60056"),
    "ELECON/01-PP60056-b-BOM.pdf": ("bom_system", "PP60056", "b", None, "bom_system:PP60056"),
    "ELECON/01-HAS90265-a-BOM (Side Clamp Upper Cyl).pdf": ("bom_cylinder", "HAS90265", "a", "Side Clamp Upper Cyl", "bom_cylinder:HAS90265"),
    "ELECON/01-HA90471-a-BOM (Wheel Stopper for E+T).pdf": ("bom_cylinder", "HA90471", "a", "Wheel Stopper for E+T", "bom_cylinder:HA90471"),
    "ELECON/01-HQ60273-0-BOM (SAC).pdf": ("bom_spares", "HQ60273", "0", "SAC", "bom_spares:HQ60273"),
    "SMS/01-HV11495-d-BOM (As Built).pdf": ("bom_valve_stand", "HV11495", "d", "As Built", "bom_valve_stand:HV11495"),
    "ELECON/02-PP60058-b-GA (E+T).PDF": ("ga_drawing", "PP60058", "b", "E+T", "ga_drawing:PP60058"),
    "ELECON/02-HAS90543-0-GA.pdf": ("ga_drawing", "HAS90543", "0", None, "ga_drawing:HAS90543"),
    "ELECON/03-PP60056-0-JB.Doc.pdf": ("jb_doc", "PP60056", "0", None, "jb_doc:PP60056"),
    "ELECON/03-MB5,6,7,8,HAS90264,HAS90265,HAS90266,HAS90543-a-JB.Doc.pdf":
        ("jb_doc", "MB5,6,7,8,HAS90264,HAS90265,HAS90266,HAS90543", "a", None,
         "jb_doc:MB5,6,7,8,HAS90264,HAS90265,HAS90266,HAS90543"),
    "ELECON/PP60056-0-AC Motor Datasheet (110kW, CGL).pdf":
        ("motor_datasheet", "PP60056", "0", "110kW, CGL", "motor_datasheet:PP60056:110kW, CGL"),
    "ELECON/PP60057-0-Electrical Load List.pdf": ("elec_load_list", "PP60057", "0", None, "elec_load_list:PP60057"),
    "ELECON/PP60057-0-IO List.pdf": ("io_list", "PP60057", "0", None, "io_list:PP60057"),
    "ELECON/01-PP60057-0-Operation Write-Up (SAC).pdf": ("operation_writeup", "PP60057", "0", "SAC", "operation_writeup:PP60057"),
    "ELECON/Cylinder GA drawings for C.009132-DBGVL-Rev.c.pdf":
        ("cylinder_ga_book", "C.009132", "c", "DBGVL", "cylinder_ga_book:C.009132:DBGVL"),
    "ELECON/Cylinder GA Drawings for C.009000-Rev.a.pdf":
        ("cylinder_ga_book", "C.009000", "a", None, "cylinder_ga_book:C.009000"),
    "ELECON/Cylinder GA drawings for C.009132-DBGVL.pdf":
        ("cylinder_ga_book", "C.009132", "0", "DBGVL", "cylinder_ga_book:C.009132:DBGVL"),
    "ELECON/01-PP60056-0-CRS.xlsx": ("crs", "PP60056", "0", None, "crs:PP60056"),
    "ELECON/02-HAS90545-CRS Dt 07.02.2023.XLSX": ("crs", "HAS90545", "0", None, "crs:HAS90545"),
    "ELECON/Cylinder GA drawings for C.009132-DBGVL-CRS Dt 10.03.2023.XLSX": ("crs", "C.009132", "0", "DBGVL", None),
    "ELECON/01-PP60056-b-Hyd.Ckt (WT+WC+WG).dwg": ("cad", "PP60056", "b", "WT+WC+WG", None),
    "ELECON/02-HAS90545-a-GA.DWG": ("cad", "HAS90545", "a", None, None),
    "ELECON/02-PP60056-GA (3D-PDF).PDF": ("cad", "PP60056", "0", "3D-PDF", None),   # 3D-PDFs: no text layer
    "ELECON/02-PP60057-0-GA (3d - PDF).PDF": ("cad", "PP60057", "0", "3d - PDF", None),
    "ELECON/02-PP60058-0-GA (e-Drawing).EASM": ("cad", "PP60058", "0", "e-Drawing", None),
    "ELECON/PP60058-Manifold Block Assembly-01/4WE6-D-ASM.SLDPRT": ("cad", "PP60058", None, None, None),
}


@pytest.mark.parametrize("path,exp", CASES.items())
def test_classify(path, exp):
    c = classify(path)
    category, code, rev, app, family = exp
    assert (c.category, c.project_code, c.revision, c.application) == (category, code, rev, app)
    if family:
        assert c.family_key == family


@pytest.mark.parametrize("name", ["ELECON/Thumbs.db", "a/x.dwl", "a/x.dwl2", "ELECON/24BBCE9C.tmp", "a/THUMBS.DB"])
def test_junk_is_ignored(name):
    assert is_junk(name.split("/")[-1])
    assert classify(name) is None


def test_product_class_and_prefix():
    c = classify("ELECON/01-HAS90265-a-BOM (Side Clamp Upper Cyl).pdf")
    assert (c.product_class, c.doc_prefix, c.source_folder, c.kind) == ("HA", "01", "ELECON", "pdf")
    assert classify("SMS/01-PP02123-c-BOM.pdf").product_class == "PP"


def test_unknown_pdf_is_not_dropped():
    assert classify("ELECON/something odd.pdf").category == "unclassified"


def test_rev_rank():
    assert [rev_rank(r) for r in ("0", "a", "b", "e", None)] == [0, 1, 2, 5, 0]


def _docs(paths, sha=None):
    docs = [classify(p) for p in paths]
    return docs, {d.rel_path: (sha or {}).get(d.rel_path, d.rel_path) for d in docs}


def test_latest_revision_per_family_and_application_drift():
    # the -b BOM dropped the "(WT+WC+WG)" suffix; it must still be in the same family as d
    paths = ["ELECON/01-PP60056-b-BOM.pdf", "ELECON/01-PP60056-d-BOM (WT+WC+WG).pdf",
             "ELECON/01-PP60056-a-BOM (WT+WC+WG).pdf"]
    docs, sha = _docs(paths)
    r = resolve(docs, sha)
    assert [p for p, v in r.latest.items() if v] == ["ELECON/01-PP60056-d-BOM (WT+WC+WG).pdf"]


def test_motor_datasheets_of_one_project_are_separate_families():
    paths = ["ELECON/PP60056-a-AC Motor Datasheet (110kW, CGL).pdf", "ELECON/PP60056-0-AC Motor Datasheet (18.5kW, CGL).pdf"]
    docs, sha = _docs(paths)
    assert all(resolve(docs, sha).latest.values())


def test_copy_is_duplicate_of_original_and_never_latest():
    orig, copy = "ELECON/01-PP60058-d-Hyd.Ckt (E+T).pdf", "ELECON/01-PP60058-d-Hyd.Ckt (E+T) - Copy.pdf"
    docs, sha = _docs([copy, orig], {copy: "same", orig: "same"})
    r = resolve(docs, sha)
    assert r.duplicate_of == {copy: orig}
    assert r.latest[copy] is False and r.latest[orig] is True


def test_cad_sibling_links_both_directions_same_folder_only():
    pdf, dwg = "ELECON/01-PP60056-b-Hyd.Ckt (WT+WC+WG).pdf", "ELECON/01-PP60056-b-Hyd.Ckt (WT+WC+WG).dwg"
    other = "SMS/01-PP60056-b-Hyd.Ckt (WT+WC+WG).dwg"      # same name, different folder: not a sibling
    docs, sha = _docs([pdf, dwg, other])
    assert set(resolve(docs, sha).cad_siblings) == {(pdf, dwg), (dwg, pdf)}
