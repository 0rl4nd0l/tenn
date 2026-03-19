# 04 — Ingestion Pipeline

This document describes the document ingestion pipeline: from discovery of ASX announcements through persistence, PDF download, text extraction, chunking, embedding, and vector upsert. It also covers idempotency, deterministic Qdrant point IDs, where ingestion runs (sync vs async), and common failure modes.

---

## Pipeline stages

The pipeline proceeds in a fixed sequence. Each stage consumes the output of the previous one.

| Stage | Description | Location |
|-------|-------------|----------|
| **Discover** | Fetch announcement metadata (ticker, date range) from ASX (and optionally MarketIndex fallback). Produces a list of discovered documents (source URL, title, published_at, etc.). | `pipeline.discover_and_insert_documents` → ASXProvider / MarketIndexProvider |
| **Persist** | Normalize source URLs, deduplicate by `source_url`, insert new rows into `documents`. Only newly inserted document IDs are returned for downstream stages. | `pipeline.insert_discovered_documents` |
| **Download PDF** | For each new document, fetch the PDF from `source_url`, validate PDF signature, optionally resolve via HTML if the URL returns HTML. Write file to disk and set `doc.pdf_path`, `doc.pdf_sha256`. | `pipeline.download_pdf_for_document` |
| **Extract text** | Read the PDF from disk and extract raw text. | `pipeline.process_document` → `extract_text_from_pdf` |
| **Chunk** | Split extracted text into fixed-size chunks (e.g. `max_chars=4500`) for embedding. | `pipeline.process_document` → `simple_chunk` |
| **Embed** | Compute embeddings for each chunk via Ollama (`nomic-embed-text`). Batched; optional in-memory cache by text SHA256. | `pipeline.process_document` → `_embed_chunks` → `ollama_embed` |
| **Upsert** | Write vectors to Qdrant with deterministic point IDs and payload (document_id, ticker, chunk_index, etc.). Optionally run LLM extraction and upsert financial/risk rows. | `pipeline.process_document` → `upsert_points`; `_upsert_financial_rows` |

Discovery and persist are done once per backfill run; download → extract → chunk → embed → upsert are done per document (for each `new_document_id` returned from persist). The per-document loop is implemented in `pipeline._download_and_process_document_ids`: when `max_workers` is 1 (default), documents are processed sequentially; when `max_workers` > 1 (e.g. `BACKFILL_CONCURRENCY` or script `--concurrency`), multiple documents are processed in parallel with shared HTTP and Qdrant clients for the run.

---

## Idempotency guarantees

- **Discover + Persist**
  - **Source URL uniqueness:** `documents.source_url` has a unique constraint. Before insert, the pipeline normalizes URLs and checks existing `source_url`s; it only inserts documents whose `source_url` is not already present.
  - **In-batch dedupe:** Within a single discovery batch, duplicate `source_url`s are skipped so each URL is inserted at most once.
  - **Race safety:** If a concurrent process inserts the same `source_url` first, the batch commit can raise `IntegrityError`. The pipeline catches it, rolls back, and retries inserts one-by-one; URLs that already exist are skipped, so re-running the same backfill does not create duplicate document rows.

- **Download**
  - There is no “skip if file already exists” in the current implementation. Download is only invoked for **new** document IDs (those just inserted in the same run). Re-running a backfill does not re-download for documents that were already in the DB (they are not in `new_document_ids`). If `download_pdf_for_document` or `process_document` is called again for the same document (e.g. via a single-document task), the PDF is overwritten and processing repeats.

- **Extract → Chunk → Embed → Upsert**
  - **Qdrant:** Point IDs are deterministic (see below). Re-running embedding and upsert for the same document overwrites the same points, so the vector store state is idempotent with respect to that document.
  - **Financial/risk rows:** Upserts are keyed by `(ticker, period_end, period_type)` and `document_id`; re-running updates the same rows.

---

## Deterministic Qdrant point IDs

- **Format:** `document_id:chunk_index`
  - `document_id` is the canonical lowercase UUID string of the document (same as in the `documents` table).
  - `chunk_index` is the zero-based index of the chunk within that document.

- **Why deterministic:** Same document + same chunking always yields the same point ID. Re-embedding and re-upserting replace the same points instead of creating duplicates. This is required by [vector store invariants](../../.cursor/rules/vector_store_invariants.md) and [backend architecture](../../.cursor/rules/backend_architecture.md).

- **Implementation:** In `pipeline.process_document`, for each chunk: `point_id = f"{doc_id_str}:{index}"` with `doc_id_str = str(doc.document_id).lower()`.

---

## Where ingestion runs

### Sync path (backend pipeline)

- **Trigger:** API `POST /api/backfill/ticker/{ticker}` or `POST /api/backfill/asx20` when `task_mode` is `"sync"`.
- **Execution:** The FastAPI app calls the pipeline **in-process** via `pipeline_service.run_pipeline_sync(PipelineJobSpec(...))`. That uses `pipeline.discover_and_insert_documents`, then `pipeline._download_and_process_document_ids` (download + optional process for each new document, with concurrency from `settings.backfill_concurrency`). Scripts use `pipeline.backfill_ticker_sync`, which also calls `_download_and_process_document_ids` (concurrency from `--concurrency` or `settings.backfill_concurrency`).
- **Blocking:** The HTTP request runs the full pipeline and returns when done (or when an unhandled error is raised).

