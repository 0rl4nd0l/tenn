# Backend API Surface

Current backend API surface for `financial-engine_v2/backend`.

This document describes the live HTTP routes mounted by
`financial-engine_v2/backend/app/main.py`.
When this document conflicts with `SYSTEM_CONTRACT.md`, the contract wins.

## Mount layout

The FastAPI app mounts routes in these groups:

- `/api/*` from `app.api.routes`
- `/api/analysis/*` from `app.api.analysis`
- `/chat` and `/api/chat` from `app.routes.chat`
- `/research/*` from `app.routes.research`
- `/rag/query` at the app level
- compatibility aliases for `/ingest/*` at the app level

## Authentication

`require_api_key()` guards selected routes with `X-API-Key` only when
`settings.local_api_key` is configured.

- Read-only routes such as `/api/health`, `/api/docs`, `/api/financials`, and `/api/price`
  do not require an API key by default.
- Context diagnostic reads under `/api/context/verification*` require `X-API-Key`
  when `settings.local_api_key` is configured. `/api/context/ticker` remains a
  backend-owned context read, but unauthenticated configured-key responses
  redact operator diagnostics such as source paths/hashes, extraction failures,
  announcement excerpts/source paths, low-confidence rows, and internal error details.
- Mutating routes such as `/ingest/*`, `/backfill/*`, `/process/*`, and `/api/analysis/{ticker}`
  do require the dependency where declared.
- Memory/thesis mutation routes under `/api/context/memory/*` and `/api/context/thesis/*`
  also require the dependency where declared.
- Operational job-state reads and streams under `/api/ops/*` require the
  dependency where declared because they expose run metadata and artifact paths.
- Intel Pulse diagnostic routes under `/api/cockpit/pulse` and
  `/api/cockpit/matrix` require the dependency where declared because they
  expose extraction-health, population, and failure-density diagnostics.
- TradingView webhook writes under `/api/cockpit/tv/alert` require a
  `webhook_token` JSON field or `X-TradingView-Webhook-Token` header matching
  `TV_WEBHOOK_TOKEN` / `settings.tv_webhook_token` and fail closed when no token
  is configured. The token is not persisted in alert history. TradingView alert
  history reads use `X-API-Key` when `settings.local_api_key` is configured.
- Extraction-review read routes under `/api/extraction-review/*` expose
  operator review state, run diagnostics, and snippet images; they require the
  dependency where declared.

## Route inventory

### Health and document reads

- `GET /api/health`
  - basic health response
- `GET /api/docs?ticker=...`
  - document inventory for one ticker
- `GET /api/financials?ticker=...`
  - structured financial rows for one ticker
- `GET /api/risk?document_id=...`
  - stored risk/guidance note for one document
- `GET /api/context/verification?ticker=...`
  - verification context bundle for extraction failures and low-confidence financial rows
  - ticker is optional; empty scope returns cross-ticker queue state
  - requires `X-API-Key` when `settings.local_api_key` is configured

### Context and memory routes (`/api/context/*`)

- `GET /api/context/ticker?ticker=...`
  - ticker context bundle: docs, financials, latest snapshot, announcement context,
    extraction failures, low-confidence financial rows
  - when `settings.local_api_key` is configured and no matching `X-API-Key` is
    supplied, diagnostic/path fields and announcement excerpts are redacted while
    ordinary context fields remain available
- `GET /api/context/company_dump?ticker=...`
  - expanded ticker dump including context + risk notes + price history + memory surfaces
  - inherits `/api/context/ticker` diagnostic/path redaction unless a matching
    `X-API-Key` is supplied when `settings.local_api_key` is configured
- `GET /api/context/memory?ticker=...`
  - combined memory view for one ticker:
    - company memory
    - market memory
    - user thesis memory
- `POST /api/context/memory/company/add`
  - manual qualitative company-memory insert
- `POST /api/context/memory/company/expire`
  - manual company-memory soft-expire
- `POST /api/context/memory/market/add`
  - manual qualitative market-memory insert (sector/macro scopes)
