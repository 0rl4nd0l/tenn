# Cockpit Contract Enforcement Plan

Pre-flight:
- Session tag: `[SESSION: cockpit-contract-enforcement]`
- Branch: `cloud/session-20260319`
- Worktree: linked worktree at `/home/l4nd0/tenn` (`git worktree list`), not `main`
- Target layer: `Client (Cockpit) + Storage/Retrieval boundary`
- Relevant contract rules: `SYSTEM_CONTRACT.md` §§1.1, 1.2, 1.3, 2, 5.1
- What must not change: backend-owned extraction/retrieval authority, extraction pipeline, `multipass_extraction.py`, `embeddings.py`, eval fixtures, Qdrant schema, existing Cockpit chat/watchlist/dossier scratch flows
- Why this planning pass is safe: read-only analysis plus plan creation only; no implementation or runtime mutation

Notes:
- The requested audit paths are shifted in this checkout. The actual files are under `financial-engine_v2/cockpit/...`.
- `cockpit/ui/tool_router.py` does not exist here. The relevant wiring lives in `financial-engine_v2/cockpit/core/tools.py` and `financial-engine_v2/cockpit/integrations/backend_api.py`.
- Claude memory index at `/home/l4nd0/.claude/projects/-home-l4nd0-tenn/memory/MEMORY.md` could not be read from this session due to filesystem permission denial, so the plan below is grounded in the checked-out code and commit baseline `e5af6718`.

## 1. Call-site inventory

### Backend API surface relevant to this migration

Current backend endpoints confirmed from `financial-engine_v2/backend/app/api/routes.py`, `financial-engine_v2/backend/app/routes/chat.py`, `financial-engine_v2/backend/app/routes/research.py`, `financial-engine_v2/backend/app/api/analysis.py`, and `financial-engine_v2/backend/app/main.py`:

- `GET /api/health`
- `GET /api/docs?ticker=...`
- `GET /api/financials?ticker=...`
- `GET /api/risk?document_id=...`
- `GET /api/price`
- `GET /api/fundamentals/profile`
- `GET /api/fundamentals/summary`
- `GET /api/fundamentals/statements`
- `POST /rag/query`
- `POST /chat`
- `POST /api/chat`
- `POST /research/synthesize`
- `POST /api/analysis/{ticker}`
- `GET /api/analysis/{ticker}`
- `GET /api/system/status`
- `GET /api/system/capabilities`
- `POST /api/system/proposals/apply`

No backend endpoint currently exposes:
- `cockpit_announcement_context`
- extraction failures from `extraction_runs`
- low-confidence financial rows from `asx_periodic_financials`
- a unified ticker-context bundle that replaces Cockpit-side dataset fusion
- transcript-review approval/upsert behind HTTP
- SQL diagnostics behind backend HTTP

### Inventory table

