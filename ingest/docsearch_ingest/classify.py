"""Filename rules -> category, revision, family, duplicates, CAD siblings (scope.md §3).

Pure functions only (no I/O) so the whole table is unit-testable. Content is primary and the
filename is only a hint; mismatches are logged later by the extractors.
File mtimes are never used (all SMS files share a copy timestamp).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath, PureWindowsPath

JUNK_EXT = {".dwl", ".dwl2", ".tmp"}
JUNK_NAMES = {"thumbs.db"}
CAD_EXT = {".dwg", ".sldprt", ".sldasm", ".easm"}

# One project code can carry several distinct documents of these categories (e.g. a 110kW and an
# 18.5kW motor datasheet). Elsewhere the application is NOT part of the family, because a drawing
# often drops/changes it between revisions (01-PP60056-b-BOM.pdf vs -a-BOM (WT+WC+WG).pdf).
APP_IN_FAMILY = {"motor_datasheet", "cylinder_ga_book"}

_CODE = r"(?:PP|HAS|HA|HQ|HV)\d+"
_PREFIXED = re.compile(rf"^(?:(?P<prefix>\d{{2}})-)?(?P<code>{_CODE})(?:-(?P<rev>0|[a-z]))?-(?P<rest>.+)$")
_JB = re.compile(r"^(?P<prefix>\d{2})-(?P<code>.+)-(?P<rev>0|[a-z])-JB\.Doc$")
_CODE_IN_PATH = re.compile(_CODE)
_PAREN_TAIL = re.compile(r"\s*\(([^()]*)\)\s*$")
_COPY = re.compile(r"\s+-\s+copy$", re.I)
_3D_PDF = re.compile(r"3d\s*-?\s*pdf", re.I)
_CYL_BOOK_CODE = re.compile(r"\bC\.\d+")
_CYL_BOOK_REV = re.compile(r"-Rev\.([a-z])", re.I)
_CYL_BOOK_APP = re.compile(r"C\.\d+-([A-Za-z]+)(?=-|\.|$)")

PRODUCT_CLASS = {"PP": "PP", "HAS": "HA", "HA": "HA", "HQ": "HQ", "HV": "HV"}
BOM_CATEGORY = {"PP": "bom_system", "HA": "bom_cylinder", "HQ": "bom_spares", "HV": "bom_valve_stand"}


@dataclass
class Classified:
    rel_path: str
    file_name: str
    ext: str                       # lowercase, with dot
    source_folder: str | None
    kind: str                      # pdf | xlsx | cad
    category: str
    product_class: str | None = None
    project_code: str | None = None
    doc_prefix: str | None = None
    revision: str | None = None
    rev_rank: int = 0
    application: str | None = None
    family_key: str = ""
    is_copy_name: bool = False     # "... - Copy.pdf": prefer the other file as the original


def is_junk(file_name: str) -> bool:
    n = file_name.lower()
    return n in JUNK_NAMES or PureWindowsPath(n).suffix in JUNK_EXT


def rev_rank(rev: str | None) -> int:
    """'0' < 'a' < 'b' ...; unknown -> 0."""
    if not rev or rev == "0":
        return 0
    return ord(rev.lower()) - ord("a") + 1


def product_class_of(code: str | None) -> str | None:
    m = re.match(r"[A-Z]+", code or "")
    return PRODUCT_CLASS.get(m.group(0)) if m else None


def _category(kind: str, ext: str, name: str, rest: str, pclass: str | None, is_jb: bool) -> str:
    """First match wins (scope §3)."""
    if kind == "xlsx":
        return "crs"
    if kind == "cad":
        return "cad"
    if _3D_PDF.search(name):          # 3D-PDFs have no text layer: link only
        return "cad"
    low = name.lower()
    if "hyd.ckt" in low:
        return "hyd_circuit"
    if rest.upper().startswith("BOM"):
        return BOM_CATEGORY.get(pclass or "", "unclassified")
    if low.startswith("cylinder ga"):
        return "cylinder_ga_book"
    if is_jb:
        return "jb_doc"
    if "motor datasheet" in low:
        return "motor_datasheet"
    if "electrical load list" in low:
        return "elec_load_list"
    if re.search(r"\bio list\b", low):
        return "io_list"
    if "operation write-up" in low:
        return "operation_writeup"
    if re.match(r"GA\b", rest, re.I):
        return "ga_drawing"
    return "unclassified"


def classify(rel_path: str) -> Classified | None:
    """Classify one file by its path relative to DOCSEARCH_ROOT. Returns None for junk."""
    p = PureWindowsPath(rel_path)
    file_name, ext = p.name, p.suffix.lower()
    if is_junk(file_name):
        return None
    parts = p.parts
    source_folder = parts[0] if len(parts) > 1 else None
    kind = "pdf" if ext == ".pdf" else "xlsx" if ext == ".xlsx" else "cad" if ext in CAD_EXT else "other"
    stem = p.stem
    copy = bool(_COPY.search(stem))
    stem = _COPY.sub("", stem)

    code = prefix = rev = app = None
    rest = stem
    is_jb = False

    if stem.lower().startswith("cylinder ga"):
        m = _CYL_BOOK_CODE.search(stem)
        code = m.group(0) if m else None
        r = _CYL_BOOK_REV.search(stem)
        rev = r.group(1).lower() if r else "0"
        a = _CYL_BOOK_APP.search(stem)
        app = a.group(1) if a and a.group(1).lower() != "rev" else None
    elif (m := _JB.match(stem)):
        is_jb = True
        prefix, code, rev = m["prefix"], m["code"], m["rev"]
        rest = "JB.Doc"
    elif (m := _PREFIXED.match(stem)):
        prefix, code, rev, rest = m["prefix"], m["code"], m["rev"] or "0", m["rest"]
        t = _PAREN_TAIL.search(rest)
        if t:
            app = t.group(1).strip()
            rest = rest[: t.start()].strip()

    if code is None and kind == "cad":  # SolidWorks parts: project comes from the folder name
        for part in reversed(parts[:-1]):
            f = _CODE_IN_PATH.search(part)
            if f:
                code = f.group(0)
                break

    pclass = product_class_of(code)
    category = _category(kind, ext, stem, rest, pclass, is_jb)

    # family: revisions of "the same thing" share a key
    if kind == "cad":
        # cad files are only compared with other revisions of the same drawing (dwg for rev b vs e)
        key = f"cad:{code}:{rest.lower()}" if prefix and code else f"cad:{stem.lower()}"
        key += f"|{ext}"
    elif code:
        key = f"{category}:{code}"
        if app and category in APP_IN_FAMILY:
            key += f":{app}"
    else:
        key = f"{category}:{stem.lower()}"

    return Classified(
        rel_path=rel_path.replace("\\", "/"), file_name=file_name, ext=ext, source_folder=source_folder,
        kind=kind, category=category, product_class=pclass, project_code=code, doc_prefix=prefix,
        revision=rev, rev_rank=rev_rank(rev), application=app, family_key=key, is_copy_name=copy,
    )


# --- cross-document rules -------------------------------------------------------------------------

@dataclass
class Resolved:
    duplicate_of: dict[str, str] = field(default_factory=dict)    # rel_path -> rel_path of the original
    latest: dict[str, bool] = field(default_factory=dict)         # rel_path -> is_latest
    cad_siblings: list[tuple[str, str]] = field(default_factory=list)   # (rel_path, rel_path), both directions


def resolve(docs: list[Classified], sha256: dict[str, str]) -> Resolved:
    """Duplicates by sha256, is_latest by highest revision per family, CAD siblings by filename stem."""
    out = Resolved()

    by_sha: dict[str, list[Classified]] = {}
    for d in docs:
        by_sha.setdefault(sha256[d.rel_path], []).append(d)
    for group in by_sha.values():
        group.sort(key=lambda d: (d.is_copy_name, d.rel_path))
        for dup in group[1:]:
            out.duplicate_of[dup.rel_path] = group[0].rel_path

    fam: dict[str, int] = {}
    for d in docs:
        if d.rel_path not in out.duplicate_of:
            fam[d.family_key] = max(fam.get(d.family_key, 0), d.rev_rank)
    for d in docs:
        out.latest[d.rel_path] = d.rel_path not in out.duplicate_of and d.rev_rank == fam[d.family_key]

    # sibling = same folder + same stem, different extension (…Hyd.Ckt (SAC).pdf <-> .dwg)
    by_stem: dict[tuple[str, str], list[Classified]] = {}
    for d in docs:
        if d.rel_path in out.duplicate_of:
            continue
        folder = str(PurePosixPath(d.rel_path).parent)
        by_stem.setdefault((folder, PurePosixPath(d.rel_path).stem.lower()), []).append(d)
    for group in by_stem.values():
        for a in group:
            for b in group:
                if a is not b and "cad" in (a.kind, b.kind):
                    out.cad_siblings.append((a.rel_path, b.rel_path))
    return out