- `POST /api/context/memory/market/expire`
  - manual market-memory soft-expire
- `GET /api/context/thesis?ticker=...`
  - user thesis memory view for one ticker (entries + proposals)
- `POST /api/context/thesis/proposals`
  - create user thesis proposal (`create_thesis`, `add_evidence`, `invalidate`)
- `POST /api/context/thesis/proposals/{proposal_id}/confirm`
  - explicit confirmation step
- `POST /api/context/thesis/proposals/{proposal_id}/reject`
  - reject pending/confirmed proposal
- `POST /api/context/thesis/proposals/{proposal_id}/apply`
  - apply a confirmed proposal into durable thesis entries
- `GET /api/context/verification?ticker=...`
  - extraction verification queue context (ticker-scoped or global)
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `GET /api/context/verification/runs?limit=...`
  - latest verification run history snapshots
  - requires `X-API-Key` when `settings.local_api_key` is configured

### Retrieval and chat

- `POST /rag/query`
  - unified retrieval endpoint
  - accepted sources:
    - `asx_docs`
    - `news`
  - unsupported sources are rejected by request validation:
    - `commentary`
    - `hybrid`
  - commentary and hybrid retrieval remain owned by `/chat` until backend
    retrieval support is implemented for `/rag/query`
- `POST /chat`
- `POST /api/chat`
  - chat endpoint exposed at both paths
  - `analysis` mode delegates to `chat_with_tenn()`
  - `strategy` mode routes to proposal/confirm/apply helpers

### Cockpit web control-plane (`/api/cockpit/*`)

- `GET /api/cockpit/health`
  - aggregated cockpit-facing health for backend, llama.cpp, Ollama, Qdrant, Redis, and GPU snapshot
- `GET /api/cockpit/config`
  - cockpit runtime config snapshot (llm model/endpoint, profile, feature flags)
- `GET /api/cockpit/queue`
  - lightweight queue status summary
- `GET /api/cockpit/docs`
  - latest global document list for cockpit history views
  - requires `X-API-Key` when `settings.local_api_key` is configured because
    it exposes global document provenance, source URLs, and local `pdf_path`
    values
- `GET /api/cockpit/news/status`
  - read-only A2M/news split-truth status contract
  - public response redacts operator-only diagnostics such as artifact roots,
    absolute projection paths, evidence report paths, and Qdrant collection identity
  - full path-bearing diagnostics are service-internal unless a future guarded
    caller explicitly requests them
- `GET /api/cockpit/pulse?ticker=...`
  - Intel Pulse population and quality metrics, optionally ticker-scoped
  - requires `X-API-Key` when `settings.local_api_key` is configured because
    it exposes extraction-health and failure diagnostics
- `GET /api/cockpit/matrix?stage=...&ticker=...`
  - Intel Pulse diagnostic density matrix for one pipeline stage, optionally
    ticker-scoped
  - requires `X-API-Key` when `settings.local_api_key` is configured because
    it exposes entity-level extraction-state diagnostics
- `POST /api/cockpit/chat`
  - cockpit chat endpoint (blocking and SSE modes)
  - SSE emits status/chunk/tool/action-preview/done events
  - request payload contract:
    - web access flag is `web_search` (boolean)
    - retrieval flag is `rag` (boolean)
    - SQL diagnostics flag is `db_diagnostics` (boolean)
    - `enable_web` is not a `CockpitChatRequest` field and is ignored by strict clients
  - routing contract highlights:
    - explicit web-search phrasing (`search web for ...`, `web search ...`) routes to web enrichment
    - imperative ingest phrasing (`ingest <ticker>`) routes to action preview
    - ingest shortcuts and explicit web-search shortcuts are deterministic and non-overlapping
- `POST /api/cockpit/action/execute`
  - executes a confirmed cockpit action by `action_id` + `args`
  - returns command output on success, structured HTTP errors on validation/runtime failure
  - includes strategy-memory actions:
    - `create_thesis`
    - `add_thesis_evidence`
  - these actions write to `user_thesis_memory` through backend-owned store logic
