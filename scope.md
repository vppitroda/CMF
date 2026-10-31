# Docsearch POC — Project Scope

> Audience: Claude Code (and humans) implementing this repo. Read this file first, then `docs/schema.md`.
> Status date: 2026-10-30. Owner: Vijay. Repo root: `D:\CMF\Docsearch`.

---

## 1. Problem and goal

Customer engineers at a hydraulics-product manufacturer re-create designs from scratch because the
existing drawings, BOMs and spec sheets are a disorganised mess of files. We are building a **search tool that
helps them find reusable designs** instead.

This is a **proof of concept to win the contract**. If it works, it moves to an Azure VM for further development.
Optimise for a convincing demo on the real sample data, not polish.

### What "search" means here (decided with the user)
A four-step cascading filter, not a chat box:

1. **Category** — e.g. Hydraulic circuit, Cylinder BOM, System BOM, Motor datasheet
2. **Property** — only properties that exist for that category (e.g. Design pressure)
3. **Value** — the distinct values actually found in the indexed documents, with counts (clickable)
4. **Search box** — type a value; return documents whose value is **nearest** to it

Example: Category = Hydraulic circuit → Property = Design pressure → type `223` → documents ranked by closeness
(a 230 Bar drawing ranks above a 250/300 Bar one). Values are compared **in the unit printed in the document**;
there is no unit conversion layer.

A plain free-text keyword search (fuzzy) over the same data is a later milestone (§11, M7).

### Explicit non-goals
- No customer-name or date filters. (Customer and project names are not fields. Dates are ignored.)
- No parsing of CAD geometry (DWG / SolidWorks / eDrawing / 3D-PDF) — these are **linked** only.
- No LLM / RAG / embeddings in the core path. Extraction is rule-based. (pgvector and a local VLM are optional later.)
- No authentication, no multi-tenancy, no polish for the POC.
- No hydraulics-domain reasoning. We treat the content as text and numbers.

---

## 2. Environment and stack (frozen)

| Layer | Choice |
|---|---|
| Host OS | Windows. Python / .NET / Node run on the host. |
| Database | PostgreSQL (`docker pull postgres`, latest) + `pg_trgm`. pgvector deferred. pgAdmin bundled. |
| Ingestion | Python 3.12, **own venv** at `D:\CMF\Docsearch\.venv` (do NOT use `D:\Ai\gpu-env`; it is a shared image-gen env) |
| API | .NET 10 standard Web API (controller classes + contract methods/DTOs), Npgsql + Dapper, no auth |
| UI | Angular (standalone components) + pdf.js viewer (`ngx-extended-pdf-viewer`) |
| Docker | Compose: `db` + `pgadmin` only. API/UI/ingest run on the host for fast iteration. |

Python deps (`requirements.txt`): `pdfplumber`, `pypdfium2`, `openpyxl`, `rapidfuzz`, `psycopg[binary]`.
**Use pypdfium2 for all PDF text** (see §4 lessons). pdfplumber is only for optional ruling-line geometry.
**Do not use PyMuPDF** (AGPL).

Services after `docker compose up -d`:
- Postgres `localhost:5432` db/user/password all `docsearch`
- pgAdmin `http://localhost:5050` (no login; server "docsearch (POC)" pre-registered)

Optional later: `D:\Ai\Models\qwen3-vl-8b-instruct` (≈17.5 GB bf16) as a fallback for spec boxes the rules cannot parse.
Dev machine: RTX 5090 24 GB. The Azure dev VM has 16 GB, so that model would need quantisation or the 4B variant.

Design for an eventual air-gapped deployment: **no runtime CDN calls** in the UI (bundle the pdf.js worker),
pin all dependency versions, no telemetry.

### Config (env / appsettings)
| Key | Meaning |
|---|---|
| `DOCSEARCH_ROOT` | Folder containing the source files (`D:\CMF\sample`). Read-only. |
| `DOCSEARCH_DB` | `postgresql://docsearch:docsearch@localhost:5432/docsearch` |

---

## 3. Source data (what is actually in `D:\CMF\sample`)

201 files in two subfolders: `ELECON/` (Metso Outotec projects) and `SMS/`.

