# Cockpit client contract (addendum)

This document is the **Cockpit-facing addendum** to `docs/architecture/SYSTEM_CONTRACT.md`. **Normative system rules** remain in the system contract; here we summarize **how Cockpit (Textual TUI + Next.js UI) is expected to behave**, which **HTTP surfaces** operators use, and a **conformance matrix** tied to the codebase.

If anything here conflicts with `SYSTEM_CONTRACT.md`, **the contract wins**.

---

## 1. Role (aligned with SYSTEM_CONTRACT §1.2–§1.3)

Cockpit is a **client and orchestration layer**:

- It **MUST** obtain authoritative financial and document context from the **backend** when `BackendApiClient` is configured (see `financial-engine_v2/cockpit/integrations/backend_api.py`).
- It **MUST NOT** act as a second source of truth for structured financial data, independent retrieval ranking, or ingestion pipelines that replace the backend.

**Retrieval:** Cockpit may **request** retrieval via backend APIs (e.g. RAG-shaped calls on the client). It **MUST NOT** implement its own retrieval pipeline as the authority for production answers when the backend is the configured path.

---

## 2. Health checks: liveness vs Cockpit health

Operators should treat these as **different questions**:

| Check | Typical use | Backend route | Notes |
|-------|-------------|---------------|--------|
| **Minimal liveness** | “Is the API process up?” | `GET /api/health` | Canonical boot check per `docs/entrypoints.md`. The Textual Cockpit client uses this path in `BackendApiClient.health()`. |
| **Aggregated Cockpit health** | “Are dependencies and Cockpit-oriented services in a good state?” | `GET /api/cockpit/health` | Implemented in `financial-engine_v2/backend/app/routes/cockpit_api.py`. May include probes beyond a single process (e.g. GPU, upstream services) depending on backend version. |

**Recommended order:** run **`/api/health`** first; if that passes and you need a fuller picture, use **`/api/cockpit/health`**.

The **Next.js** app may expose a same-origin BFF that **proxies or augments** health data for the browser (host GPU, etc.); see `cockpit-ui/app/api/cockpit/health/route.ts`. That BFF is **not** a substitute for the system contract — it is a **presentation and aggregation** layer for the UI.

---

## 3. Supported consumer patterns

| Consumer | Typical base URL | Role |
|----------|------------------|------|
| Operators, scripts, Textual Cockpit | Backend origin (e.g. `http://127.0.0.1:8000`) | Direct FastAPI routes under `/api/*` and `/api/cockpit/*`. |
| Browser (Cockpit web UI) | Next.js origin | Calls same-origin `cockpit-ui/app/api/cockpit/*` routes; those routes forward to the backend where appropriate. |

External automation **SHOULD** prefer the **backend** for stable contracts. Next BFF routes exist for **UI** needs and may change with frontend refactors.

---

## 4. Backend `/api/cockpit` surface (inventory)

Router is mounted with prefix **`/api/cockpit`** from `financial-engine_v2/backend/app/main.py`. Representative routes (see `financial-engine_v2/backend/app/routes/cockpit_api.py` for the authoritative list):

| Method | Path (relative to `/api/cockpit`) | Purpose (summary) |
|--------|-----------------------------------|-------------------|
| GET | `/health` | Aggregated health for Cockpit-oriented probes. |
| GET | `/config` | Cockpit configuration including **extraction activity** (`extraction_active`, `extraction_active_runs`, etc.) from `get_extraction_activity_snapshot()` in `financial-engine_v2/backend/app/services/router_state.py`. |
| GET | `/models` | Available / discovered models. |
| POST | `/models/load` | Load model on llama runtime (subject to server policy). |
| GET | `/queue` | Queue / routing status. |
| GET | `/docs` | Docs manifest for UI. |
| GET | `/pulse`, `/matrix` | Intel / pulse endpoints. |
| POST | `/action/preview`, `/action/execute` | Action preview and execution. |
| GET | `/action/jobs/{job_id}` | Action job status. |
| POST | `/feedback/flag` | Flag feedback. |
| GET | `/feedback/flags`, `/feedback/flags/{report_id}` | List / read flagged reports. |
| POST | `/chat` | Cockpit chat (streaming behavior — see tests below). |

---

## 5. Python client (`BackendApiClient`)

