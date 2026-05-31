# Read/Write Path Map

## Backend Reasoning Memory

| Surface | Write path | Read path | Controls |
|---|---|---|---|
| Company memory | `CompanyMemoryStore.update_company_memory`, manual add API, `memory_signal_router` | `CompanyMemoryStore.retrieve`, `MemoryAssembler`, `/api/context/memory`, `/api/context/company_dump` | financial metric signal types rejected; active-score/status filtering before answer input |
| Market memory | `MarketMemoryStore.update_market_memory`, manual add API, `memory_signal_router` | `MarketMemoryStore.retrieve`, `MemoryAssembler`, `/api/context/memory`, `/api/context/company_dump` | financial metric signal types rejected; scope is sector or macro; active-score/status filtering |
| User thesis memory | `create_proposal` -> `confirm_proposal` -> `apply_confirmed_proposal` | `UserThesisMemoryStore.retrieve`, `/api/context/thesis`, `MemoryAssembler` | apply requires confirmed proposal; entries retrieved by ticker and active status |
| Memory events | emit read/write JSONL events from assembler/store mutations | report/log inspection only | best-effort, fail-open; no schema/health gate found |

## Session and Workspace Memory

| Surface | Write path | Read path | Controls |
|---|---|---|---|
| OpenViking session memory | cockpit/backend chat records each turn when enabled | semantic or recent prior turns for chat context | optional; degrades to empty when unavailable |
| Cockpit StateStore chat history | user/assistant messages after turns | recent conversation history for prompts | startup cleanup for time-limited tables |
| StateStore preferences | `/api/cockpit/preferences` and route-alias APIs | cockpit service runtime/routing preference methods | invalid routing policies rejected; route aliases confirmation-gated |
| MemoryStore filesystem | agent memory tools and compactor | agent research/session workflows | compaction threshold, no automatic archive deletion |
| Dossier findings | research tools append JSONL findings | local context/dossier recall | keyword/substr filtering only |

## Client Surfaces

| Surface | Backend path | Client path | Assessment |
|---|---|---|---|
| Web Memory tab | `/api/context/memory*`, `/api/context/thesis*`, `/api/context/company_dump` | `cockpit-ui/app/api/cockpit/memory/*`, `memory-screen.tsx` | static fit; live parity unproven |
| Textual Memory screen | backend API client | Cockpit Textual UI | documented client-only management surface |
| Chat slash commands | backend API client methods | Cockpit chat command handling | documented add/show/raw/remove routes |
| Preferences route aliases | `/api/cockpit/preferences/route-aliases*` | cockpit preferences route/API callers | confirmation gate has backend tests |

## Source-Plan Flow

The query orchestrator plans explicit sources per intent, then calls the deterministic `MemoryAssembler`. The assembler retrieves only the planned sources, filters source-specific payloads, emits a read event, and returns both filtered and raw evidence. This is the correct architectural shape because it keeps memory source selection inspectable and avoids implicit context injection.

Evidence:

- `MemoryAssembler` provider map and source-plan loop (`financial-engine_v2/backend/app/services/memory_assembler.py:28`, `financial-engine_v2/backend/app/services/memory_assembler.py:61`).
- Query orchestrator memory sources and source plans (`financial-engine_v2/backend/app/services/query_orchestrator.py:43`, `financial-engine_v2/backend/app/services/query_orchestrator.py:405`).
- Memory management surfaces proxy through backend APIs, not direct store edits (`docs/architecture/18_cockpit_memory.md:178`).
