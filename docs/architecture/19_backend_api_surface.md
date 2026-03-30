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
- Mutating routes such as `/ingest/*`, `/backfill/*`, `/process/*`, and `/api/analysis/{ticker}`
  do require the dependency where declared.

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

### Retrieval and chat

- `POST /rag/query`
  - unified retrieval endpoint
  - current implemented sources:
    - `asx_docs`
    - `news`
  - current not-yet-implemented sources return `501`:
    - `commentary`
    - `hybrid`
- `POST /chat`
- `POST /api/chat`
  - chat endpoint exposed at both paths
  - `analysis` mode delegates to `chat_with_tenn()`
  - `strategy` mode routes to proposal/confirm/apply helpers

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
  - process one already-downloaded document
- `POST /api/process/ticker/{ticker}`
  - process downloaded-but-unextracted documents for a ticker

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

## Notes on compatibility and drift

- The canonical retrieval route is `POST /rag/query`, not `POST /api/rag/query`.
- The chat endpoint is intentionally exposed at both `/chat` and `/api/chat`.
- Ingest routes are intentionally exposed both under `/api/ingest/*` and top-level `/ingest/*`.

## Source files

- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/api/analysis.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/app/routes/research.py`
