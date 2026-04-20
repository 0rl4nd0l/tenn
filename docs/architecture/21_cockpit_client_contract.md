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
| C10 | Web UI active-model/switch UX reflects backend authority rather than stale client state | `cockpit-ui/components/cockpit/chat/chat-screen.tsx`, `cockpit-ui/components/cockpit/cockpit-status-bar.tsx`, `cockpit-ui/lib/cockpit-config.ts` | UI should compare normalized backend-backed runtime identity before showing switch-wait states | **conform** |
| C11 | Web UI commentary attachments remain ephemeral and backend-authoritative | `cockpit-ui/components/cockpit/chat/chat-screen.tsx`, `cockpit-ui/lib/hooks/use-attached-sources.ts`, `cockpit-ui/lib/api-client.ts` | The browser stores only per-tab attachment metadata and forwards `attached_sources` to backend chat routes; no client retrieval path was added | **conform** |
| C12 | Source contract bypass requires PURE refusal — no financial claims | `backend/app/routes/cockpit_api.py` `_enforce_visible_source_contract` + `_CONTAINS_FINANCIAL_CLAIM_RE` | A response hedged with "I cannot confirm" that also contains named tickers, dollar amounts, percentages, or financial events is blocked by the guard — the `_EXPLICIT_UNVERIFIED_RESPONSE_RE` bypass only fires when `_CONTAINS_FINANCIAL_CLAIM_RE` does NOT match | **conform** |
| C13 | Agent hard-blocks substantive tool-less responses after one grounding nudge | `cockpit/core/agent_loop.py` `grounding_nudges_given` counter + `_response_is_pure_refusal()` | After the first grounding nudge, any non-pure-refusal response that still lacks tool evidence is replaced with a safe refusal; the model cannot answer substantive questions without tools on a second attempt | **conform** |
| C14 | Market-wide queries must not receive active ticker context | `cockpit/core/agent_loop.py` intent-aware ticker injection + `cockpit/core/query_intent.py` | MARKET_WIDE and COMMAND intents bypass the `Current ticker context: X` prefix so "news today?" searches the whole corpus | **conform** |
| C15 | Imperative commands short-circuit to action proposals before agent loop | `cockpit/core/command_router.py` + `AgentLoop.run()` pre-loop check | `ingest VEA`, `chart BHP`, `update CBA` are matched by regex pre-router and returned as `action_preview` without entering the LLM loop | **conform** |
| C16 | Verification run history persisted and exposed via backend endpoint | `backend/app/services/cockpit_service.py` `record_verification_run` + `GET /api/context/verification/runs` | Run metadata stored in `$DATA_ROOT/cockpit_verification_runs.json`; frontend verification-screen fetches on mount and shows ticker/date/pass-fail/re-run panel | **conform** |

---

## 10. Related documents

- `docs/architecture/SYSTEM_CONTRACT.md` — authoritative invariants.
- `docs/architecture/19_backend_api_surface.md` — full backend route inventory.
- `docs/architecture/18_cockpit_memory.md` — Cockpit memory layers (separate concern).
- `docs/ops/cockpit_operator_observability.md` — link-only operator runbook.
- `docs/entrypoints.md` — canonical boot and health checks.
