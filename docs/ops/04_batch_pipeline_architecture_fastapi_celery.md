# 04 - Batch-First Pipeline Architecture (FastAPI + Celery + Postgres + Qdrant)

## High-Level Architecture Diagram (Description)

Components:
1. FastAPI API layer
2. Celery workers (CPU and GPU-specialized queues)
3. Redis broker/result backend
4. Postgres system-of-record
5. Qdrant vector store
6. Local disk artifact store (PDFs, extracted text, job artifacts)
7. Host Ollama service (Phase 1)

Data flow:
1. Ingest request enters FastAPI.
2. FastAPI creates `job_run` row and enqueues task by workload type.
3. Ingest worker discovers ASX announcements and stores document metadata.
4. PDF capture stores raw file and content hash.
5. Extraction/chunking creates normalized text artifacts.
6. Embedding worker computes vectors and upserts Qdrant with payload metadata.
7. Scoring workers compute event flags/ranking.
8. GPU queue generates research packs/summaries via Ollama.
9. Postgres stores all provenance and output links.

## Celery Queue Plan

Queues:
- `ingest`: network-bound discovery and metadata writes
- `embed`: text chunk embedding + vector upserts
- `score`: deterministic scoring/event flag jobs
- `llm_gpu`: all GPU-bound generation tasks
- `llm_cpu`: fallback generation and low-priority text transforms

Concurrency guidance:
- `llm_gpu`: strict concurrency `1`
- `embed`: small bounded concurrency (avoid saturating weak CPU)
- `ingest`: moderate concurrency with upstream rate limits
- `score`: moderate/high as CPU budget allows outside interactive windows
- `llm_cpu`: low concurrency and noninteractive priority

Isolation guidance:
- Separate worker pools per queue class.
- Keep `llm_gpu` workers isolated from CPU-heavy queues.
- During interactive hours, deprioritize heavy CPU queues.

## Postgres Provenance Schema Sketch

Core tables (additive sketch):

### `job_runs`
- `job_run_id` (PK)
- `job_type`
- `queue_name`
- `status`
- `requested_at`, `started_at`, `finished_at`
- `trigger_source` (api/schedule/manual)
- `request_payload_json`
- `error_code`, `error_detail`

### `documents`
- `document_id` (PK)
- `ticker`
- `source_url`
- `source_provider`
- `published_at`
- `title`
- `doc_hash_sha256`
- `storage_path`
- `ingested_at`

### `document_artifacts`
- `artifact_id` (PK)
- `document_id` (FK)
- `artifact_type` (raw_pdf/extracted_text/chunks)
- `artifact_path`
- `artifact_hash`
- `created_at`

### `extraction_runs`
- `run_id` (PK)
- `document_id` (FK)
- `job_run_id` (FK)
- `model_name`
- `model_version`
- `prompt_template_version`
- `extractor_version`
- `status`
- `structured_json`
- `created_at`

### `research_outputs`
- `output_id` (PK)
- `job_run_id` (FK)
- `ticker`
- `output_type` (pack/summary/alert_draft)
- `model_name`
- `model_version`
- `prompt_template_version`
- `input_doc_ids_json`
- `output_path`
- `created_at`

### `event_scores`
- `score_id` (PK)
- `job_run_id` (FK)
- `ticker`
- `event_type`
- `score_value`
- `score_features_json`
- `created_at`

## Qdrant Collection Layout

Collection:
- Primary: `asx_docs_v1` (versioned naming)

Point ID strategy:
- Deterministic composite: `hash(document_id + chunk_index + chunk_hash)`

Payload fields:
- `document_id`
- `ticker`
- `published_at`
- `source_url`
- `doc_hash_sha256`
- `chunk_index`
- `chunk_char_start`, `chunk_char_end`
- `chunk_hash`
- `embed_model`
- `embed_model_version`
- `job_run_id`
- `created_at`

Chunk strategy:
- Fixed-size + overlap baseline
- Keep chunk boundaries deterministic for reproducible re-embedding
- Re-upsert only when chunk hash changes

## Nightly Batch Schedule (Example)

Window assumptions:
- Interactive window: business hours
- Batch window: overnight

Suggested schedule:
1. Early night: ingest + PDF capture + dedupe
2. Mid night: extraction + chunking + embeddings
3. Late night: scoring + LLM deep synthesis (research packs)
4. End window: acceptance checks + summary report

Policy:
- Do not run CPU-heavy scoring at peak interactive times.
- Keep GPU queue dedicated to batch synthesis overnight.

## Failure Handling, Retries, and Idempotency

Idempotency keys:
- Document-level dedupe by `doc_hash_sha256`
- Chunk-level dedupe by `chunk_hash`
- Output-level dedupe by `(ticker, run_date, output_type, input_hash)`

Retry policy:
- Retry transient network/provider failures with bounded backoff.
- Do not retry deterministic validation failures endlessly.
- Route repeated failures to dead-letter queue with diagnostic context.

Deterministic rerun behavior:
- If inputs and model/prompt versions are unchanged, rerun should reproduce equivalent artifacts.
- Any version change must create new provenance rows, not overwrite lineage.