### Async path (worker delegates to shared pipeline)

- **Trigger:** Same API endpoints when `task_mode` is not `"sync"` (e.g. Celery). The API enqueues a task (e.g. `backfill_ticker`) and returns immediately.
- **Execution:** A **Celery worker** runs the task. The worker **does not implement its own ingestion logic**. It delegates to the same backend pipeline:
  - `backfill_ticker` builds a `PipelineJobSpec` and calls `run_pipeline_sync(spec)` from `app.services.pipeline_service`.
  - `run_pipeline_sync` uses `app.services.pipeline` (discover_and_insert_documents, download_pdf_for_document, process_document).
  - Granular tasks such as `download_pdf` and `process_document` call `download_pdf_for_document` and `process_document` from `app.services.pipeline` directly.

So: **all ingestion logic lives in the backend** (`pipeline.py`, `pipeline_service.py`). The worker only invokes that logic (and uses the same DB, config, and docs root so that file paths and document state are consistent).

### Script modes and cockpit

- **Bulk (long-term):** Script `full_history_ticker_sync.py` with `--ticker-universe-file`, `--years 5`, `--skip-complete`, and `--min-docs-to-skip`. Tickers that already have enough documents in the DB are skipped so restarts do not re-iterate over completed companies. Cockpit action: `bulk_backfill`.
- **Recent (updater):** Same script with `--ticker-universe-file` and `--months M` (e.g. 3); no skip-complete. Cockpit action: `recent_backfill`.
- **Single ticker:** `full_history` (one ticker, N years). See [08_backfill_contract.md](08_backfill_contract.md) for parameters and quarantine on interrupt.

---

## Common failure modes

| Failure | Cause | Behavior |
|--------|--------|----------|
| **Document not found** | Invalid or unknown `document_id` passed to download/process. | **Fail fast:** `ValueError` raised; not retried. Caller should not retry with the same ID. |
| **Invalid document_id format** | `document_id` not a valid UUID when building Qdrant point IDs. | **Fail fast:** `RuntimeError` raised in `process_document`. |
| **MarketIndex headless blocked** | Download attempted for a MarketIndex URL without a headed browser. | **Skip and continue:** `RuntimeError("marketindex_headed_required")` caught; document is marked (e.g. `pdf_sha256 = "blocked_marketindex_headed_required"`), counted as skipped_download, and the pipeline continues with the next document. |
| **MarketIndex 403** | HTTP 403 when fetching a MarketIndex URL. | **Skip and continue:** Document marked (e.g. `pdf_sha256 = "blocked_marketindex_403"`), skipped_download incremented, pipeline continues. |
| **Download not a PDF** | Response does not start with `%PDF` and no PDF link could be resolved from HTML. | **Fail for that document:** `ValueError` raised; error recorded in the run result; pipeline continues with next document (sync/orchestrator catches and appends to `errors`). |
| **Network / HTTP errors** | Timeouts, connection errors, 5xx, etc. on download or provider calls. | **Fail for that document:** Exception (e.g. `httpx.HTTPStatusError`) caught; DB rollback for that document; error appended to result; pipeline continues. |
| **Text extraction failure** | PDF corrupted or unreadable; extractor returns empty or fails. | **Fail for that document:** Can raise or surface as extraction failure; `process_document` may still write an `ExtractionRun` with status `"failed"`. Extraction failure taxonomy (e.g. `ocr_or_text_unavailable`, `parser_timeout`, `corrupted_pdf`) is used for classification; pipeline continues with next document. |
| **Ollama / LLM extraction failure** | Ollama unreachable or returns invalid JSON. | **Non-fatal for process_document:** Extraction status set to `"failed"` and stored in `ExtractionRun`; financial/risk upsert is skipped for that doc. Embedding and Qdrant upsert may already have succeeded. Pipeline continues. |
| **Qdrant dimension / distance mismatch** | Collection exists with wrong vector size or distance (e.g. not COSINE). | **Fail fast:** `ensure_collection` / validation raises `RuntimeError`. No automatic repair; collection must be recreated or fixed externally. |
| **Qdrant unavailable** | Connection or server error when upserting. | **Fail for that document:** Exception propagates; that document’s processing fails and error is recorded; pipeline continues with next document if in a loop. |

Summary:

- **Fail fast (no retry):** Invalid inputs (missing document, bad document_id), Qdrant schema mismatch. Correct by fixing input or collection.
- **Skip and continue (no retry):** Known blocked conditions (MarketIndex headless, MarketIndex 403). Document is marked so it is not retried blindly.
- **Fail for document, continue pipeline:** Download/network errors, not-a-PDF, extraction/LLM failures. Error is recorded; remaining documents in the batch are still processed. Retry is at the discretion of the caller (e.g. re-run backfill or re-invoke single-document task).