`financial-engine_v2/cockpit/integrations/backend_api.py` implements the **primary** HTTP client for the Textual Cockpit. It provides `health()` → **`GET /api/health`**, `capabilities()`, ticker and verification context, RAG/query helpers, transcript actions, and other backend calls. **Authoritative data paths** should go through this client when the backend is configured.

---

## 6. Next.js BFF (`cockpit-ui`)

Under `cockpit-ui/app/api/cockpit/` (non-exhaustive; glob the directory if routes were added):

- `health/route.ts` — UI health aggregation (backend + host probes).
- `restart/route.ts` — restart orchestration.
- `action/execute/route.ts` — action execution proxy.
- `action/jobs/[jobId]/route.ts`, `action/jobs/[jobId]/stop/route.ts` — job status / stop.
- `commentary/takeaways/route.ts` — thin browser proxy to backend commentary takeaway generation.
- `commentary/ephemeral-index/route.ts`, `commentary/ephemeral-index/[sessionId]/route.ts` — thin browser proxies for session-scoped commentary indexing lifecycle.
- `commentary/recent/route.ts` — thin browser proxy for recently approved commentary sources.
- `watchlist/route.ts`, `watchlist/[ticker]/route.ts` — thin browser proxies for watchlist CRUD.

Client-side helpers may live under `cockpit-ui/lib/` (e.g. `api-client.ts`).

These browser routes are **presentation-layer pass-throughs only**. Their presence in `cockpit-ui` does **not** guarantee that the matching backend route exists on every branch or environment.

### 6.1 Active model and switch-state UX

The web Cockpit UI may show both:

- a **selected model** (operator preference / requested model id), and
- an **active runtime model** (what the backend/router currently reports as loaded).

For correctness:

- the **active runtime model** shown in the UI **SHOULD** come from a backend-backed runtime snapshot such as `GET /api/cockpit/config` and not from stale client-only placeholders,
- client-side fallback values like `local` are presentation defaults only and **MUST NOT** be treated as authoritative runtime state,
- "switching" / "waiting for model switch" UI states **SHOULD** be based on backend-backed runtime identity and normalized model aliases, not on raw string inequality between a selected alias and a resolved runtime display name.

This keeps the UI aligned with SYSTEM_CONTRACT §1.2: Cockpit presents backend authority; it does not invent an independent model-truth state.

### 6.2 Ephemeral attached-source state

The web chat UI may keep a per-tab list of attached commentary sources in client state so the operator can:

- re-attach recently ingested commentary sources,
- carry those attachments across subsequent chat turns in the same browser tab,
- render non-authoritative UI affordances such as ingest summary cards and takeaways panels.

For correctness:

- this attachment list is **ephemeral client state only** and **MUST NOT** become an alternate source of truth,
- the browser **MUST** forward any attachment metadata to backend-owned chat/commentary endpoints rather than performing its own retrieval or ranking,
- any browser proxy route under `cockpit-ui/app/api/cockpit/*` remains a pass-through layer only; it **does not** authorize frontend-owned ingestion, retrieval, or watchlist truth.

Implementation note: the current web client forwards `attached_sources` in the chat payload, but the backend remains the contract authority for whether that field is accepted or ignored.

---

## 7. Streaming and chat tests

Cockpit chat streaming and API behavior are covered by backend tests such as:

- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- Other `financial-engine_v2/backend/tests/test_cockpit_api_*.py` files as applicable.

Use those tests as the **behavioral reference** for event shapes when docs and implementation disagree.

---

## 8. Authentication

Backend APIs that require authentication use the **`X-API-Key`** header pattern where configured. **Do not** document or paste real keys, tokens, or `.env` contents in repo markdown. See `docs/architecture/13_security_and_secrets.md`.

---

## 9. Conformance matrix (SYSTEM_CONTRACT §1.2, §1.3, §5.2)

Review date: `2026-04-21`

This matrix is intentionally evidence-scoped to files and tests inspected in this Cloud-4 pass.