- `POST /api/cockpit/tv/alert`
  - receives TradingView Pine Script webhook alerts
  - requires `webhook_token` in the JSON alert body, or
    `X-TradingView-Webhook-Token` for relay/manual callers, matching the
    configured webhook token
  - strips `webhook_token` before alert persistence
  - fails closed with `503` when no webhook token is configured
- `GET /api/cockpit/tv/alerts`
  - returns recent TradingView alerts from the local alert history file
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `POST /api/cockpit/feedback/flag`
  - persists a cockpit assistant turn plus user feedback with `feedback_type: "poor" | "good"`, transcript, and backend diagnostics
  - accepts `capture_kind: "chat_feedback" | "ui_issue" | "auto_diagnostic"`; `auto_diagnostic` is reserved for deterministic backend-observed issues such as tool failures, missing visible sources, truncation markers, timeouts, and latency/tool-count inefficiencies
  - poor feedback returns artifact paths, `report_id`, `read_api_path`, and a backend-generated Codex prompt keyed to the saved flag ID
  - good feedback uses the same backend-owned persistence path so strong responses can be reviewed later for training/tuning
  - persistence happens before optional LLM review so the save returns immediately; poor feedback may later get `analysis.json`, while positive feedback is stored immediately without the failure-analysis pass
- `GET /api/cockpit/feedback/flags?limit=...`
  - lists recent cockpit feedback reports with `report_id`, `feedback_type`, excerpt, and read API path
- `GET /api/cockpit/feedback/flags/{report_id}`
  - returns the saved feedback report bundle, markdown summary, and analysis payload by report ID
- `/api/cockpit/marketplace/price-intelligence/*`
  - standalone Marketplace price-intelligence route family mounted before the
    larger Cockpit router
  - includes tracked-product reads and creation, price-observation reads and
    ingestion, timelines, benchmark snapshots, and eBay sold-data sync
  - guarded by `require_api_key()` when `settings.local_api_key` is configured
  - Cockpit BFF/client callers must forward `X-API-Key` for guarded reads and
    mutations

### Flagged chat references

Flagged cockpit chats should be referenced by backend API, not by assuming a local
filesystem path visible to the current shell or agent runtime.

Canonical discovery flow:

- list recent flags:
  - `GET /api/cockpit/feedback/flags?limit=10`
- read one flagged chat by ID:
  - `GET /api/cockpit/feedback/flags/{report_id}`

Important fields:

- `report_id`
  - stable identifier for one flagged chat report
- `feedback_type`
  - whether the saved example was marked `poor` or `good`
- `read_api_path`
  - backend-owned path Codex or other tools should use to read the saved flag
- `bundle`
  - saved transcript snapshot, flagged message, backend turn, runtime context
- `summary_markdown`
  - compact human-readable summary of the flagged turn
- `analysis`
  - backend-generated review of likely failure modes when available

Example operator flow:

1. Call `GET /api/cockpit/feedback/flags?limit=5`
2. Copy the newest `report_id`
3. Refer Codex to `http://127.0.0.1:8000/api/cockpit/feedback/flags/{report_id}`

Example prompt for Codex:

```text
Investigate this flagged cockpit response and fix the underlying bug.

Read:
http://127.0.0.1:8000/api/cockpit/feedback/flags/flag_20260409_074407_58b51013

Check the flagged message, transcript, backend_turn, routing metadata, and analysis.
Identify root cause in code, implement the minimal safe fix, and verify it.
```

Runtime note:

- canonical backend persistence root is `${DATA_ROOT}/reports/...` (for example
  `/data/reports/...` in Docker Compose)
- some services keep a writable fallback under `financial-engine_v2/backend/reports/...`
  when `DATA_ROOT` is unavailable or not writable
- the API above is the supported way to retrieve flagged chats across environments

### System control-plane and capability state

- `GET /api/system/status`
  - point-in-time backend system status snapshot
