# 2026-04-18 Memory Stabilization Design

Status: Implemented 2026-04-18
Owner: Codex
Scope: Backend and Cockpit memory/retrieval stabilization

## Implementation Status

Implemented scope:

- shared session-context fallback now prefers semantic OpenViking recall and falls back to recent turns only when semantic recall is empty
- orchestrator ticker resolution now rejects false ordinary-word tickers while preserving explicit and cue-driven ticker detection
- sector inference is now shared between signal routing and market-memory retrieval, so tickerless prompts like "iron ore sector" can recover stored sector context
- OpenViking client initialization is isolated per `SessionMemoryClient`, with temporary env scoping instead of process-global config pinning

Completed reliability follow-ups:

- Cockpit watchlist-history collection now uses the active thread id
- `/api/context/company_dump` now uses raw active market-memory rows and correct total counts instead of ranked slices
- qualitative company/market memory stores now enable SQLite `WAL`, `busy_timeout`, and bounded retry-on-busy behavior
- commentary/news memo `extract_and_store(...)` now returns structured `signal_routing` status instead of surfacing routing failures only in logs
- Cockpit qualitative-context bootstrap now ignores stale local embedding config and preserves the backend-only `rag_query` contract
- shared ticker inference now drives backend `query_orchestrator`, backend `rag`, Cockpit chat ticker detection, and Cockpit tool-executor news ticker inference from one helper instead of four drifting local implementations
- the dormant Cockpit `MemorySearch` SQLite-vec layer has been removed, along with its dead tests and the stale `sqlite-vec` backend dependency

Validation summary:

- focused memory/orchestrator regression lane: `90 passed`
- watchlist-history regression lane: `13 passed`
- context + market-memory raw-dump lane: `31 passed`
- qualitative memory SQLite hardening lane: `25 passed`
- memo-routing status lane: `6 passed`
- commentary/news task compatibility lane: `2 passed`
- qualitative-context bootstrap lane: `2 passed`
- broader memory/context recheck: `58 passed`
- shared ticker-inference consolidation lane: `59 passed`

Operational note:

- `graphify update .` was attempted after code changes but could not run in this shell because `graphify` is not installed (`command not found`)

## Problem Statement

The current Tenn memory stack has four reproduced correctness failures that affect chat continuity and qualitative retrieval accuracy:

1. Production chat paths only use semantic session recall, so continuity drops when OpenViking returns no indexed hits.
2. `query_orchestrator.resolve()` can treat ordinary words as tickers and route retrieval against fake entities.
3. `MarketMemoryStore.retrieve()` cannot recover sector memory from tickerless sector prompts even when matching sector state exists.
4. `SessionMemoryClient` config selection is effectively process-global, so backend and Cockpit clients can interfere when they run in the same process.

These failures are independent of financial-truth storage, but they degrade user-facing analysis quality and can produce misleading retrieval inputs.

## Chosen Approach And Rationale

Chosen approach: `Critical stabilization`

This wave fixes only the four reproduced correctness failures above. It does not attempt broader memory-layer consolidation or quality-of-life cleanup. The goal is to restore correctness on the current architecture with the smallest safe change set.

Rationale:

- The defects are proven with current code and runtime probes.
- The fixes are local to existing contracts and do not require schema or storage-format changes.
- This approach minimizes risk to the contract that qualitative memory is contextual only and financial numbers remain sourced from canonical backend truth.

## Architecture Overview

This change touches two existing boundaries only:

- `Session continuity boundary`
  - Session recall remains OpenViking-backed.
  - The fix adds a shared read helper that falls back to recent turns only when semantic recall is empty or unusable.
- `Qualitative retrieval boundary`
  - Orchestrator entity resolution remains the entry point for company/market memory reads.
  - Market-memory retrieval remains rank-based over existing stored state.
  - The fix tightens entity resolution and aligns sector inference between write-time routing and read-time retrieval.

Nothing in this design changes:

- financial extraction
- authoritative financial reads
- database schema
- Qdrant behavior
- company/market memory storage format

## Contract And Safety Constraints

Target layer:

- backend session memory client
- backend query orchestration
- backend market-memory retrieval
- cockpit/backend chat callers that read session context

Relevant contract rules:

- Backend remains the sole authority for authoritative retrieval and data correctness.
- Cockpit remains a client/orchestration layer and must not introduce alternate retrieval pipelines.
- Financial numbers must continue to come from canonical financial truth, not qualitative memory.

Must not change:

- no new memory store
- no shadow retrieval path
- no change to canonical financial data sources
- no broad redesign of older local memory layers in this wave

Why this design is safe:

- Each fix is a correction inside an existing component boundary.
- The session fallback only activates when semantic recall is empty.
- The ticker fix removes false positives rather than widening routing scope.
- The sector fix reuses existing classification semantics rather than inventing a new taxonomy.
- The OpenViking fix isolates client configuration without changing external configuration shape.

## Component Design

### 1. Shared Session Context Fallback

Files:

- `financial-engine_v2/shared/session_memory_base.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/cockpit/core/chat.py`

Design:

- Add a shared read helper on `SessionMemoryClient` that:
  - calls `get_relevant_session_context(...)`
  - returns those semantic results when non-empty
  - otherwise falls back to `get_recent_turns(...)`
- Keep the output shape compatible with existing chat prompt construction.
- Update production call sites to use the new shared helper instead of calling semantic recall directly.

Inputs:

- `session_id: str`
- `query: str`
- semantic `limit`
- recent-turn `limit`

Outputs:

- list of session-context items in the same caller-consumable string format used today

Non-goals:

- no change to write-time turn persistence
- no change to OpenViking ranking behavior

### 2. Strict Orchestrator Ticker Resolution

Files:

- `financial-engine_v2/backend/app/services/query_orchestrator.py`

Design:

- Tighten `resolve(query, context=None)` so it stops accepting arbitrary 2-5 letter words as tickers.
- Preserve explicit valid ticker extraction and prior-context ticker reuse.
- Reject plain-language tokens that only match the current regex shape.

Inputs:

- raw user query
- optional context containing prior ticker state

Outputs:

- unchanged entity payload shape:
  - `primary_ticker`
  - `tickers`

Non-goals:

- no repo-wide ticker-detector consolidation in this wave
- no change to intent classification categories

### 3. Shared Sector Inference For Retrieval

Files:

- `financial-engine_v2/backend/app/services/market_sector_inference.py`
- `financial-engine_v2/backend/app/services/memory_signal_router.py`
- `financial-engine_v2/backend/app/services/market_memory.py`

Design:

- Extract the sector-keyword inference logic currently used by signal routing into a shared helper.
- Place that helper in a neutral module so retrieval and routing can both import it without creating a cycle.
- Reuse that helper in market-memory retrieval when no ticker is available.
- Keep current ranking and item-selection logic unchanged once a sector is resolved.

Inputs:

- prompt text
- entities payload

Outputs:

- same `MarketMemoryStore.retrieve(...)` response shape as today
- improved `sector` resolution for tickerless sector prompts

Non-goals:

- no change to stored market-memory rows
- no change to sector ranking heuristics after sector resolution

### 4. Per-Client OpenViking Config Isolation

Files:

- `financial-engine_v2/shared/session_memory_base.py`

Design:

- Remove reliance on a long-lived process-global `OPENVIKING_CONFIG_FILE` default inside client initialization.
- Each `SessionMemoryClient` must initialize against its own resolved config path.
- If OpenViking still requires the env var during initialize-time, set it only for the duration of that initialization and restore the previous env value immediately after.

Inputs:

- resolved client config path

Outputs:

- same public session-memory client behavior
- isolated client initialization semantics

Non-goals:

- no change to external config file layout
- no launcher/profile redesign in this wave unless required by tests

## Data Contracts

Contracts intentionally preserved:

- `resolve(...)` keeps returning the current entity dictionary shape.
- `MarketMemoryStore.retrieve(...)` keeps returning the current market-memory payload shape.
- Chat call sites continue receiving string-ready prior context.
- Session persistence payloads written after chat responses remain unchanged.

New helper contract:

- `SessionMemoryClient` gains one shared read helper that returns semantically relevant context when available, otherwise recent turns.
- Callers treat this helper as the sole session-context read surface for chat continuity.

## Failure Taxonomy

