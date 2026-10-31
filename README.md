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
- out/     extraction output: circuits.json, circuits_report.txt (see docs/schema.md)

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