| Type | Count | Notes |
|---|---|---|
| PDF | 117 | almost all have a real text layer; **3D-PDFs (3 files) and one scanned GA (`02-HAS90543-0-GA.pdf`) have none** |
| xlsx | 36 | **all are Comments Review Sheets (CRS)** — customer comment/reply logs, NOT BOMs |
| CAD | 41 | 16 `.dwg`, 19 `.sldprt/.sldasm`, 3 `.easm`, plus the 3 3D-PDFs |
| junk | 10 | `.dwl .dwl2 .tmp Thumbs.db` — **ignore** |

### Filename convention → free metadata
`NN-<ProjectCode>-<rev>-<Type> (<application>).ext`

- `NN`: `01` BOM or Hyd.Ckt, `02` GA, `03` JB doc
- `ProjectCode` prefix = product class: `PP` complete hydraulic system / power unit, `HA`/`HAS` cylinder assembly,
  `HQ` commissioning spares, `HV` valve stand
- `rev`: `0`, then `a`, `b`, `c` …
- Examples:
  `01-PP60056-d-BOM (WT+WC+WG).pdf`, `01-HAS90265-a-BOM (Side Clamp Upper Cyl).pdf`,
  `01-PP60056-b-Hyd.Ckt (WT+WC+WG).pdf`, `02-PP60058-b-GA (E+T).PDF`, `03-PP60056-0-JB.Doc.pdf`,
  `03-MB5,6,7,8,HAS90264,…-0-JB.Doc.pdf` (multi-project), `PP60056-0-AC Motor Datasheet (110kW, CGL).pdf`,
  `PP60057-0-Electrical Load List.pdf`, `PP60057-0-IO List.pdf`, `01-PP60057-0-Operation Write-Up (SAC).pdf`,
  `Cylinder GA drawings for C.009132-DBGVL-Rev.c.pdf`, `01-PP60056-0-CRS.xlsx`,
  `02-HAS90545-CRS Dt 07.02.2023.XLSX`
- **Filenames and content can disagree** (e.g. the PP60057 write-up says `Document No.: PP60051` inside; CRS filenames
  have wrong years; `HA90471` vs `HAS90545` for the same item). Content is primary, filename is a hint; log mismatches.
- File mtimes are unreliable (all SMS files share a copy timestamp). Do not use them.
- Exact duplicate exists: `01-PP60058-d-Hyd.Ckt (E+T) - Copy.pdf` (same sha256 as the non-Copy file).

### Categories (rule-based; first match wins)
| `category` | Rule | Count |
|---|---|---|
| `hyd_circuit` | name contains `Hyd.Ckt` and ext pdf | 24 |
| `bom_system` | `BOM` + project code `PP…` | 18 |
| `bom_cylinder` | `BOM` + `HA…`/`HAS…` | 10 |
| `bom_spares` | `BOM` + `HQ…` | 7 |
| `bom_valve_stand` | `BOM` + `HV…` | 3 |
| `ga_drawing` | `-GA` pdf (not 3D) | 12 |
| `cylinder_ga_book` | starts with `Cylinder GA` | 5 |
| `jb_doc` | `JB.Doc` | 15 |
| `motor_datasheet` | `Motor Datasheet` | 11 |
| `elec_load_list` / `io_list` | by name | 3 / 3 |
| `operation_writeup` | `Operation Write-Up` | 3 |
| `crs` | xlsx | 36 |
| `cad` | dwg/dwl-free, sldprt, sldasm, easm, 3D pdf | 41 |
| `unclassified` | fallback; never drop silently | — |

### Revisions and duplicates
- `family_key` = `category:project_code` (plus `:application` where one project code has several docs).
- Within a family, `is_latest` = highest revision (`0` < `a` < `b` …). Search shows latest only by default;
  `includeOld=true` shows all.
- Identical `sha256` → `duplicate_of` the earlier document; excluded from results.

### Sibling links
Link by filename stem across extensions (`…Hyd.Ckt (WT+WC+WG).pdf` ↔ `.dwg`). SolidWorks parts in
`PP60058-Manifold Block Assembly-01/` link to project `PP60058` and are findable by filename (vendor model codes
like `4WE6`, `DB3E`). Results must show sibling CAD files so an engineer can open the editable source.

---

## 4. Extraction — what is DONE and verified, and the lessons that must be preserved