| Call site | Exact lines | Direct access | Data touched | Existing backend endpoint | Other Cockpit features coupled to it |
|---|---:|---|---|---|---|
| `financial-engine_v2/cockpit/integrations/db_reader.py` | 20-22 | creates SQLAlchemy engine from `database_url` | direct Postgres/SQLite connection | No | Used across `ui/app.py`, `core/tools.py`, `core/tool_executor.py`, `core/research/deep_research.py`, `core/verification.py`, `ui/screens.py` |
| `financial-engine_v2/cockpit/integrations/db_reader.py` | 38-55 | `get_docs()` SQL | `documents` | Partial: `GET /api/docs` exists | ToolRouter context loading, announcement search, preferred web domains, updater snapshot, verification |
| `financial-engine_v2/cockpit/integrations/db_reader.py` | 57-73 | `get_financials()` / `get_latest_financial_snapshot()` SQL | `asx_periodic_financials` | Partial: `GET /api/financials` exists | Tool executor, deep research, updater screen, snapshot flow |
| `financial-engine_v2/cockpit/integrations/db_reader.py` | 75-90 | `get_announcement_context()` SQL | `cockpit_announcement_context` | No | ToolRouter context load, announcement search, deep research |
| `financial-engine_v2/cockpit/integrations/db_reader.py` | 92-115 | `get_extraction_failures()` SQL | `extraction_runs` joined to `documents` | No | ToolRouter context load, data quality tool, verification |
| `financial-engine_v2/cockpit/integrations/db_reader.py` | 117-135 | `run_diagnostic_query()` SQL | allowlisted diagnostic SQL against local DB | No | `/dbdiag` capability; separate diagnostics concern |
| `financial-engine_v2/cockpit/integrations/db_reader.py` | 137-159 | `get_low_confidence_financials()` SQL | `asx_periodic_financials` | No | ToolRouter context load, data quality tool, verification |
| `financial-engine_v2/cockpit/integrations/transcript_review.py` | 41-71 | imports backend embedding helpers and writes to Qdrant | Qdrant collection from staged metadata, default `commentary_chunks`; calls `verify_qdrant()` and `upsert_points()` | No | Transcript approval path only; isolated high-risk path |
| `financial-engine_v2/cockpit/core/tools.py` | 104-153 | `_load_ticker_context()` assembles ticker bundle via `DbReader` | docs, announcement context, financials, extraction failures, low-confidence rows | Partial | Used by `query_ticker_data` and any local context composition that consumes `gather_local_context()` |
| `financial-engine_v2/cockpit/core/tools.py` | 568-590 | `get_preferred_web_domains()` falls back to `DbReader.get_docs()` | `documents.source_url` | Partial: docs endpoint exists | Web-domain preference and source shaping |
| `financial-engine_v2/cockpit/core/tool_executor.py` | 192-204 | `_exec_get_financials()` | `asx_periodic_financials` | Partial | Direct read-only tool path |
| `financial-engine_v2/cockpit/core/tool_executor.py` | 219-231 | `_exec_search_announcements()` | `documents`, `cockpit_announcement_context` | Partial | Direct read-only tool path |
| `financial-engine_v2/cockpit/core/tool_executor.py` | 246-262 | `_exec_get_data_quality()` | `extraction_runs`, low-confidence `asx_periodic_financials` rows | No | Direct read-only tool path |
| `financial-engine_v2/cockpit/core/research/deep_research.py` | 85-90 | `_gather()` financial read | `asx_periodic_financials` | Partial | Deep research only |
| `financial-engine_v2/cockpit/core/research/deep_research.py` | 122-130 | `_gather()` announcement reads | `documents`, `cockpit_announcement_context` | Partial | Deep research only |
| `financial-engine_v2/cockpit/ui/app.py` | 165-168 | instantiates `DbReader` and stores it on app | local DB authority in client | No | Wiring root for most direct DB reads |
| `financial-engine_v2/cockpit/ui/app.py` | 1822-1856 | updater snapshot and verification use `DbReader` directly | latest financial row, docs, verification inputs | Partial | Updater/snapshot and verification UI |
| `financial-engine_v2/cockpit/ui/screens.py` | 412-414 | updater “Show Latest Financial Row” button | latest `asx_periodic_financials` row | Partial | Updater screen |
| `financial-engine_v2/cockpit/core/verification.py` | 10-58 | verification aggregates via `DbReader` | docs, extraction failures, low-confidence rows | Partial | Verification screen and exported verification payload |

### Existing good boundary-aligned paths

- `financial-engine_v2/cockpit/ui/app.py:187-240` already wires `BackendApiClient` into Cockpit.
- `financial-engine_v2/cockpit/integrations/backend_api.py:119-153` uses backend-owned `POST /rag/query`.
- `financial-engine_v2/cockpit/integrations/backend_api.py:155-193` uses backend-owned `POST /research/synthesize`.
- `financial-engine_v2/cockpit/integrations/qual_context.py` already treats backend RAG as the retrieval authority.

### Breakage assessment if direct access is removed without replacement

Removing direct DB/Qdrant access immediately would break:
- ticker-context gathering in `ToolRouter`
- `get_financials`, `search_announcements`, and `get_data_quality` tool calls
- deep research gather step before backend synthesis
- updater “latest row”, updater snapshot, and verification workflows
- transcript approval of staged commentary chunks

The only direct-access surface that is plausibly retainable as an exception is diagnostic SQL, and only if explicitly carved out as backend-mediated diagnostics rather than Cockpit-owned DB access.

## 2. Missing endpoint gap analysis

