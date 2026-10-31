"""python -m docsearch_ingest <scan|extract|load|report> --root D:\\CMF\\sample --db $DOCSEARCH_DB

Rules (scope.md §7): idempotent; one failing document never aborts the run; never write into the root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import pypdfium2 as pdfium
from psycopg.types.json import Jsonb

from . import aliases, db
from .circuit import NUMERIC, extract_circuit
from .classify import classify, is_junk, resolve
from .props import PROPERTIES

EXTRACTOR_VERSION = {"hyd_circuit": "circuit-1"}
EXTRACTORS = {"hyd_circuit": extract_circuit}
DEFAULT_OUT = Path(__file__).resolve().parents[2] / "out"
DEFAULT_DSN = "postgresql://docsearch:docsearch@localhost:5432/docsearch"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- scan -----------------------------------------------------------------------------------------

DOC_COLS = ["file_name", "ext", "sha256", "size_bytes", "source_folder", "kind", "category", "product_class",
            "project_code", "doc_prefix", "revision", "rev_rank", "application", "family_key", "is_latest"]


def cmd_scan(conn, root: Path, out: Path) -> None:
    docs, sha, size = [], {}, {}
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if is_junk(fn):
                continue
            full = Path(dirpath) / fn
            c = classify(full.relative_to(root).as_posix())
            if c is None:
                continue
            docs.append(c)
            sha[c.rel_path] = _sha256(full)
            size[c.rel_path] = full.stat().st_size
    docs.sort(key=lambda d: d.rel_path)
    res = resolve(docs, sha)

    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in DOC_COLS)
    changed = " OR ".join(f"documents.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in DOC_COLS)
    sql = (f"INSERT INTO documents (rel_path, {', '.join(DOC_COLS)}) VALUES (%s, {', '.join(['%s'] * len(DOC_COLS))}) "
           f"ON CONFLICT (rel_path) DO UPDATE SET {set_clause}, "
           # a changed file must be re-extracted
           "parse_status = CASE WHEN documents.sha256 <> EXCLUDED.sha256 THEN 'pending' ELSE documents.parse_status END, "
           "extract_hash = CASE WHEN documents.sha256 <> EXCLUDED.sha256 THEN NULL ELSE documents.extract_hash END "
           f"WHERE {changed} RETURNING (xmax = 0)")
    inserted = updated = 0
    with conn.cursor() as cur:
        for d in docs:
            vals = [d.file_name, d.ext, sha[d.rel_path], size[d.rel_path], d.source_folder, d.kind, d.category,
                    d.product_class, d.project_code, d.doc_prefix, d.revision, d.rev_rank, d.application,
                    d.family_key, res.latest[d.rel_path]]
            cur.execute(sql, [d.rel_path, *vals])
            row = cur.fetchone()
            if row:
                inserted, updated = inserted + bool(row[0]), updated + (not row[0])

        cur.execute("SELECT rel_path, id FROM documents")
        ids = dict(cur.fetchall())
        gone = [p for p in ids if p not in sha]
        if gone:
            cur.execute("DELETE FROM documents WHERE rel_path = ANY(%s)", (gone,))
            ids = {p: i for p, i in ids.items() if p in sha}

        dup_updates = 0
        for d in docs:
            want = ids[res.duplicate_of[d.rel_path]] if d.rel_path in res.duplicate_of else None
            cur.execute("UPDATE documents SET duplicate_of = %s WHERE id = %s AND duplicate_of IS DISTINCT FROM %s",
                        (want, ids[d.rel_path], want))
            dup_updates += cur.rowcount

        want_links = {(ids[a], ids[b], "cad_sibling") for a, b in res.cad_siblings}
        cur.execute("SELECT from_id, to_id, link_type FROM doc_links WHERE link_type = 'cad_sibling'")
        have = set(cur.fetchall())
        for f, t, lt in have - want_links:
            cur.execute("DELETE FROM doc_links WHERE from_id=%s AND to_id=%s AND link_type=%s", (f, t, lt))
        for f, t, lt in want_links - have:
            cur.execute("INSERT INTO doc_links (from_id, to_id, link_type) VALUES (%s,%s,%s)", (f, t, lt))
    conn.commit()
    print(f"scan: {len(docs)} files | inserted {inserted}, updated {updated}, deleted {len(gone)}, "
          f"duplicate flags changed {dup_updates}, sibling links +{len(want_links - have)} -{len(have - want_links)}")


# --- extract --------------------------------------------------------------------------------------

def _cache_path(out: Path, sha: str) -> Path:
    return out / "extract" / f"{sha}.json"


def cmd_extract(conn, root: Path, out: Path, category: str | None, force: bool) -> None:
    cats = [category] if category else list(EXTRACTORS)
    with conn.cursor() as cur:
        cur.execute("SELECT id, rel_path, sha256, category, extractor_version FROM documents "
                    "WHERE category = ANY(%s) AND duplicate_of IS NULL ORDER BY rel_path", (cats,))
        todo = cur.fetchall()
    done = skipped = 0
    for doc_id, rel, sha, cat, ver in todo:
        if cat not in EXTRACTORS:
            continue
        cache = _cache_path(out, sha)
        if not force and ver == EXTRACTOR_VERSION[cat] and cache.exists():
            skipped += 1
            continue
        status, warnings, pages, payload = "ok", [], None, None
        try:
            payload = EXTRACTORS[cat](str(root / rel))
            warnings = list(payload.get("warnings", []))
            pdf = pdfium.PdfDocument(str(root / rel))
            pages = len(pdf)
            pdf.close()
            status = "failed" if not payload.get("specs") else "partial" if warnings else "ok"
        except Exception as e:  # one bad document must not abort the run
            status, warnings = "failed", [f"EXCEPTION {type(e).__name__}: {e}"]
        if payload is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"category": cat, "extractor_version": EXTRACTOR_VERSION[cat],
                                         "result": payload}, indent=1), encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute("UPDATE documents SET parse_status=%s, parse_warnings=%s, page_count=%s, "
                        "extractor_version=%s, indexed_at=now() WHERE id=%s",
                        (status, Jsonb(warnings), pages, EXTRACTOR_VERSION[cat], doc_id))
        conn.commit()
        done += 1
        print(f"  {status:7s} {rel}")
    print(f"extract: {done} extracted, {skipped} up to date")


# --- load -----------------------------------------------------------------------------------------

def _load_circuit(cur, doc_id: int, r: dict) -> None:
    page = r.get("page")
    for key, v in r["specs"].items():
        if key == "project_name":      # deliberately not emitted (scope §5)
            continue
        text = aliases.ws(v["value"])
        _, remark = aliases.split_remark(text)
        extra = {k: v[k] for k in ("current", "frequency_hz") if v.get(k) is not None}
        if remark:
            extra["remark"] = remark
        cur.execute(
            "INSERT INTO spec_fields (document_id, prop_key, value_text, value_canon, unit, list_sep, extra, page, bbox) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (doc_id, key, text, aliases.canon(text), v.get("unit"), v.get("list_sep"),
             Jsonb(extra) if extra else None, page, Jsonb(v["bbox"])))
        field_id = cur.fetchone()[0]
        if key in NUMERIC:
            for i, n in enumerate(v.get("numbers") or []):
                cur.execute("INSERT INTO spec_numbers (field_id, ord, num) VALUES (%s,%s,%s)", (field_id, i, n))
    for t in r["terminations"]:
        cur.execute("INSERT INTO terminations (document_id, tbl, name, size, connection, tube_pipe, page, bbox) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (doc_id, t.get("table"), t.get("name"), t.get("size"), t.get("connection"), t.get("tube_pipe"),
                     page, Jsonb(t["bbox"]) if t.get("bbox") else None))
    for n in r["notes"]:
        cur.execute("INSERT INTO notes (document_id, no, text, page) VALUES (%s,%s,%s,%s)",
                    (doc_id, n.get("no"), n.get("text"), page))


LOADERS = {"hyd_circuit": _load_circuit}


def cmd_load(conn, out: Path, force: bool) -> None:
    loaded = skipped = 0
    with conn.cursor() as cur:
        for cat, props in PROPERTIES.items():
            for i, (key, label, dtype) in enumerate(props):
                cur.execute("INSERT INTO properties (category, prop_key, label, data_type, sort_order) "
                            "VALUES (%s,%s,%s,%s,%s) ON CONFLICT (category, prop_key) DO UPDATE SET "
                            "label=EXCLUDED.label, data_type=EXCLUDED.data_type, sort_order=EXCLUDED.sort_order "
                            "WHERE (properties.label, properties.data_type, properties.sort_order) "
                            "IS DISTINCT FROM (EXCLUDED.label, EXCLUDED.data_type, EXCLUDED.sort_order)",
                            (cat, key, label, dtype, i))
        cur.execute("SELECT id, sha256, category, extract_hash FROM documents "
                    "WHERE category = ANY(%s) AND duplicate_of IS NULL ORDER BY rel_path", (list(LOADERS),))
        docs = cur.fetchall()
    conn.commit()
    for doc_id, sha, cat, old_hash in docs:
        cache = _cache_path(out, sha)
        if not cache.exists():
            continue
        raw = cache.read_text(encoding="utf-8")
        new_hash = hashlib.sha256(raw.encode()).hexdigest()
        if not force and new_hash == old_hash:
            skipped += 1
            continue
        with conn.cursor() as cur:
            for t in ("spec_fields", "terminations", "notes"):    # spec_numbers cascades from spec_fields
                cur.execute(f"DELETE FROM {t} WHERE document_id = %s", (doc_id,))
            LOADERS[cat](cur, doc_id, json.loads(raw)["result"])
            cur.execute("UPDATE documents SET extract_hash = %s WHERE id = %s", (new_hash, doc_id))
        conn.commit()
        loaded += 1
    print(f"load: {loaded} documents loaded, {skipped} unchanged")


# --- report ---------------------------------------------------------------------------------------

def cmd_report(conn, out: Path) -> None:
    lines = ["# Docsearch extraction report", ""]
    with conn.cursor() as cur:
        cur.execute("SELECT category, count(*), count(*) FILTER (WHERE duplicate_of IS NOT NULL), "
                    "count(*) FILTER (WHERE parse_status='ok'), count(*) FILTER (WHERE parse_status='partial'), "
                    "count(*) FILTER (WHERE parse_status='failed') FROM documents GROUP BY category ORDER BY category")
        lines += ["## Documents per category", "", "| category | files | duplicates | ok | partial | failed |",
                  "|---|---|---|---|---|---|"]
        lines += [f"| {' | '.join(map(str, r))} |" for r in cur.fetchall()]
        for cat, props in PROPERTIES.items():
            cur.execute("SELECT count(*) FROM documents WHERE category=%s AND duplicate_of IS NULL", (cat,))
            total = cur.fetchone()[0]
            lines += ["", f"## Field coverage: {cat} ({total} documents)", "", "| property | documents |", "|---|---|"]
            for key, label, _ in props:
                cur.execute("SELECT count(*) FROM spec_fields f JOIN documents d ON d.id=f.document_id "
                            "WHERE d.category=%s AND d.duplicate_of IS NULL AND f.prop_key=%s", (cat, key))
                lines.append(f"| {key} | {cur.fetchone()[0]}/{total} |")
        cur.execute("SELECT rel_path, parse_status, parse_warnings FROM documents "
                    "WHERE parse_status IN ('partial','failed') ORDER BY rel_path")
        bad = cur.fetchall()
        cur.execute("SELECT category, rel_path FROM documents WHERE category='unclassified' ORDER BY rel_path")
        unclassified = cur.fetchall()
    lines += ["", "## Partial / failed documents", ""]
    lines += [f"- `{p}` **{s}** {json.dumps(w)}" for p, s, w in bad] or ["none"]
    lines += ["", "## Unclassified files", ""]
    lines += [f"- `{p}`" for _, p in unclassified] or ["none"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report: wrote {out / 'report.md'}")


# --- entry ----------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="docsearch_ingest")
    ap.add_argument("command", choices=["scan", "extract", "load", "report"])
    ap.add_argument("--root", default=os.environ.get("DOCSEARCH_ROOT"), help="source folder (read-only)")
    ap.add_argument("--db", default=os.environ.get("DOCSEARCH_DB", DEFAULT_DSN))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--category")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    if a.command in ("scan", "extract") and not a.root:
        ap.error("--root or DOCSEARCH_ROOT is required")
    root = Path(a.root) if a.root else None

    with db.connect(a.db) as conn:
        db.migrate(conn)
        if a.command == "scan":
            cmd_scan(conn, root, out)
        elif a.command == "extract":
            cmd_extract(conn, root, out, a.category, a.force)
        elif a.command == "load":
            cmd_load(conn, out, a.force)
        else:
            cmd_report(conn, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
