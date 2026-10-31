# Docsearch POC

Search hydraulics BOMs / drawings by category -> spec property -> value -> nearest match.

## Frozen stack (POC)
- Postgres (`docker pull postgres`), extensions: pg_trgm + full-text. pgvector deferred.
- Python ingestion (own venv; rule-based extraction, no GPU)
- .NET 10 standard Web API with controllers and contracts (Npgsql + Dapper), no auth
- Angular + pdf.js viewer
- Optional later: Qwen3-VL-8B (D:\Ai\Models\qwen3-vl-8b-instruct) as fallback for unparseable spec boxes.
  Cloud dev VM has 16 GB, so it needs quantization (or the 4B variant).

## Layout
- ingest/  Python extractors
- api/     .NET API
- web/     Angular UI
- docs/    schema spec
- ingest/tools/  helpers (golden-set crops)
- out/     extraction output: circuits.json, circuits_report.txt (see docs/schema.md)

## Demo (start here)

**Start everything** (Windows, Docker Desktop running, sample files in `D:\CMF\sample`):

    docker compose up -d                                   # Postgres + pgAdmin (http://localhost:5050)
    cd ingest ; $env:DOCSEARCH_ROOT = "D:\CMF\sample"
    ..\.venv\Scripts\python -m docsearch_ingest scan ; ..\.venv\Scripts\python -m docsearch_ingest extract
    ..\.venv\Scripts\python -m docsearch_ingest load ; ..\.venv\Scripts\python -m docsearch_ingest report
    cd ..pi\Docsearch.Api ; dotnet run                 # http://localhost:5013/swagger
    cd ..\..\web ; npm start                              # http://localhost:4200

**Click-through** (each step is also an automated test; `npx playwright test` in `web/` runs them):

| # | Do this | You see | Test |
|---|---|---|---|
| 1 | *Filter by property* -> Hydraulic circuit -> Design pressure; chips show `230 Bar · 3`, `250/300 Bar · 1`, `300 Bar · 2`; type `223`, Go | the three SMS 230 Bar drawings first (Δ 7), then 250/300 (Δ 27), then 300; a `DWG` chip where an editable source exists | AT-1 |
| 2 | Click a result | the PDF opens on the right page with the matched cell highlighted; side panel lists every extracted spec, ports and notes | AT-4 |
| 3 | Tick *Include old revisions* | PP60056 shows revisions 0-e; unticked, only `e`. The `- Copy.pdf` never appears | AT-5, AT-6 |
| 4 | Cylinder BOM -> Bore (mm) -> `80` | the four Ø80 x 56 cylinders first, each with the projects it was reused on (`PP60050, PP60053, PP60056`) | AT-3 |
| 5 | Motor datasheet -> Rated output -> `100`; JB document -> Enclosure -> `350` | 110 kW motors (Δ 10); JB covers with a 350 mm depth. Highlight sits on the printed cell | M6 |
| 6 | *Free-text search*: `presure relef valve`, `TPN0O041`, `4we6` (category CAD) | typos still find the BOM rows; the letter-O part number finds `TPN00041`; SolidWorks parts are offered as downloads | M7 |
| 7 | Re-run `scan`, `extract`, `load` | each prints 0 changed (idempotent) | AT-7 |

## Quality, honestly

* **Accuracy** (`out/report.md`, section "Accuracy against the golden set"): on 23 hand-read circuit drawings, 365/365 spec
  fields, 177/177 port rows and 84/84 notes are exact, with nothing invented. Method, the 17 mistakes the *reader* made, and the
  limits are in [ingest/tests/golden/README.md](ingest/tests/golden/README.md). In short: the golden values were read by Claude, not
  signed off by an engineer; the notes logic was tuned on this same set; and the 23 drawings are only six distinct layouts, so it
  does not prove the extractor copes with templates outside the sample.
* **Parse success**: every extracted category is at 100 % `ok` (target 95 %). `ok` means "no warnings", not "correct": only the
  circuits are scored against ground truth.
* **Not parsed in the POC**: GA drawings (link-only; 1 of 12 has the spec block, 2 are scanned images), CRS spreadsheets, load /
  IO lists, operation write-ups. They appear as `skipped` with a reason, and are not searchable by their contents.
* **Known glyph issue**: pdfium cannot map the Ø in BOM descriptions (it reads as `�`); it is left as extracted, not guessed.

## Python venv (Windows)
    py -3.12 -m venv D:\CMF\Docsearch\.venv
    D:\CMF\Docsearch\.venv\Scripts\pip install -r requirements.txt

## Ingest into Postgres (M2)
    docker compose up -d
    cd ingest
    $env:DOCSEARCH_ROOT = "D:\CMF\sample"
    ..\.venv\Scripts\python -m docsearch_ingest scan      # classify, hash, duplicates, revisions, CAD siblings
    ..\.venv\Scripts\python -m docsearch_ingest extract   # run extractors -> out/extract/<sha256>.json (cache)
    ..\.venv\Scripts\python -m docsearch_ingest load      # spec fields / numbers / ports / notes / properties
    ..\.venv\Scripts\python -m docsearch_ingest report    # out/report.md
All commands are idempotent (a second run changes nothing). Tests: `pip install -r requirements-dev.txt; cd ingest; python -m pytest`.

## API (M3)
    cd api\Docsearch.Api
    dotnet run                      # http://localhost:5013 , Swagger UI at /swagger , OpenAPI at /swagger/v1/swagger.json
    cd ..; dotnet test Docsearch.sln   # unit tests + acceptance tests (need the DB ingested, see above)
`DOCSEARCH_ROOT` / `DOCSEARCH_DB` are read from environment variables, falling back to `appsettings.json`.
Endpoints: `GET /api/categories`, `/api/categories/{cat}/properties`, `/api/categories/{cat}/properties/{prop}/values?q=`,
`/api/search?category=&property=&value=&mode=near|exact&limit=&includeOld=`, `/api/documents/{id}`, `/api/documents/{id}/file`,
`/api/text-search?q=&category=&limit=&includeOld=` (fuzzy: part numbers with O/0 and I/1 folded, BOM descriptions, spec values,
circuit notes, file names; typos tolerated; one result per document with the page/bbox of its best match).
Text search scans the tables with trigram `word_similarity` (no index): fine for the POC's thousands of rows; add GIN trigram
indexes on `lower(description)`, `lower(file_name)` and use the `<%` operator when the corpus grows.

## UI (M4)
    cd web
    npm install
    npm start                       # http://localhost:4200 (needs the API on :5013)
    npm run api-client              # regenerate src/app/api/api-client.ts with NSwag (API must be running;
                                    #   set DOTNET_ROLL_FORWARD=Major if only the .NET 10 runtime is installed)
    npx ng test --watch=false       # unit tests
    npx playwright test             # four-step smoke test; starts the API and `npm start` itself if they are not running
The pdf.js worker and viewer files are served from the app's own `/assets` (copied from `ngx-extended-pdf-viewer`), so there are
no CDN calls. The API base URL is in `web/src/environments/environment.ts`.

## Run the circuit extractor (standalone)
    cd ingest
    python run_circuits.py <path-to-sample> ..\out