| Cockpit call site | Data needed | Existing backend endpoint? | New endpoint required |
|---|---|---|---|
| `DbReader.get_docs()` consumers | ordered document metadata by ticker, including `pdf_sha256` | YES, partial via `GET /api/docs` | Extend `GET /api/docs` or add `GET /api/context/ticker` so ordering and `pdf_sha256` parity are guaranteed |
| `DbReader.get_financials()` / latest snapshot consumers | recent financial rows, sometimes latest-only | YES, partial via `GET /api/financials` | Possibly no new endpoint if shape is extended; otherwise include in `GET /api/context/ticker` |
| `DbReader.get_announcement_context()` consumers | `cockpit_announcement_context` rows by ticker | NO | `GET /api/context/announcements?ticker=...&limit=...` or fold into `GET /api/context/ticker` |
| `DbReader.get_extraction_failures()` consumers | failed `extraction_runs`, optionally filtered by ticker | NO | `GET /api/context/extraction-failures` or fold into `GET /api/context/ticker` |
| `DbReader.get_low_confidence_financials()` consumers | low-confidence financial rows, optionally filtered by ticker and threshold | NO | `GET /api/context/low-confidence-financials` or fold into `GET /api/context/ticker` |
| `ToolRouter._load_ticker_context()` | one backend-authoritative bundle for docs, announcement context, financials, extraction failures, low-confidence rows | NO | Recommended: `GET /api/context/ticker?ticker=...` |
| `ToolExecutor._exec_search_announcements()` | docs + announcement context | PARTIAL | Can use `GET /api/context/announcements` or subset of `GET /api/context/ticker` |
| `ToolExecutor._exec_get_data_quality()` and `core/verification.py` | extraction failures + low-confidence rows + docs | PARTIAL | Recommended: `GET /api/context/verification?ticker=...` or reuse `GET /api/context/ticker` plus backend-side verification endpoint |
| `ui/app.py` updater snapshot / `ui/screens.py` latest row | latest financial snapshot and docs after update | PARTIAL | Either use extended existing docs/financials endpoints or expose `GET /api/context/ticker` |
| `deep_research.py` gather step | financials + docs + announcement context | PARTIAL | Recommended: `GET /api/context/ticker` |
| `transcript_review.py` approve path | backend-owned staged transcript approval and Qdrant upsert | NO | `POST /api/commentary/transcripts/{source_id}/approve` |
| transcript review list/reject/purge operations | staged transcript queue state | NO | Optional but likely needed for clean ownership: `GET /api/commentary/transcripts/pending`, `POST /api/commentary/transcripts/{source_id}/reject`, `POST /api/commentary/transcripts/purge-expired` |
| diagnostic SQL (`run_diagnostic_query`) | allowlisted read-only DB diagnostics | NO | If retained: `POST /api/system/dbdiag/query` or similar, gated by backend access state |

Recommended endpoint shape:
- Prefer one backend-owned aggregate endpoint for authoritative ticker context: `GET /api/context/ticker`
- Keep specialized endpoints only where the UX/action is operationally distinct: transcript review and DB diagnostics

Why the aggregate endpoint is safer:
- It prevents Cockpit from reassembling authoritative datasets itself.
- It collapses multiple current `DbReader` calls into one backend-owned context contract.
- It reduces migration risk for `ToolRouter`, `deep_research`, updater snapshot, and verification because they all need overlapping data.

## 3. Proposed SYSTEM_CONTRACT.md amendment

Proposed insertion under §1.2 Cockpit Role, immediately after the current “MUST NOT” list:

> ### 1.2.a Cockpit Scratch Memory (Permitted, Non-Authoritative)
>
> Cockpit MAY maintain local scratch memory for user workflow continuity, including:
> - session chat history
> - watchlists and user preferences
> - per-ticker dossier notes
> - user-authored strategy criteria
> - transient observations and working notes
>
> This scratch memory is strictly non-authoritative. It exists only to support client-side reasoning, continuity, and operator workflow.
>
> Cockpit scratch memory MUST NOT:
> - be treated as source of truth for financial data, extracted metrics, document metadata, or retrieval results
> - override, correct, enrich, or substitute backend-owned authoritative records
> - be queried as a retrieval authority in place of backend retrieval
> - be merged with authoritative backend data in a way that makes provenance ambiguous
>
> Any output that uses Cockpit scratch memory MUST preserve the distinction between:
> - authoritative backend data (Postgres, Qdrant, backend retrieval outputs), and
> - non-authoritative Cockpit memory (notes, preferences, dossier findings, strategy context, session artifacts)
>
> Dossier entries are operator/agent notes, not validated financial facts. They may inform analysis prompts, but they MUST NEVER be presented or consumed as authoritative financial data.

Optional reinforcing sentence for §1.3 Retrieval Boundary:

> Cockpit-local scratch memory may be supplied to analysis as user context, but it is not part of retrieval authority and must remain provenance-distinct from backend retrieval outputs.

## 4. Staged migration plan

Migration ordering rule:
- No Cockpit direct-access path is removed until the replacement backend endpoint exists, is exercised through `BackendApiClient`, and the corresponding UI/tool flow has been verified.