- `GET /api/system/capabilities`
  - backend authority for Cockpit capability state and remediation proposals
  - returns:
    - `access` state for `web_enabled`, `rag_enabled`, and `db_diagnostic_query_enabled`
    - dependency health for database, Redis, Qdrant, chat runtime, extraction runtime, and embedding runtime
    - feature status for ingestion, extraction, embeddings, and RAG
    - proposal inventory such as `start_extraction_runtime`, `restore_qdrant`, `restore_embedding_runtime`, `rebuild_embeddings`, and access toggles
  - important limitation:
    - the capability snapshot may advertise informational proposals that are not yet executable through `POST /api/system/proposals/apply`
- `POST /api/system/proposals/apply`
  - applies one backend-owned proposal by `proposal_id`
  - current supported access proposals:
    - `enable_web_access`
    - `disable_web_access`
    - `enable_rag_access`
    - `disable_rag_access`
    - `enable_dbdiag_access`
    - `disable_dbdiag_access`
  - current supported runtime proposal:
    - `start_extraction_runtime`

### Ops job state (`/api/ops/*`)

The Ops job-state surface is intended for Cockpit operator views. These routes
require `X-API-Key` when `settings.local_api_key` is configured:

- `GET /api/ops/jobs`
  - list persisted and synthetic operational jobs
- `GET /api/ops/jobs/active`
  - list pending/running operational jobs
- `GET /api/ops/jobs/{job_id}`
  - read one job run
- `GET /api/ops/jobs/{job_id}/events`
  - read job event history
- `GET /api/ops/jobs/{job_id}/artifacts`
  - read job artifact metadata
- `GET /api/ops/stream`
  - stream job events via SSE
  - clients must send credentials as headers through a header-capable SSE
    mechanism; durable API keys must not be embedded in browser URLs

### Commentary and framework ingestion

- `POST /api/ingest/transcript`
- `POST /ingest/transcript`
  - ingest a transcript into backend-owned commentary storage
- `POST /api/ingest/book`
- `POST /ingest/book`
  - ingest a book/framework document into backend-owned source storage

### Market data and fundamentals

- `GET /api/price`
  - market price endpoint
  - routes through Yahoo or OpenBB sidecar depending on runtime config
- `GET /api/fundamentals/profile`
- `GET /api/fundamentals/summary`
- `GET /api/fundamentals/statements`
  - fundamentals endpoints backed by the OpenBB sidecar provider
  - optional staging writes depend on runtime settings

### Backfill and document processing

- `POST /api/backfill/asx20`
  - enqueue or run ASX20 backfill
- `POST /api/backfill/ticker/{ticker}`
  - enqueue or run ticker backfill
- `POST /api/process/document/{document_id}`
  - process one document by `document_id`
  - intended for re-processing an already-downloaded document
  - if the local file is missing and the row still has empty `pdf_sha256`, the backend first runs the canonical PDF download path, then proceeds with extraction
- `POST /api/process/ticker/{ticker}`
  - process downloaded-but-unextracted documents for a ticker

### Extraction verification and review

- `POST /api/extraction-eval/real-gold`
  - runs the current `run_multipass_extraction()` pipeline against the real gold corpus under `financial-engine_v2/data/extraction_gold_real`
  - accepts optional JSON body fields:
    - `limit`
    - `tolerance`
    - `method` and `strict_method` — parser backend selection (`auto`, `docling`, `pymupdf`, `anthropic`)
    - `prompt_variant_id` — bundle id resolved via `app.services.prompt_registry.resolve()`; `None` selects the canonical `"default"` bundle (the one that pins `extraction_runs.prompt_hash` to its historical value)
    - `model_override` — llama.cpp model id (e.g. `qwen2.5-14b-instruct`); threaded through every LLM call in the run via `metadata.requested_model`, honored by `app.services.llm._resolve_runtime_from_metadata`
  - default (no query string): blocking execution, returns inline `200 OK` JSON summary plus per-document metric/trust results for the verification UI; response echoes `prompt_variant_id` and `model_override` for audit. Existing callers (cockpit-ui verification surface, `scripts/run_prompt_model_matrix.py`, E2E tests) rely on this blocking shape
  - optional `?background=true`: schedules the run on a background daemon thread backed by an in-memory task registry (`app.services.eval_task_registry`) and returns `202 Accepted` with `{ "task_id": "<uuid4.hex>", "status": "pending" }` immediately. Use this for full-corpus runs that would otherwise exceed the HTTP client timeout. **Scope limits:** the registry is process-local; on backend restart all scheduled task state is lost. Persistence is intentionally out of scope for this slice — a DB-backed implementation can replace the registry later without changing the endpoint contract
  - batch driver: `financial-engine_v2/scripts/run_prompt_model_matrix.py` enumerates (prompt_variant × model) cells in model-major order to minimize llama.cpp `--models-max 1` VRAM swaps
