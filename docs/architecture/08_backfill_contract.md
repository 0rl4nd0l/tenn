# Backfill contract

This document defines the contract for backfill endpoints and pipeline parameters: default values, idempotency, and response shape.

---

## Entrypoints and defaults

| Entrypoint | Default `years` | Default `process_documents` | Notes |
|------------|-----------------|-----------------------------|--------|
| **API** `POST /api/backfill/ticker/{ticker}` | 1 | False | Caller must pass `years` and/or `process_documents` explicitly for long-range or full processing. |
| **API** `POST /api/backfill/asx20` | 1 | False | Same as single-ticker. |
| **Worker** `backfill_ticker` task | From API kwargs | From API kwargs | Worker receives same args the API was called with. |
| **Pipeline** `run_pipeline_sync(spec)` | — | — | Spec is explicit; no defaults in service. |
| **Pipeline** `backfill_ticker_sync(...)` (legacy / scripts) | 5 | True | Used by standalone scripts; not used by API. |
| **Script** `full_history_ticker_sync.py --asx20` / `make backfill-asx20` | 5 (configurable) | False by default | Preset of 20 tickers. Run from host with stack up; set `DATABASE_URL` and `DOCS_ROOT` / `IMPORTANCE_OUTPUT_ROOT` to writable paths. For more tickers use `--ticker-universe-file` (+ optional `--max-tickers`) or `--ticker`. See `financial-engine_v2/README.md`. |

**Contract:** API defaults are intentionally conservative (1 year, no process_documents) so that a bare POST does not trigger heavy work. Scripts and callers that want multi-year discovery and/or full document processing must pass `years` and `process_documents` explicitly. The worker and `run_pipeline_sync` use whatever values are in the request or spec.

### Parameters

- **`years`** (int, default: API 1, worker 5): Lookback window in years from **now** (request time or pipeline run time). Discovery considers documents published between `now - years` and `now`. Changing `years` only changes which documents are discovered (and thus downloaded/processed); it does not alter or delete existing document rows, logical vector IDs, or their deterministic physical Qdrant point-ID mapping. Existing document rows are deduplicated by `source_url`; re-running with the same or different `years` does not create duplicate document rows.
- **`process_documents`** (bool): When true, after downloading each new PDF the pipeline runs extraction, chunking, embedding, and Qdrant upsert (and optional financial/risk DB writes). When false, only discovery and download run; existing documents are not reprocessed.
- **Single-document `process_document` behavior:** The dedicated single-document path is still intended for re-processing downloaded documents, but it now self-heals one narrow state: if the local PDF is missing and the row still shows `pdf_sha256` empty, the backend first runs `download_pdf_for_document()` and then continues extraction. Rows with a non-empty marker and a missing file still fail loudly.
- **Concurrency:** Script `full_history_ticker_sync.py` accepts `--concurrency N` (default 1). API/worker sync backfill use `BACKFILL_CONCURRENCY` (default 1). When N > 1, up to N documents are downloaded and processed in parallel per ticker; HTTP and Qdrant clients are reused for the run. See [09_worker_and_celery_contract.md](09_worker_and_celery_contract.md) for env details.
- **Two ingestion modes (script only):**
  - **Bulk (long-term):** `--years 5` (default) with `--skip-complete` and `--min-docs-to-skip N` (default 50). Tickers that already have ≥ N documents in the DB are skipped so restarts do not re-iterate over completed companies.
  - **Recent (updater):** `--months M` (e.g. 3) for a short lookback over many tickers; typically no `--skip-complete`.
- **Quarantine on interrupt:** If the script is stopped (SIGINT/SIGTERM), it still writes the report and runs quarantine (adds no-announcement tickers to `config/ticker_quarantine.json`) before exiting.
- **Cockpit:** The cockpit TUI exposes these as actions: `bulk_backfill` (Bulk 5y backfill, universe + skip-complete) and `recent_backfill` (Recent updater, universe + months). Chat in operational mode includes ingestion system knowledge so it can explain bulk vs recent and how to run actions. See `financial-engine_v2/README.md` (Cockpit and ingestion).

---

## Idempotency

- Re-running backfill for the same ticker and `years` does not create duplicate document rows (deduplication by `source_url`).
- Re-running `process_document` for the same document overwrites the same Qdrant points (deterministic logical IDs `document_id:chunk_index`, with deterministic physical point-ID mapping) and updates the same financial/risk rows.
- See [04_ingestion_pipeline.md](04_ingestion_pipeline.md) for details.

---

## Response shape (sync and worker)

When the API runs in sync mode or the worker returns the result of `run_pipeline_sync`, the response includes:

- `ticker`, `found`, `inserted`, `processed`, `processed_ok_count`, `extraction_failed_count`, `skipped_download`, `process_documents`
- `importance_classification`, `provider_metrics`, `provider_failures_sample`
- `errors`, `error_count`

Single-ticker sync: `{"mode": "sync", **result}`. ASX20 sync: `{"mode": "sync", "processed": N, "results": [result, ...]}`.

---

## Gotchas

- **Changing `years`** affects which documents are in scope for discovery and processing only; it does not alter or delete existing document rows, logical vector IDs, or physical point-ID mappings. To re-process already-ingested documents you need a separate mechanism (e.g. re-run with same `years` and `process_documents=true`; only already-present docs are skipped for download but can be explicitly reprocessed via a different path).
- **Running with `process_documents=false`** then later with `true` does not auto-process documents that were only downloaded earlier. The second run only processes documents discovered in that run (new since the first run). To get full processing for a given lookback window, run once with `process_documents=true` for that window.
- **Calling `POST /api/process/document/{document_id}` on a pending-download row** may now trigger the canonical PDF download first if `pdf_sha256` is still empty. That is a single-document recovery convenience, not a change to backfill semantics.