### Stage A: Add backend read endpoints, no Cockpit behavior change

Goal:
- Introduce backend-owned read APIs for all currently direct-authority data needs while leaving Cockpit on current paths.

Files to change:
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/main.py` only if route registration or shared models require it
- Possibly a new backend service/helper module for context assembly if needed
- `financial-engine_v2/cockpit/integrations/backend_api.py`
- Backend tests covering the new endpoints

Changes:
- Add backend-authoritative endpoint(s) for:
  - ticker context bundle (`docs`, `financials`, `announcement_context`, `extraction_failures`, `low_confidence_financials`, `db_error`-style availability signals if needed)
  - transcript review approval path
  - optional transcript pending/reject endpoints if the Cockpit UI uses them
  - explicit DB diagnostic query endpoint if diagnostics are retained
- Extend `BackendApiClient` with methods for the new endpoint(s), but do not switch consumers yet.

Verification:
- backend route tests for response shape, ticker filtering, threshold handling, and empty-data behavior
- manual `curl` against the new endpoint(s)
- confirm no changes to existing Cockpit flows because no call sites are switched yet

Milestone commit boundary:
- backend endpoints exist and are verified; Cockpit still uses legacy reads

### Stage B: Wire Cockpit authoritative reads to backend endpoints, keep `DbReader` only as temporary fallback shim

Goal:
- Move all non-diagnostic authoritative reads behind `BackendApiClient` while preserving user-visible behavior.

Files to change:
- `financial-engine_v2/cockpit/core/tools.py`
- `financial-engine_v2/cockpit/core/tool_executor.py`
- `financial-engine_v2/cockpit/core/research/deep_research.py`
- `financial-engine_v2/cockpit/core/verification.py`
- `financial-engine_v2/cockpit/ui/app.py`
- `financial-engine_v2/cockpit/ui/screens.py`
- `financial-engine_v2/cockpit/integrations/backend_api.py`
- Cockpit tests currently mocking `db_reader`

Changes:
- Make `ToolRouter` authoritative context loading call backend context APIs, not `DbReader`.
- Replace tool executor reads (`get_financials`, `search_announcements`, `get_data_quality`) with backend client calls.
- Replace `deep_research._gather()` authoritative reads with backend context calls.
- Replace updater snapshot/latest-row/verification reads with backend calls.
- Keep `DbReader` present only for explicit diagnostics during this stage if fallback is needed for rollout safety.
- Preserve dossier/session/strategy scratch stores unchanged.

Verification:
- Cockpit unit tests updated to mock `BackendApiClient` instead of `db_reader` for migrated flows
- targeted tests for `deep_research`, strategy tools, updater snapshot, and verification screen
- backend unavailable behavior tested explicitly: user gets clear degraded response instead of silent hard failure

Milestone commit boundary:
- all normal Cockpit authoritative reads flow through backend, with diagnostics still separate

### Stage C: Remove `DbReader` as a general data-access layer

Goal:
- Eliminate direct Postgres reads from Cockpit for authoritative data.

Files to change:
- `financial-engine_v2/cockpit/integrations/db_reader.py`
- `financial-engine_v2/cockpit/ui/app.py`
- any remaining `db_reader` references found by `rg`
- Cockpit tests still built around `db_reader`

Changes:
- Remove or sharply narrow `DbReader` so it no longer exposes docs/financials/announcement/extraction/low-confidence reads.
- If diagnostics are retained, either:
  - keep a tiny diagnostics-only adapter with no general data reads, or
  - delete `DbReader` entirely and move diagnostics fully to backend HTTP.
- Remove `DbReader` injection from `ToolRouter` if no longer needed.

Verification:
- `rg -n "db_reader\\.|DbReader\\(" financial-engine_v2/cockpit -S` returns only approved diagnostic-only uses, or none
- updater, verification, deep research, and read-only tools still work through backend APIs

Milestone commit boundary:
- Cockpit no longer performs direct authoritative DB reads

### Stage D: Isolate transcript-review Qdrant write behind backend endpoint

Goal:
- Remove the highest-risk direct storage violation separately from the DB migration.

Files to change:
- `financial-engine_v2/backend/app/api/routes.py` and/or dedicated commentary routes
- `financial-engine_v2/cockpit/integrations/backend_api.py`
- `financial-engine_v2/cockpit/integrations/transcript_review.py`
- transcript review tests on both backend and Cockpit sides

Changes:
- Add backend endpoint for staged transcript approval that:
  - reads staged points server-side
  - validates Qdrant availability server-side
  - performs `upsert_points()` server-side
  - updates source registry and staging index server-side
- Update Cockpit transcript review service to call backend endpoint, not import backend internals.
- Remove Cockpit-side direct imports of `verify_qdrant` and `upsert_points`.

Verification:
- backend tests for approve success, missing staged file, empty staged file, and Qdrant failure cases
- Cockpit transcript review tests updated to mock backend client behavior
- `rg -n "verify_qdrant|upsert_points" financial-engine_v2/cockpit -S` returns no Qdrant-write call sites

Milestone commit boundary:
- Cockpit no longer writes to Qdrant directly

### Stage E: Contract/documentation closeout and diagnostic SQL decision

Goal:
- Encode the final boundary explicitly and close the migration loop.

Files to change:
- `docs/architecture/SYSTEM_CONTRACT.md`
- any Cockpit/architecture docs that describe local state or dossier behavior
- optionally backend docs for diagnostics endpoint if retained

Changes:
- Add the scratch-memory carve-out language from Section 3.
- Document the final status of DB diagnostics:
  - preferred: backend-mediated opt-in diagnostics only
  - not acceptable: silent return to Cockpit-owned DB authority
- Mark the transitional migration complete.

Verification:
- final grep audit:
  - no Cockpit imports of backend storage internals
  - no Cockpit direct DB reads except approved diagnostics path, if retained
  - no Cockpit direct Qdrant writes
- manual review of `SYSTEM_CONTRACT.md` language for ambiguity

Milestone commit boundary:
- contract matches implementation; migration complete

### Diagnostic SQL assessment

Recommendation:
- Retain diagnostic SQL only as an explicit, backend-mediated operator capability.

Reasoning:
- Diagnostics are operational introspection, not product retrieval.
- Today the enable/disable toggle is already backend-owned via `/api/system/capabilities` and `/api/system/proposals/apply`, but the actual query execution remains Cockpit-local.
- To preserve the capability without violating backend authority, query execution should move behind a backend endpoint and remain allowlisted, read-only, and opt-in.

Not recommended:
- keeping `DbReader` as a broad “just in case” fallback after Stage B
- treating diagnostics as justification for retaining general-purpose Cockpit DB access

## 5. Risk register

| Risk | What breaks | Mitigation |
|---|---|---|
| Stages done out of order | Removing Cockpit direct access before backend endpoint rollout breaks tools, updater snapshot, verification, and deep research gather | Keep Stage A before all client rewiring; do not remove old path until replacement is verified |
| Transcript-review move combined with DB migration | Harder fault isolation; Qdrant write failures become mixed with ticker-context regressions | Keep transcript review in its own Stage D |
| Backend unavailable at Cockpit startup | Current `DbReader` path degrades locally; backend-only path may disable price/RAG/context reads and potentially more UI actions | Add explicit degraded-mode messaging in Cockpit for backend-dependent flows; preserve startup without crash; tests must cover backend-down behavior |
| Missing aggregate endpoint | Cockpit reimplements data assembly by stitching several backend responses together, preserving architectural drift | Prefer a single backend ticker-context endpoint so assembly logic moves server-side |
| Hidden `DbReader` dependents missed | Residual direct DB reads survive in updater/verification/screens even after tools migration | Stage C includes grep audit and direct file review; inventory above already identifies the known residuals |
| Diagnostic SQL left Cockpit-local | Contract breach remains even if “normal” tool paths migrate | Decide explicitly in Stage E: migrate diagnostics behind backend or remove it |
| Verification semantics drift | If backend replacement omits `pdf_sha256` or ordering parity, updater snapshot and verification outputs change | Keep response-shape parity tests against the current `DbReader` behavior before switching clients |
| Deep research output changes | Deep research gather set may shrink if announcements/context endpoint is incomplete | Include deep research tests when wiring backend context, and verify gathered source keys stay stable |
| Eval regressions | Expected none, because extraction, embeddings, Qdrant schema, and eval fixtures are out of scope | Confirm no changes in extraction pipeline or eval fixtures; no eval baseline required for planning, but endpoint/client tests are required during implementation |

## 6. Estimated session count to complete

Estimated implementation sessions: `5`

Suggested breakdown:
- Session 1: Stage A backend read endpoints
- Session 2: Stage B Cockpit wiring for tools + deep research
- Session 3: Stage B/C updater, verification, and final `DbReader` removal for general reads
- Session 4: Stage D transcript review backend endpoint migration
- Session 5: Stage E contract/docs closeout and final grep/test audit

> Do not write any implementation code. Return the plan only.