- `GET /api/extraction-eval/real-gold/tasks/{task_id}`
  - polls the status of a previously-scheduled background run
  - returns `{ "task_id", "status", "created_at", "updated_at", "result", "error" }` where `status` is one of `pending`, `running`, `completed`, `failed`; `result` is populated only on `completed` (same shape as the blocking POST response), `error` only on `failed`
  - returns `404 Not Found` for an unknown `task_id` (including one observed before a backend restart)
  - CLI client: `scripts/run_real_extraction_eval.py` always uses `?background=true` + poll, capping each HTTP call at 60 s while honoring the CLI-level `--timeout-seconds` as the overall deadline via `time.monotonic()`
- `POST /api/extraction-review/session`
  - builds a manual metric-review session from the latest extracted run(s) for selected document IDs
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `GET /api/extraction-review/runs?ticker=...&limit=...`
  - returns recent manual review extraction runs
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `GET /api/extraction-review/sessions?ticker=...&limit=...`
  - returns saved manual review session summaries
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `GET /api/extraction-review/session/{session_id}`
  - loads one saved manual review session snapshot
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `POST /api/extraction-review/session/{session_id}/decision`
  - persists one manual reviewer decision (`approved`, `wrong`, `abstain`)
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `GET /api/extraction-review/errors?limit=...`
  - returns the structured wrong-metric queue accumulated from manual review decisions
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `GET /api/extraction-review/run/{run_id}?limit=...`
  - returns run-status diagnostics for one extraction review run
  - requires `X-API-Key` when `settings.local_api_key` is configured
- `GET /api/extraction-review/snippets/{image_name}`
  - serves generated evidence snippet PNGs for manual extraction review
  - requires `X-API-Key` when `settings.local_api_key` is configured
  - preserves image-name and resolved-path traversal checks before serving files

### Analysis modules

- `POST /api/analysis/{ticker}`
  - run analysis modules and return structured results
- `GET /api/analysis/{ticker}`
  - read latest saved module artifacts
- `GET /api/analysis/risk`
  - risk-analysis helper route in `app.api.routes`

### Research synthesis

- `POST /research/synthesize`
  - server-side synthesis of gathered research sources into a structured brief
  - used by cockpit deep research flows
  - requires `X-API-Key` when `settings.local_api_key` is configured because
    synthesis is a server-side inference path, not a passive public read

## Notes on compatibility and drift

- The canonical retrieval route is `POST /rag/query`, not `POST /api/rag/query`.
- The chat endpoint is intentionally exposed at both `/chat` and `/api/chat`.
- Ingest routes are intentionally exposed both under `/api/ingest/*` and top-level `/ingest/*`.
- Cockpit access state is backend-owned through `/api/system/capabilities` and `/api/system/proposals/apply`; Cockpit should treat those routes as the authority rather than maintaining a parallel access toggle state.
- Today there is still a partial mismatch between advertised proposals and executable proposals. Document operator flows against the apply endpoint, not the full capability proposal list.

## Source files

- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/api/context.py`
- `financial-engine_v2/backend/app/api/analysis.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/routes/ops_api.py`
- `financial-engine_v2/backend/app/routes/research.py`