### Already implemented (do not rewrite; extend)
- `ingest/docsearch_ingest/pdfium_text.py` — char/run text layer.
- `ingest/docsearch_ingest/circuit.py` — hydraulic-circuit spec box extractor.
- `ingest/run_circuits.py` — runs it over the sample, writes `out/circuits.json` + coverage report.

**Result:** 24/24 circuit drawings parse; 15 of 17 fields at 24/24, the other two are real absences
(`tank_material` 21/24: valve stands have no tank; `rec_pump_flow` 19/24 + `open_loop_flow` 5/24 = 24: PP60057
uses "Open Loop Flow"). 186 port-table rows. ~0.1 s per drawing. Visually verified on 3 drawings
(PP60056-d, PP60057-d, PP02123-d): every field and every port matched. **No hand-verified ground-truth set yet
(see M8).**

### Lessons learned (each one cost real debugging; keep them in code comments/tests)
1. **pdfminer/pdfplumber drop `/` and `%`** from these PDFs (`250/300 Bar` → `250300 Bar`). pdfium reads them correctly.
2. **14 of 24 circuit sheets are `/Rotate 270`** (A0 stored portrait). Map pdfium's user-space boxes to the displayed
   orientation (`_view_mapper`) or text lands off-page.
3. **Faux-bold overprint**: text is drawn 2–3× — dedupe identical glyphs at the same position.
4. **Never sort chars by x.** pdfium's own space characters are in correct *index* order but have bogus x boxes.
   Keep index order; split into *runs* where position jumps. A run ≈ a table cell.
5. **Scale every distance threshold by glyph height** (median ≈ 6.3 pt on A2, 8.9 on A1, 13.1 on A0).
6. Label matching: normalise to lowercase alphanumerics and match across up to 4 adjacent runs
   (`"Control"` + `"Voltage for Solenoid"`).
7. Line clustering: compare to the line's running mean, and drop the vertical frame text at the left margin
   (found by anchoring on the `Project Name` row first) or it chains rows together.
8. Revision-marker triangles inject lone lowercase letters (`a b c d`): drop single lowercase runs inside the box.
9. Mixed fractions lose their space (`21/2"` → `2 1/2"`): repaired for port sizes/connections.
10. Font sizes from pdfium are scaled and meaningless in absolute terms; use only relatively.
11. The **port-table columns mean different things per template**: ELECON `size` = tube OD × wall and `connection` = SAE/G thread;
12. **pypdfium2 reports a Letter box (0,0,612,792) when the page has no MediaBox/CropBox of its own** (inherited from the `/Pages`
    node - all the A4 BOMs). Every y then came out 197 pt too low. `_view_mapper` now uses `get_*box(fallback_ok=False)` and falls
    back to `page.get_size()`. Test against an independent oracle (pdfplumber word positions), not just "a highlight appears".
13. **Do not apply the "drop small glyphs" filter to BOMs** (`page_chars(drop_small=False)`): text added in a later revision is stored
    at a different font-size scale and was silently deleted (blank part no. + description on rev-a rows). Only the circuit
    drawings' revision-marker letters need that filter.
14. BOM item ranges come in several spellings: `002.01~002.02`, `023.03&023.04`, `063.01~63.02`; they wrap (`002.01~0` / `02.02`).
    A BOM row starts on the line that carries a Qty; everything else is a continuation (see `bom.py`).
    SMS `size` = thread/flange, `connection` = flange type, `tube_pipe` = Ø × wall. Store as printed; normalise later.

### Each extracted value stores
`page` (1-based), `bbox` `[x0,y0,x1,y1]` in PDF points, top-left origin, **displayed orientation, scale 1**.
The UI uses it to jump to and highlight the value in the PDF viewer.

---

## 5. Properties per category (the schema the filters are built from)

Generic rule: a property is either `number` (stored as a list of numbers + the printed unit) or `text`.
`list_sep` records `/` or `+` for multi-value fields (`250/300 Bar`, `215+215 lpm`).

### hyd_circuit — implemented
`customer_drawing_no`(text), `design_pressure`, `working_pressure`, `test_pressure`, `main_pump_flow`, `rec_pump_flow`,
`open_loop_flow` (numbers), `solenoid_voltage`, `instrumentation_voltage`, `supply_voltage` (number, unit `V`, plus
`current` AC/DC and `frequency_hz`), `working_fluid`, `tank_material`, `piping_material`, `fittings_flanges_material`,
`pipe_dim_standard`, `pipe_material_standard`, `connection_type` (text), plus `terminations[]`
(`name,size,connection,tube_pipe,table`) and `notes[]` (`no,text`). `project_name` is deliberately **not** emitted.

