# Worker and Celery contract

This document describes the worker’s role, task entrypoints, queue/routing, required environment, and how to verify the worker is running the correct code.

## Worker’s role

The **worker executes pipeline jobs; it does not implement pipeline logic.**

- All discovery, download, extraction, embedding, and importance logic lives in the **backend** (`app.services.pipeline`, `app.services.pipeline_service`, and related modules).
- The current routed Celery surface in this repo is the backend app: `financial-engine_v2/backend/app/celery_app.py` plus `financial-engine_v2/backend/app/worker_tasks.py`.
- Those backend task wrappers are thin Celery entrypoints that receive arguments, then **delegate synchronously** to backend pipeline or LLM services.
- `financial-engine_v2/scripts/run_worker.sh` launches `celery -A app.celery_app.celery worker --loglevel=INFO` against that backend app.
- A separate worker package also exists under `financial-engine_v2/worker/app/`, but it is a legacy surface and is not the source of truth for the routed LLM task set documented here.

## Task entrypoints and delegation

Tasks are registered under fixed names so the API can send work with `send_task(name, ...)` without importing the worker package. Each task is a thin wrapper:

| Task name           | Location                    | Delegates to |
|---------------------|-----------------------------|--------------|
| `backfill_ticker`   | `app.worker_tasks`          | `run_pipeline_sync(PipelineJobSpec(...))` in `app.services.pipeline_service` |
| `download_pdf`      | `app.worker_tasks`          | `download_pdf_for_document(db, document_id)` in `app.services.pipeline` |
| `process_document`  | `app.worker_tasks`          | `process_document_sync(document_id)` in `app.services.pipeline` |
| `llm_generate_json` | `app.worker_tasks`          | `app.services.llm.generate_json(prompt, metadata)` |
| `llm_embed_texts`   | `app.worker_tasks`          | `app.services.llm.embed_texts(texts, metadata)` |

- **`backfill_ticker`**: Builds a `PipelineJobSpec` (ticker, years, process_documents, mode=`"celery"`) and calls `run_pipeline_sync(spec)`. Discovery, download, and optional per-document processing all happen inside the backend.
- **`download_pdf`**: Opens a DB session, calls `download_pdf_for_document`, closes the session. No pipeline logic in the worker.
- **`process_document`**: Accepts either `document_id` or a chain payload `prev` with `document_id`; calls `process_document_sync(document_id)` in the backend.
- **`llm_generate_json`**: Calls the routed backend LLM facade. Queue selection is computed from `route_request(prompt, metadata)`, which now collects Redis queue depth, GPU pressure, in-memory task counts, and rolling model metrics before selecting `llm_cpu` or `llm_gpu`.
- **`llm_embed_texts`**: Calls the routed embedding facade. Queue selection is fixed to `embed`.

This contract describes the backend Celery app that is smoke-tested in-repo and used by the local worker launcher. If you run the separate `financial-engine_v2/worker/` container image, audit it separately before assuming routed-task parity.

## Queue and routing expectations

- **Queues**: The backend declares `ingest`, `embed`, `score`, `llm_gpu`, and `llm_cpu`.
- **Routing**:
  - `backfill_ticker` -> `ingest`
  - `download_pdf` -> `ingest`
  - `process_document` -> `llm_gpu`
  - `llm_embed_texts` -> `embed`
  - `llm_generate_json` -> `llm_cpu` or `llm_gpu` from `app.services.router.route_request(...)`
- **Adaptive note**:
  - Queue names are unchanged.
  - `llm_generate_json` may now fall back to `llm_cpu` for short/light coding or reasoning prompts when `llm_gpu` is overloaded or backlogged.
  - Long-context requests remain on `llm_gpu` and are marked deferred for serialized handling.
- **Worker launch profiles**:
  - Current local launcher: `celery -A app.celery_app.celery worker --loglevel=INFO`
  - Optional CPU-only pool: `celery -A app.celery_app.celery worker --loglevel=INFO -Q ingest,embed,score,llm_cpu`
  - Optional GPU-only pool: `celery -A app.celery_app.celery worker --loglevel=INFO --concurrency=1 -Q llm_gpu`
- **Broker/backend**: Redis. Broker URL and result backend are set via `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` (worker’s Celery app reads these from the environment; see below).

## Expected environment variables

