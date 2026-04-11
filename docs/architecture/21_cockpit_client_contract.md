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

Client-side helpers may live under `cockpit-ui/lib/` (e.g. `api-client.ts`).

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

## 9. Conformance matrix (SYSTEM_CONTRACT §1.2–§1.3)

Each row maps a **contract obligation** to **implementation** and an explicit **outcome**. Update this table when behavior intentionally changes.

| # | Contract obligation (summary) | Implementation pointers | Tests / notes | Outcome |
|---|--------------------------------|---------------------------|---------------|---------|
| C1 | Call backend APIs for authoritative reads when client is configured | `BackendApiClient`; `financial-engine_v2/cockpit/core/tools.py`, `tool_executor.py`, `verification.py`, research modules using `backend_api_client` | `financial-engine_v2/cockpit/tests/test_tool_executor_extraction.py`, `test_slash_commands.py`, `test_deep_research.py` | **conform** |
| C2 | No silent fallback to local DB for authoritative reads when backend is configured | Contract text in `SYSTEM_CONTRACT.md` §1.2; failure returns empty + error signal | Backend integration behavior covered indirectly via cockpit tests with mocks | **conform** (by contract spec; verify when touching error paths) |
| C3 | `DbReader` limited to diagnostics + legacy stubs | `financial-engine_v2/cockpit/integrations/db_reader.py` (diagnostics + legacy SQL stubs) | Stubs still execute SQL if invoked — only acceptable when `backend_api_client` is **not** configured per contract | **intentional deviation** — legacy / no-backend environments; **do not** use stubs for authoritative paths when backend is configured |
| C4 | Do not access Qdrant directly for commentary write authority | Preferred: `BackendApiClient` transcript approve via backend `/api/commentary/transcripts/*` | `financial-engine_v2/cockpit/tests/test_transcript_review.py` | **conform** for preferred path |
| C5 | Legacy direct Qdrant upsert from Cockpit for transcript approve | `TranscriptReviewService.approve()` in `financial-engine_v2/cockpit/integrations/transcript_review.py` (direct `verify_qdrant` / `upsert_points`) | Docstring states legacy path when backend API unavailable | **intentional deviation** — migrate callers to backend endpoint when possible |
| C6 | Request retrieval via backend (RAG) | `BackendApiClient.rag_query`, `qual_context.py` | `test_tool_executor_extraction.py` | **conform** for primary path |
| C7 | News context SQLite fallback when Qdrant/backend path fails | `financial-engine_v2/cockpit/core/tools.py` (`news_context`) | Logs fallback; not a second ranked retrieval engine — resilience only | **intentional deviation** — documented fallback; tighten if contract interpretation changes |
| C8 | No independent merge/rank as authority | Cockpit does not replace backend hybrid retriever for `/api/chat` | N/A | **conform** (scope: Cockpit client; backend owns `/chat` RAG) |
| C9 | Orchestration (subprocess actions, UI) without owning ingestion truth | `financial-engine_v2/cockpit/core/actions.py` runs scripts (e.g. ticker sync, loaders) | Actions invoke repo scripts; backend remains authority for persisted truth | **conform** |

---

## 10. Related documents

- `docs/architecture/SYSTEM_CONTRACT.md` — authoritative invariants.
- `docs/architecture/19_backend_api_surface.md` — full backend route inventory.
- `docs/architecture/18_cockpit_memory.md` — Cockpit memory layers (separate concern).
- `docs/ops/cockpit_operator_observability.md` — link-only operator runbook.
- `docs/entrypoints.md` — canonical boot and health checks.
