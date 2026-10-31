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

## Run the circuit extractor (standalone)
    cd ingest
    python run_circuits.py <path-to-sample> ..\out