| Clause | Implemented surface | Evidence (code/tests/docs) | Status | Notes |
|---|---|---|---|---|
| §1.2 Cockpit must read authoritative data via backend APIs when configured | Cockpit HTTP client + ticker/news context paths | `financial-engine_v2/cockpit/integrations/backend_api.py` (`/api/health`, `/rag/query`); `financial-engine_v2/cockpit/core/tools.py` (`_load_ticker_context`, `_load_ticker_context_from_backend`) | `compliant` | When configured, ticker context flows through backend endpoints. |
| §1.2 Cockpit must not silently substitute local authority when backend read fails | Ticker-context error handling returns explicit error payloads | `financial-engine_v2/cockpit/core/tools.py` (returns `db_error` on unavailable backend / backend exception) | `compliant` | Current implementation degrades visibly with explicit backend-unavailable signal. |
| §1.2 Cockpit must not use direct Postgres reads for authoritative flows | Legacy `DbReader` still ships direct SQL methods | `financial-engine_v2/cockpit/integrations/db_reader.py` (module header says diagnostics-only; methods `get_docs`, `get_financials`, etc. still execute SQL) | `partial` | Risk persists if callers regress to `DbReader`; guard is policy + call-site discipline, not full mechanical removal. |
| §1.2 Cockpit must not access Qdrant directly for authority | Legacy transcript approve path performs direct Qdrant upsert | `financial-engine_v2/cockpit/integrations/transcript_review.py` (`approve()` imports `verify_qdrant` and `upsert_points`) | `non-compliant` | Docstring marks this as legacy, but code path still exists and can bypass backend commentary API. |
| §1.3 Cockpit may request retrieval via backend, must not own retrieval logic | News retrieval calls backend first, then local SQLite fallback | `financial-engine_v2/cockpit/core/tools.py` (`get_news_context` Qdrant-first + `sqlite_fallback`); `financial-engine_v2/cockpit/tests/test_tool_executor_extraction.py` (fallback expectations at lines with `_source == "sqlite_fallback"`) | `partial` | Backend-first is in place; fallback still introduces cockpit-local retrieval surface. |
| §5.2 Unified retrieval interface `POST /rag/query` | Endpoint exists and enforces source enum | `financial-engine_v2/backend/app/main.py` (`@app.post("/rag/query")`) | `partial` | Interface exists, but not all declared sources are live yet. |
| §5.2 `source=asx_docs` implemented | ASX docs retrieval branch | `financial-engine_v2/backend/app/main.py` (`if body.source == "asx_docs": return query_rag(...)`) | `compliant` | Implemented and routed in backend authority layer. |
| §5.2 `source=news` implemented | News retrieval branch | `financial-engine_v2/backend/app/main.py` (`elif body.source == "news": return query_news_chunks(...)`) | `compliant` | Implemented and routed in backend authority layer. |
| §5.2 `source=commentary` should be served by unified retrieval contract | Current endpoint returns 501 | `financial-engine_v2/backend/app/main.py` (`elif body.source == "commentary": raise HTTPException(status_code=501, ...)`) | `partial` | Explicitly unimplemented in `/rag/query`; callers are redirected to `/chat`. |
| §5.2 `source=hybrid` should be served by unified retrieval contract | Current endpoint returns 501 | `financial-engine_v2/backend/app/main.py` (`elif body.source == "hybrid": raise HTTPException(status_code=501, ...)`) | `partial` | Explicitly unimplemented in `/rag/query`; callers are redirected to `/chat`. |

### 9.1 Highest-risk open gaps (ranked)

| Rank | Gap | Current status | Risk | Why it matters |
|---|---|---|---|---|
| 1 | Direct cockpit Qdrant write path for transcript approval remains callable | `non-compliant` | High | Violates backend-only authority and can reintroduce split-write behavior for commentary indexing. |
| 2 | Cockpit SQLite news fallback remains active when backend retrieval fails | `partial` | High | Keeps a client-side retrieval surface that can drift from backend ranking/filters. |
| 3 | `DbReader` legacy SQL methods still present | `partial` | Medium | Even with current call-site discipline, latent direct-DB methods increase regression risk. |
| 4 | `/rag/query` does not yet implement `commentary` and `hybrid` sources | `partial` | Medium | Unified retrieval contract remains incomplete, increasing route-shape divergence across clients. |

---

## 10. Related documents

- `docs/architecture/SYSTEM_CONTRACT.md` — authoritative invariants.
- `docs/architecture/19_backend_api_surface.md` — full backend route inventory.
- `docs/architecture/18_cockpit_memory.md` — Cockpit memory layers (separate concern).
- `docs/ops/cockpit_operator_observability.md` — link-only operator runbook.
- `docs/entrypoints.md` — canonical boot and health checks.