The worker process must see the same logical configuration as the backend, because it runs backend code that uses `app.core.config.settings`. Set these (e.g. in `.env` or Docker `environment`):

| Variable                 | Purpose |
|--------------------------|--------|
| `DATABASE_URL`           | PostgreSQL (or SQLite) URL for `SessionLocal` and all DB access in pipeline and pipeline_service. |
| `QDRANT_URL`             | Qdrant base URL for embeddings/vector writes (e.g. `http://qdrant:6333` in Docker). |
| `LLAMACPP_URL`           | Primary llama.cpp/OpenAI-compatible base URL for coding-model requests; used by default for embeddings and JSON generation. |
| `OLLAMA_URL`             | Optional legacy Ollama API base kept for backward-compatible extraction or embedding paths; only necessary if `LLAMACPP_URL` is unavailable or you intentionally target Ollama. |
| `DOCS_ROOT`              | Maps to `settings.docs_root`. Root directory for storing and resolving PDFs; must match backend so paths are consistent. In Docker, `/data/asx/docs`. When running the **standalone script** (e.g. `full_history_ticker_sync.py`) on the host, set to a writable path (e.g. `$(pwd)/data/asx/docs`) and `DATABASE_URL` to `postgresql+psycopg://fe:fe@localhost:5432/fe` so the script can connect and write PDFs. The `make backfill-asx20` target in `financial-engine_v2` sets these for you. |
| `BACKFILL_CONCURRENCY`   | Max parallel documents per ticker when running sync backfill (script `--concurrency` or API/worker). Default 1 (sequential). 2–4 recommended for faster ingestion; HTTP and Qdrant clients are reused per run when concurrency is used. |
| `CELERY_BROKER_URL`      | Redis URL for Celery broker (e.g. `redis://redis:6379/0`). The adaptive router also uses this broker URL for `LLEN` queue-depth probes when Redis is reachable. |
| `CELERY_RESULT_BACKEND`  | Redis URL for Celery results (e.g. `redis://redis:6379/1`). |
| `BACKEND_APP_ROOT`       | Optional; path to backend app root so worker can add it to `sys.path` and import `app.*` (Docker sets this to `/app_backend`). |

Config uses the attribute `docs_root`; Pydantic Settings maps the env var `DOCS_ROOT` to it by default. Other backend settings (e.g. `QDRANT_COLLECTION`, `EMBED_MODEL`, `EXTRACT_MODEL`, feature flags) are also read from the environment when the worker imports `app`; ensure `.env` or the worker’s environment matches what the backend would use for the same run.

## Verifying the worker is running correct code

1. **Container and process**
   - `docker ps` (or equivalent) and confirm the worker container (e.g. `fe_worker`) is up.
   - Inspect the command profile:
     - local/backend launcher uses `app.celery_app.celery`
     - split-pool deployments should consume `ingest,embed,score,llm_cpu` on CPU and `llm_gpu` with concurrency `1` on GPU

2. **Logs**
   - `docker logs fe_worker` (or your container name). Look for Celery startup (broker connection, registered tasks) and for task receipts/completions when you trigger a backfill or document job from the API.

3. **Task registration**
   - The repo includes a smoke test that the expected tasks and specialized queues are registered on the Celery app: `financial-engine_v2/scripts/test_celery_task_registration_smoke.py`.
   - The current smoke path imports `app.celery_app`, `app.worker_tasks`, and `app.tasks.commentary_tasks`, then asserts the routed task names exist in `celery.tasks`.
   - If you are validating the separate `financial-engine_v2/worker/` image, inspect its own `app.tasks` module independently; do not assume it matches the backend task surface.

4. **Parity**
   - `financial-engine_v2/scripts/test_worker_wrapper_parity.py` checks that the backend’s `backfill_ticker` task implementation delegates to `run_pipeline_sync` with the expected `PipelineJobSpec` (ticker, years, process_documents, mode=`celery`). This guards that the worker’s behavior stays a thin wrapper over the shared pipeline.

5. **End-to-end**
   - Trigger a backfill via the API (e.g. `POST` or GET to the backfill endpoint with `task_mode=celery`). Confirm the worker container logs show the task received and completed, and that DB/Qdrant/docs_root state match expectations (e.g. new documents, PDFs under `DOCS_ROOT`).