| Failure Mode | Current Behavior | Desired Behavior | Detection |
| --- | --- | --- | --- |
| Empty semantic session recall | No prior context injected | Recent turns injected | unit + integration tests |
| False ticker extraction | bogus symbols like `GOING`, `SAY`, `IS` | no ticker unless explicit/validated | unit tests + probe |
| Tickerless sector prompt | no matching sector memory returned | sector inferred from prompt keywords | unit tests + probe |
| Multi-client OpenViking init | second client inherits first config | each client uses its own config | unit test |

## Validation Gates

1. Session recall uses semantic hits when they exist and recent-turn fallback only when semantic recall is empty or unusable.
2. Orchestrator resolution no longer produces false ticker symbols from normal language prompts.
3. Market-memory retrieval can return stored sector context for tickerless sector prompts.
4. Backend and Cockpit session-memory clients can initialize independently in one process without config bleed.
5. No regression to source-boundary rules: qualitative memory remains contextual only.

Status:

- Gate 1 passed
- Gate 2 passed
- Gate 3 passed
- Gate 4 passed
- Gate 5 passed

## Eval Harness

Primary automated validation:

```bash
/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest \
  financial-engine_v2/backend/tests/test_session_memory_base.py \
  financial-engine_v2/backend/tests/test_query_orchestrator.py \
  financial-engine_v2/backend/tests/test_market_memory.py \
  financial-engine_v2/backend/tests/test_memory_signal_router.py \
  financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py -q
```

Manual probe reruns after implementation:

- re-run the ticker-resolution probe that previously produced `GOING`, `SAY`, and `IS`
- re-run the tickerless sector retrieval probe for “iron ore sector”
- re-run the dual-client OpenViking init probe

## Test Suite Impact

New or updated:

- `financial-engine_v2/backend/tests/test_session_memory_base.py`
- `financial-engine_v2/backend/tests/test_query_orchestrator.py`
- `financial-engine_v2/backend/tests/test_market_memory.py`
- one production-call-site integration test in backend or cockpit chat if needed

Unchanged by design:

- company-memory tests
- financial extraction tests
- database schema tests

## Files Changed

| File | Status | Purpose |
| --- | --- | --- |
| `financial-engine_v2/shared/session_memory_base.py` | modified | add shared session fallback helper and isolate client config initialization |
| `financial-engine_v2/backend/app/services/tenn_chat.py` | modified | switch chat session-context reads to shared helper |
| `financial-engine_v2/backend/app/routes/chat.py` | modified | switch coherence/session lookup to shared helper |
| `financial-engine_v2/cockpit/core/chat.py` | modified | switch cockpit session-context reads to shared helper |
| `financial-engine_v2/backend/app/services/query_orchestrator.py` | modified | tighten ticker resolution |
| `financial-engine_v2/backend/app/services/market_sector_inference.py` | new | shared sector keyword inference used by routing and retrieval |
| `financial-engine_v2/backend/app/services/memory_signal_router.py` | modified | expose shared sector inference helper |
| `financial-engine_v2/backend/app/services/market_memory.py` | modified | use shared sector inference in retrieval |
| `financial-engine_v2/backend/tests/test_session_memory_base.py` | modified | add fallback and config-isolation coverage |
| `financial-engine_v2/backend/tests/test_query_orchestrator.py` | modified | add false-ticker regressions |
| `financial-engine_v2/backend/tests/test_market_memory.py` | modified | add tickerless-sector retrieval regression |
| `financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py` or backend chat integration test | modified | verify one production path gets fallback context |
| `financial-engine_v2/backend/app/services/company_memory.py` | unchanged | explicitly out of this wave |
| `financial-engine_v2/backend/app/api/context.py` | unchanged | dump-surface improvements deferred |
| `financial-engine_v2/cockpit/storage/state.py` | unchanged | filestats/watchlist-history fix deferred |

## Out Of Scope

- filestats/watchlist-history thread mismatch
- `/api/context/company_dump` dump-surface accuracy changes
- SQLite WAL/busy-timeout hardening for qualitative memory stores
- qualitative-context config cleanup
- repo-wide ticker/sector inference consolidation
- any schema migration

## Implementation Order

1. Modify `SessionMemoryClient` to support fallback reads and isolated initialization.
2. Update all production session-context call sites to use the shared helper.
3. Tighten orchestrator ticker resolution.
4. Reuse shared sector inference in market-memory retrieval.
5. Add regressions and rerun the focused suite plus manual probes.