### bom_cylinder (HA*/HAS*) — to build, M5
Title line example: `Hydraulic Cylinder for Side Clamp-Upper with MB + JB : Ø160 x 100 x 360 mm Stroke (PP60050 / 53 / 56). Make-Hydac`
- `bore_mm`, `rod_mm`, `stroke_mm` ← regex `Ø(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*mm`
- `application` (text) ← words after `for`, before `with`/`:`
- `options` (text) ← `with MB + JB`, `with Manifold Block Assembly`
- `make` ← `Make-<x>`
- `reused_on[]` ← `(PP60050 / 53 / 56)` → `PP60050, PP60053, PP60056` (expand each short suffix by replacing the trailing digits
  of the first code). **This is the strongest reuse signal in the data.**
- Plus the BOM rows (below).

### BOM rows (all `bom_*`) — to build, M5
Columns: `HIPL T.P.No. | Customer T.P.No. | Rev. | Part No. | Description / Model Code | Make | Qty. | Remarks`.
- Header per page: title block with `Part No : <code> <title>`, `Rev : <letter> - Dt …`; footer `Page n of m`; header row repeats each page.
- Item numbers look like `001.00`, `002.01~002.02` (ranges wrap across two lines: `002.01~0` / `02.02`), `129.01 ~ 129.02`.
- Description can wrap onto several lines; make can wrap (`Shridhan` / `Automation`); remarks wrap.
- Parse by header x-positions (reuse `runs`/`group_lines`), start a row at an item-number match, attach continuation lines.
- Store each row in `bom_lines` (+ derived `model_code` = text after `:` in description where present).
- System BOM aggregate properties (stretch): `reservoir_litres` ← `Oil Reservoir - 800 Ltrs`, pump/filter/valve make+model lists.
- Part numbers: normalise for search (case, dashes, spaces; `O/0`, `I/1` confusion).

### motor_datasheet — M6
Two-column key/value sheet (CG Power). `rated_output_kw`, `frame`, `voltage_v`, `rated_current_a`, `rated_speed_rpm`, `poles`,
`frequency_hz`, `duty`, `cooling` (IC411), `protection_ip`, `mounting` (B35), `efficiency_class` (IE3), `insulation_class`, `weight_kg`,
`standards`. Header has Customer/Project (ignore).

### Others — M6 (lower priority)
- `jb_doc`: cover page `Enclosures 600(W) X 760(H) X 350(D)`, `Supply Voltage`, `Control Voltage`; page index.
- `cylinder_ga_book`: page 2 index rows `n | PART NO | DESCRIPTION (bore x rod x stroke) | MATERIAL CODE (ZX…)`, grouped by project.
- `ga_drawing`: only **some** carry a materials/terminations/notes block (SMS `PP02123-b-GA` does; ELECON `PP60057-d` p1 and SMS `HV11452-b` showed
  nothing in that region). **Needs investigation before committing a schema.**
- `elec_load_list`, `io_list`: tables (header: customer/project/rev; rows). Index as text rows.
- `operation_writeup`, `crs`: free text only; index for text search.

---

## 6. Database (PostgreSQL)

One migration file `db/001_init.sql`, applied by the loader if the tables do not exist. Owned by the .NET project later
(EF Core migrations or DbUp) — for the POC plain SQL is fine.

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE documents (
  id                bigserial PRIMARY KEY,
  rel_path          text   NOT NULL UNIQUE,          -- relative to DOCSEARCH_ROOT
  file_name         text   NOT NULL,
  ext               text   NOT NULL,
  sha256            text   NOT NULL,
  size_bytes        bigint NOT NULL,
  source_folder     text,                            -- ELECON | SMS
  kind              text   NOT NULL,                 -- pdf | xlsx | cad
  category          text   NOT NULL,                 -- see §3
  product_class     text,                            -- PP | HA | HQ | HV
  project_code      text,                            -- PP60056, HAS90265 (a document label, NOT a filter)
  doc_prefix        text,                            -- 01 | 02 | 03
  revision          text,                            -- '0','a','b',...
  rev_rank          int,                             -- 0 for '0', 1 for 'a', ...
  application       text,                            -- WT+WC+WG, SAC, E+T ...
  family_key        text   NOT NULL,
  is_latest         boolean NOT NULL DEFAULT true,
  duplicate_of      bigint REFERENCES documents(id),
  page_count        int,
  parse_status      text   NOT NULL DEFAULT 'pending',  -- pending|ok|partial|failed|skipped
  parse_warnings    jsonb  NOT NULL DEFAULT '[]',
  extractor_version text,
  indexed_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX documents_cat_latest ON documents (category, is_latest) WHERE duplicate_of IS NULL;
CREATE INDEX documents_family     ON documents (family_key);
CREATE INDEX documents_sha        ON documents (sha256);

-- registry that drives step 2 of the UI
CREATE TABLE properties (
  category     text NOT NULL,
  prop_key     text NOT NULL,
  label        text NOT NULL,
  data_type    text NOT NULL CHECK (data_type IN ('number','text')),
  sort_order   int  NOT NULL DEFAULT 0,
  PRIMARY KEY (category, prop_key)
);

CREATE TABLE spec_fields (
  id           bigserial PRIMARY KEY,
  document_id  bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  prop_key     text   NOT NULL,
  value_text   text   NOT NULL,        -- as printed, whitespace-normalised
  value_canon  text   NOT NULL,        -- lowercase, typo-aliased, remarks stripped: used for grouping/fuzzy
  unit         text,                   -- as printed: Bar, lpm, V, mm ...
  list_sep     text,                   -- '/' | '+' | NULL
  extra        jsonb,                  -- current: AC/DC, frequency_hz, remark ...
  page         int,
  bbox         jsonb,                  -- [x0,y0,x1,y1] points, top-left origin, displayed orientation
  UNIQUE (document_id, prop_key)
);
CREATE INDEX spec_fields_prop   ON spec_fields (prop_key);
CREATE INDEX spec_fields_canon  ON spec_fields USING gin (value_canon gin_trgm_ops);

CREATE TABLE spec_numbers (            -- one row per number in a numeric field (supports "any value near")
  field_id  bigint NOT NULL REFERENCES spec_fields(id) ON DELETE CASCADE,
  ord       int    NOT NULL,
  num       numeric NOT NULL,
  PRIMARY KEY (field_id, ord)
);
CREATE INDEX spec_numbers_num ON spec_numbers (num);

CREATE TABLE terminations (
  id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  tbl text, name text, size text, connection text, tube_pipe text,
  page int, bbox jsonb
);
CREATE TABLE notes (
  id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  no text, text text, page int
);
CREATE TABLE doc_links (
  from_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  to_id   bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  link_type text NOT NULL,             -- cad_sibling | same_project | reused_on
  PRIMARY KEY (from_id, to_id, link_type)
);
CREATE TABLE bom_lines (               -- M5
  id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  item_no text, customer_item_no text, rev text, part_no text, part_no_canon text,
  description text, model_code text, make text, qty text, remarks text, page int, bbox jsonb
);
CREATE INDEX bom_part_canon ON bom_lines USING gin (part_no_canon gin_trgm_ops);
CREATE INDEX bom_desc       ON bom_lines USING gin (to_tsvector('simple', description));
```

### Canonicalisation (`value_canon`)
lowercase; collapse whitespace; strip trailing remarks in parentheses; apply an alias map for known typos
(`minerial` → `mineral`, `iso vg 68` → `iso vg68`); keep the original in `value_text`. Unknown values are kept, never dropped.
The alias map lives in `ingest/docsearch_ingest/aliases.py` and is covered by tests.

### Near-match rules
- **Numeric property:** `delta = MIN(ABS(num - target))` over the field's numbers (any value in `250/300` may match);
  rank by `delta`, then latest revision first. Return the matched number so the UI can show *which* value matched.
- **Text property:** exact `value_canon` match first, then `similarity(value_canon, :q) ≥ 0.3` (pg_trgm), ranked by similarity.
- Default `limit = 20`. No fixed tolerance, so there is always an answer.

---

## 7. Ingestion CLI (Python)

`python -m docsearch_ingest <command> --root D:\CMF\sample --db $DOCSEARCH_DB`

| Command | Does |
|---|---|
| `scan` | walk root, skip junk, hash, classify (§3 rules), compute revision/family/duplicates/sibling links, upsert `documents` |
| `extract [--category X] [--force]` | run the extractor for each category; incremental by `sha256` + `extractor_version` |
| `load` | write spec fields / numbers / ports / notes / bom rows, refresh `properties`, `is_latest`, `doc_links` |
| `report` | coverage per category/field + list of `partial/failed` documents → `out/report.md` |

Rules: idempotent; one document failing must never abort the run (record `parse_status=failed` + warning);
never write into `DOCSEARCH_ROOT`; log every filename/content mismatch as a warning.

Package layout (extend existing):
```
ingest/docsearch_ingest/
  pdfium_text.py     # DONE
  circuit.py         # DONE
  classify.py        # filename rules, revision, family, product_class
  aliases.py         # canonicalisation + typo map
  bom.py             # M5
  motor.py, jb.py, cylbook.py   # M6
  db.py              # psycopg, migration, upserts
  cli.py             # commands above
ingest/tests/        # pytest, golden JSON per sample file
```

---

## 8. API (.NET 10 standard Web API) — `api/`

Built with `[ApiController]` controller classes (one per resource group: categories, search, documents) and explicit
contract types (request/response DTOs, service interfaces), not minimal-API endpoint lambdas.

JSON, camelCase, CORS open for `http://localhost:4200`, OpenAPI enabled (generate the Angular client with NSwag).
No auth. Raw SQL via Dapper; **no business logic in the controller beyond what is below**.

| Endpoint | Returns |
|---|---|
| `GET /api/categories` | `[{key,label,docCount}]` (latest, non-duplicate documents only) |
| `GET /api/categories/{cat}/properties` | `[{key,label,dataType,docCount}]` from `properties` joined to actual data |
| `GET /api/categories/{cat}/properties/{prop}/values?q=` | `[{display,canon,docCount}]` — distinct values with counts, ordered numerically for number props; `q` filters (trigram) |
| `GET /api/search?category=&property=&value=&mode=near\|exact&limit=20&includeOld=false` | `{results:[{documentId,fileName,relPath,projectCode,revision,isLatest,application,matchedValue,matchedNumber,delta,similarity,page,bbox,siblings:[{id,fileName,kind}]}]}` |
| `GET /api/documents/{id}` | document + all `specs`, `terminations`, `notes`, `siblings`, `revisions` |
| `GET /api/documents/{id}/file` | streams the file from `DOCSEARCH_ROOT` with HTTP Range support, correct content-type |
| `GET /api/text-search?q=&category=` | M7: fuzzy keyword search over spec text, BOM rows (part no., description) |

Rules: `value` for numeric near-search is parsed as a decimal (accept `223`, `223.5`); a non-number → 400. Never expose absolute server paths.

---

## 9. UI (Angular) — `web/`

Standalone components, one page + one dialog:

```
┌ Docsearch ───────────────────────────────────────────────────────────────┐
│ 1 Category [Hydraulic circuit ▾]   2 Property [Design pressure ▾]        │
│ 3 Values found:  ( 230 Bar ·5 ) ( 250/300 Bar ·6 ) ( 300 Bar ·13 ) …     │
│ 4 Search value [ 223        ] [Near ▾]  [Include old revisions ☐]  [Go]  │
├──────────────────────────────────────────────────────────────────────────┤
│ 230 Bar    Δ 7    01-PP02123-d-Hyd.Ckt (As Built)   rev d   [PDF][DWG]   │
│ 250/300    Δ 27   01-PP60056-d-Hyd.Ckt (WT+WC+WG)   rev d   [PDF][DWG]   │
│ …                                                                         │
└──────────────────────────────────────────────────────────────────────────┘
```
- Steps are cascading: changing 1 resets 2–4; step 3 chips fill step 4 when clicked.
- Result row shows matched value, delta, filename, revision, sibling chips (pdf / dwg / sldprt …). Clicking opens the **viewer
  dialog** with the PDF at `page`, **highlighting `bbox`** (overlay = `bbox × zoom`; pdf.js already applies `/Rotate`, and our
  bbox is in displayed orientation, so no extra transform), plus a side panel with every extracted spec, ports table and notes.
- pdf.js worker bundled locally (no CDN). Test early on A0/A1 drawings — they are heavy.

---

## 10. Quality bar and acceptance tests

### Acceptance (demo script — all must pass on the sample)
- **AT-1** Hydraulic circuit → Design pressure → value `223` returns the SMS **230 Bar** drawings first (Δ 7, latest revisions only:
  `HV11452-c`, `HV11495-d`, `PP02123-d`), then **250/300** (Δ 27), then 300.
- **AT-2** Property list for `hyd_circuit` contains all 17 properties; for `bom_cylinder` contains `bore_mm, rod_mm, stroke_mm, make`.
- **AT-3** Cylinder BOMs → Bore `80` → returns the Ø80 x 56 cylinders (HA90471, HAS90264, HAS90269, HAS90545) as nearest; each shows its `reused_on` projects.
- **AT-4** Clicking a result opens the PDF on the right page with the matched cell highlighted.
- **AT-5** Includes-old-revisions toggle shows PP60056 revisions 0–e; off shows only `e`.
- **AT-6** `…- Copy.pdf` never appears in results.
- **AT-7** Re-running `scan/extract/load` with no file changes writes nothing new (idempotent).

### Accuracy
- Build a **hand-verified golden set of ≥20 circuit drawings** (JSON), pick across ELECON/SMS and all three sheet sizes.
  Target ≥ 98 % of fields exact-match. Report per-field accuracy. (Only 3 drawings were eyeballed so far.)
- Per category: ≥ 95 % of documents `parse_status=ok`; every failure visible in `report`.

### Tests
pytest for ingest (golden JSON, filename classifier table, alias map, near-match SQL against a test DB),
xUnit for API endpoints, one Playwright smoke test for the four-step flow.

---

## 11. Milestones (implement in this order)

| # | Deliverable | Definition of done |
|---|---|---|
| M0 ✅ | Scaffold, compose (Postgres + pgAdmin), README | `docker compose up -d` works |
| M1 ✅ | Circuit extractor + coverage report | 24/24 parse; `out/circuits.json` |
| M2 ✅ | `db/001_init.sql`, `classify.py`, `scan`, `load` for circuits, `properties` seed | tables populated; AT-7 for circuits; pgAdmin shows data |
| M3 ✅ | .NET API: categories / properties / values / search / document / file | AT-1, AT-5, AT-6 via curl/Swagger |
| M4 ✅ | Angular four-step UI + results + PDF viewer with highlight | AT-1, AT-4 in the browser |
| M5 ✅ | `bom.py`: cylinder title specs, `reused_on`, BOM rows (all `bom_*`) | AT-2, AT-3 |
| M6 | motor datasheet, JB cover, cylinder GA book, GA drawing investigation | properties appear in the UI |
| M7 | canonicalisation polish, fuzzy text search endpoint + UI box | typo'd query finds the right doc |
| M8 | golden set + accuracy report, README for the demo | accuracy numbers in `out/report.md` |

Do M2→M4 first: a thin end-to-end vertical slice on circuits is the demo. Then widen with M5.

---

## 12. Working agreements

- Small, reviewable commits. Do not reformat existing files. Keep the §4 lessons as comments where they apply.
- Never modify or delete anything under `D:\CMF\sample`. Treat it as read-only.
- Do not install into `D:\Ai\gpu-env`.
- Prefer rules over models. If a rule cannot parse a document, record a warning and move on; do not guess values.
- When a design question is open (§13), pick the simplest option, note the assumption in the PR/commit, and continue.

## 13. Open questions (do not block on these)
1. Which Postgres major version will the Azure target use? (Compose uses `postgres:latest`; PG18+ images want the data volume at `/var/lib/postgresql`.)
2. Is the sample representative of the full file set (other customers / vendors / templates)? Add a `report` check that flags layouts that do not match.
3. Which categories matter most to the engineers? Assumed: circuits, cylinders, system BOMs.
4. GA drawing spec block: where is it, and is it worth parsing?
5. Normalising the port table across the ELECON and SMS templates for filtering.
6. Later: stacked filters (several properties AND-ed), pgvector for semantic search, Qwen3-VL fallback for unparseable spec boxes, Windows/AD auth, Azure deployment.
