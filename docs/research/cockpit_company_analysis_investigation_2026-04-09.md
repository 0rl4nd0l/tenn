# Cockpit Company Analysis Investigation

## 1. Executive Answer
- On committed `cloud/session-20260319` (`HEAD` at `9b7773c`), the browser path is `cockpit-ui` -> `/api/cockpit/chat` -> `backend/app/routes/cockpit_api.py` -> `CockpitService.chat_stream()` -> `ChatController.build_chat_response()`; inside `ChatController`, the structured `AgentLoop` is the primary committed company-analysis path. `cockpit-ui/components/cockpit/chat/chat-screen.tsx:262-314`, `cockpit-ui/lib/api-client.ts:103-125,165-193`, `cockpit-ui/next.config.mjs:16-30`, `HEAD financial-engine_v2/backend/app/routes/cockpit_api.py:802-811,1223-1290`, `HEAD financial-engine_v2/backend/app/services/cockpit_service.py:475-526`, `HEAD financial-engine_v2/cockpit/core/chat.py:182-200,389-412,2816-3035`
- The committed cloud/session branch still has a separate direct Textual path that bypasses the backend Cockpit service entirely and calls `ChatController.build_chat_response()` in-process. `HEAD financial-engine_v2/cockpit/ui/app.py:1391-1414`
- `QueryOrchestrator` is not committed on either `main` or committed `cloud/session-20260319`. The file has no committed history and is only present as an untracked local file in the dirty worktree. `git log --all -- financial-engine_v2/backend/app/services/query_orchestrator.py` returned no commits; `git ls-tree` for `HEAD` and `main` returned no such file
- Committed cloud/session does contain a dormant `_query_orchestrator` injection seam and callsite in `ChatController`, but `CockpitService` does not construct or pass one in committed code, so it is not runtime-active there. `HEAD financial-engine_v2/cockpit/core/chat.py:175,2703-2755,3002-3033`, `HEAD financial-engine_v2/backend/app/services/cockpit_service.py:228-235,244-252,475-526`
- The committed cloud/session agent loop is primary, but the legacy/local-context path is still active as fallback/alternate logic inside `ChatController.build_chat_response()`. It uses `ToolRouter.gather_local_context()` and direct LLM prompting, not the orchestrator. `HEAD financial-engine_v2/cockpit/core/chat.py:2999-3035`; current `financial-engine_v2/cockpit/core/tools.py:1356-1652`
- On `main` (`3c700c7` locally), there is no committed browser `cockpit-ui`, no committed `backend/app/routes/cockpit_api.py`, no committed `CockpitService`, and no committed `AgentLoop`. The main Cockpit company-analysis path is the Textual UI calling `ChatController.build_chat_response()` directly with a local-context JSON prompt path. `git diff --name-status main..HEAD`, `main financial-engine_v2/cockpit/ui/app.py:2055-2062`, `main financial-engine_v2/cockpit/core/chat.py:2545-3240`
- The browser/UI `mode` field is hardcoded to `"analysis"` in `cockpit-ui`, but on `/api/cockpit/chat` it is not used for routing analysis vs strategy. The backend route accepts `mode` then ignores it when calling `service.chat_stream()`. `cockpit-ui/components/cockpit/chat/chat-screen.tsx:264,307`, `cockpit-ui/lib/api-client.ts:118,185`, `HEAD financial-engine_v2/backend/app/routes/cockpit_api.py:802-811,1226-1234,1280-1289`
- A separate backend `/chat` route still exists and does use `mode` to split `analysis` vs `strategy`, but that is not the current Cockpit browser path. It is a parallel legacy/retrieval-first path. `financial-engine_v2/backend/app/routes/chat.py:27-33,57-69,151-164`
- In the dirty local worktree, the architecture is materially different: `QueryOrchestrator`, `company_memory`, `market_memory`, `memory_signal_router`, and `provenance` are added locally; `CockpitService` now instantiates the orchestrator; `ChatController` can route general company questions through it before agent-loop fallback; and a deterministic `company_dump` / `filestats` path is added. `financial-engine_v2/backend/app/services/query_orchestrator.py:625-696`, `financial-engine_v2/backend/app/services/cockpit_service.py:15,374-378,431-440,551-563`, `financial-engine_v2/cockpit/core/chat.py:2682-2825,3866-3897`
- Company memory and market memory are not part of the committed runtime on `main` or committed cloud/session. They become part of the visible local/WIP runtime only. `HEAD` has no committed `company_memory.py` or `market_memory.py`; working tree adds `financial-engine_v2/backend/app/services/company_memory.py` and `market_memory.py`
- Provenance formatting is not applied before answer synthesis in the committed runtime. The committed source footer is display-only in the Textual UI after the response, and the dirty `provenance.py` module is not wired into Cockpit company-analysis runtime. `financial-engine_v2/cockpit/core/sources.py:1-5`, `financial-engine_v2/cockpit/ui/app.py:1803-1812`, `financial-engine_v2/backend/app/services/provenance.py:216-287`
- Collision risk is high in the dirty worktree because three overlapping formulations now coexist: committed structured agent-loop, committed/local-context fallback, and local-only orchestrator/company-memory/company-dump additions.

## 2. Lane Classification
- lane: Query Orchestration
- collision risk: High
- execution mode: Read-only architecture audit across `main`, committed `cloud/session-20260319`, and visible dirty local state

## 3. Current-State Matrix

| State | browser UI path present? | backend cockpit route present? | orchestrator file committed? | orchestrator wired? | agent loop primary? | local-context path present? | company memory active? | market memory active? | provenance active? | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `main` | No | No | No | No | No | Yes | No | No | No | Local `main` is `3c700c7`, ahead of `origin/main` by one lane file (`backend/app/api/context.py`); Cockpit is Textual-only here |
| `cloud/session-20260319 (committed)` | Yes | Yes | No | No | Yes | Yes | No | No | Footer only | `HEAD` is `9b7773c`; browser path exists, but Textual bypass path also remains live |
| `local / in-flight / dirty state` | Yes | Yes | Visible only as untracked local files | Yes, in code | Partial: orchestrator now runs before agent-loop fallback | Yes | Yes, if store exists | Yes, if store exists | No runtime use | Untracked `query_orchestrator.py`, `company_memory.py`, `market_memory.py`, `memory_signal_router.py`, `provenance.py`; high overlap with committed paths |

## 4. Runtime Path - Browser / API
1. Browser chat entrypoint is `ChatScreen.handleSend()`, which calls `sendChatMessage()` for slash commands and `streamChat()` for normal chat, always with `mode: 'analysis'`. `cockpit-ui/components/cockpit/chat/chat-screen.tsx:189-314`
2. `sendChatMessage()` and `streamChat()` both POST to `/api/cockpit/chat`. `cockpit-ui/lib/api-client.ts:103-125,165-193`
3. `cockpit-ui` does not implement `app/api/cockpit/chat/route.ts`; instead `next.config.mjs` rewrites `/api/:path*` directly to the backend, so `/api/cockpit/chat` goes straight to the FastAPI backend. `cockpit-ui/next.config.mjs:16-30`
4. The backend receiver is `cockpit_chat()` in `financial-engine_v2/backend/app/routes/cockpit_api.py`. The request model includes `message`, `mode`, `ticker`, `session_id`, `stream`, `model`, `web_search`, `rag`, and `db_diagnostics`. `HEAD financial-engine_v2/backend/app/routes/cockpit_api.py:802-811,1218-1295`
5. `cockpit_chat()` calls `service.chat_stream(...)` in both blocking and SSE modes, but it does not forward `payload.mode` anywhere. `HEAD financial-engine_v2/backend/app/routes/cockpit_api.py:1223-1234,1279-1289`
6. `CockpitService.chat_stream()` resolves the session thread, builds or reuses a `ChatController`, persists the user turn, then calls `controller.build_chat_response(...)`. `HEAD financial-engine_v2/backend/app/services/cockpit_service.py:475-549`
7. The SSE layer forwards `chunk`, `status`, `tool_trace`, `action_preview`, and final `done` events. In the working tree it also emits `chart` events for local `company_dump` evidence. `financial-engine_v2/backend/app/routes/cockpit_api.py:1656-1739`
8. The browser assembles the final assistant message only on the `done` event, combining streamed text with metadata, tool traces, sources, optional action preview, and optional chart. `cockpit-ui/components/cockpit/chat/chat-screen.tsx:381-418`

## 5. Orchestrated Path
- Status: local/in-flight only; not committed on `main` or committed cloud/session.
- File present only locally: `financial-engine_v2/backend/app/services/query_orchestrator.py:625-696`
- Exact callsite in Cockpit: `financial-engine_v2/cockpit/core/chat.py:3869-3872` in the dirty worktree. The committed cloud/session branch has the dormant call at `HEAD financial-engine_v2/cockpit/core/chat.py:3005-3008`.
- Injection vs direct call:
  - The UI and route do not call `QueryOrchestrator` directly.
  - `CockpitService` injects it into `ChatController` in the dirty worktree. `financial-engine_v2/backend/app/services/cockpit_service.py:374-378,431-440,551-563`
- Payload in:
  - `ChatController` passes `effective_message` plus `context={"prior_ticker": ticker}` in the dirty worktree. `financial-engine_v2/cockpit/core/chat.py:3869-3872`
  - `QueryOrchestrator.orchestrate_query_with_context()` classifies the query, resolves entities, retrieves evidence from providers, builds `answer`, and builds deterministic `answer_input`. `financial-engine_v2/backend/app/services/query_orchestrator.py:642-680`
- Providers:
  - `CockpitService` injects only `financial_truth_provider`, backed by `BackendApiClient.get_ticker_context(...)`. `financial-engine_v2/backend/app/services/cockpit_service.py:213-261,374-378`
  - `QueryOrchestrator` defaults `company_memory_provider` to `CompanyMemoryStore()` and `market_memory_provider` to `MarketMemoryStore()`. `financial-engine_v2/backend/app/services/query_orchestrator.py:626-637`
- Payload out:
  - `OrchestratedQueryResult` contains `query`, `intent`, `entities`, `plan`, `source_plan`, `financial_truth_results`, `company_memory_results`, `market_memory_results`, `evidence`, `raw_supporting_evidence`, `answer_input`, and `answer`. `financial-engine_v2/backend/app/services/query_orchestrator.py:235-249`
- Deterministic answer assembly before LLM:
  - `compose_answer()` only records `sources_used`, `source_status`, and `notes`. `financial-engine_v2/backend/app/services/query_orchestrator.py:394-413`
  - `build_answer_input()` builds a deterministic text scaffold from canonical financial truth, ranked company-memory items, ranked market-memory items, uncertainty notes, and the source plan. `financial-engine_v2/backend/app/services/query_orchestrator.py:416-535`
- Final answer after orchestration:
  - `ChatController._build_orchestrated_response()` wraps orchestrator output into evidence entries, then, if an agent loop exists, calls `AgentLoop.synthesize_final_answer()` or `synthesize_final_answer_stream()` with `draft_answer=orchestration_result.answer_input`; otherwise it streams the deterministic `answer_input` directly. `financial-engine_v2/cockpit/core/chat.py:3562-3667`
- Committed vs WIP:
  - Not committed: no committed history for `query_orchestrator.py`, `company_memory.py`, `market_memory.py`, `memory_signal_router.py`, or `provenance.py`.
  - Committed cloud/session only has dormant scaffolding in `ChatController`; the provider and file are missing. `HEAD financial-engine_v2/cockpit/core/chat.py:175,2703-2755,3002-3033`, `HEAD financial-engine_v2/backend/app/services/cockpit_service.py:228-235`
- Important collision:
  - On committed cloud/session, `_build_orchestrated_response()` already assumes `AgentLoop.synthesize_final_answer*()`, but committed `HEAD` `AgentLoop` has no such methods. `HEAD financial-engine_v2/cockpit/core/chat.py:2720-2755`; `git grep` on `HEAD financial-engine_v2/cockpit/core/agent_loop.py` found no `synthesize_final_answer`, `_build_synthesis_messages`, or `_finalize_result`

## 6. Structured Agent-Loop Path
- Trigger conditions on committed cloud/session:
  - Non-slash, non-short-circuit, non-action queries.
  - `COCKPIT_AGENT_MODE` defaults to `"structured"`. `HEAD financial-engine_v2/cockpit/core/chat.py:182-200,2999-3035`
- Construction:
  - `ChatController.__init__()` builds `HybridRouter`, `ToolExecutor`, and `AgentLoop` when `COCKPIT_AGENT_MODE=structured`. `HEAD financial-engine_v2/cockpit/core/chat.py:195-200,389-412`
- Runtime:
  - `_run_agent_loop()` resolves ticker context, injects prior session context and optional strategy/research context, then calls `self._agent_loop.run(...)`. `financial-engine_v2/cockpit/core/chat.py:3397-3503`
- Tool surface in committed cloud/session:
  - The committed tool set includes `query_ticker_data`, `get_price`, `get_price_on_date`, `get_price_range`, `get_financials`, `search_news`, `search_announcements`, `get_data_quality`, and `run_analysis`; it does not include committed `get_company_dump`. `HEAD financial-engine_v2/cockpit/core/tool_definitions.py:22-220`, `HEAD financial-engine_v2/cockpit/core/tool_executor.py:127-460,579-637`
- Evidence collection behavior:
  - The agent loop accumulates `{"tool", "arguments", "result"}` entries and tool traces as the model requests tools. `HEAD financial-engine_v2/cockpit/core/agent_loop.py:248-278,430-453`
- Final synthesis on committed cloud/session:
  - Committed `HEAD` agent loop does not have a separate post-pass synthesis helper. It relies on the model to emit a final `{"type":"response"}` inside the loop after tool calls. `HEAD financial-engine_v2/cockpit/core/agent_loop.py:190-219,383-453`
- Local dirty difference:
  - The dirty worktree adds `_finalize_result()`, `synthesize_final_answer*()`, `_build_synthesis_messages()`, and `_summarize_evidence()` special cases, so local dirty agent-loop answers get an extra synthesis pass after evidence collection. `financial-engine_v2/cockpit/core/agent_loop.py:194-235,632-800,957-992`
- Is this primary in committed runtime?
  - Yes on committed cloud/session.
  - No on `main` because `AgentLoop` is not committed there.
  - Not solely primary in dirty local state because the new orchestrator branch runs earlier for many general company questions. `financial-engine_v2/cockpit/core/chat.py:3866-3897`

## 7. Local-Context / Legacy Path
- Committed cloud/session fallback path:
  - `ChatController.build_chat_response()` falls through to the keyword/local-context path when the structured agent loop is disabled, skipped, or short-circuited. `HEAD financial-engine_v2/cockpit/core/chat.py:3035+`; current `financial-engine_v2/cockpit/core/chat.py:3979-4447`
- Raw context structure in committed cloud/session:
  - `ToolRouter.gather_local_context()` builds a payload with `docs`, `doc_snippets`, `financials`, `financials_narrative`, `data_quality`, `price`, `price_state`, optional `price_horizons`, merged `qual_context`, `watchlist_history`, `agent_memory`, `dossier_findings`, and `sources`. `financial-engine_v2/cockpit/core/tools.py:1356-1652`
- Prompt/evidence assembly in committed cloud/session:
  - The controller converts the payload into readable evidence sections, then calls `ollama_client.chat(user_message, prior_messages=[system])`. `financial-engine_v2/cockpit/core/chat.py:4139-4447`
- Deterministic override guards in committed cloud/session:
  - If the answer violates deep-analysis structure or missing-financials rules, it replaces the LLM answer with deterministic grounded briefs. `financial-engine_v2/cockpit/core/chat.py:4425-4540`
- `main` local-context path:
  - `main` uses the same `ChatController.build_chat_response()` entrypoint, but its formulation is different: it builds a raw JSON prompt from sanitized local payload and optional web evidence, then calls `ollama_client.chat(prompt_used, ...)`. `main financial-engine_v2/cockpit/core/chat.py:2890-3242`
  - In `main`, operational mode company analysis is deterministic via `_build_operational_analysis_brief()`; deep mode is LLM-first with deterministic fallback builders. `main financial-engine_v2/cockpit/core/chat.py:1681,2951-2969,3158-3242`
- Separate retrieval-first backend path:
  - `backend/app/routes/chat.py` -> `tenn_chat.chat_with_tenn()` is still active and is fully retrieval-first, but it is not the current Cockpit browser route. `financial-engine_v2/backend/app/routes/chat.py:57-69,151-164`, `financial-engine_v2/backend/app/services/tenn_chat.py:291-484`

## 8. Deterministic Report/Brief Paths
- `main` deterministic company-analysis brief:
  - `_build_operational_analysis_brief()` returns a deterministic operational brief without model synthesis. `main financial-engine_v2/cockpit/core/chat.py:1681`, `main financial-engine_v2/cockpit/core/chat.py:2951-2969`
- `main` deterministic deep/grounded fallback:
  - `_build_grounded_analysis_fallback()` and `_build_grounded_deep_analysis_brief()` replace bad/off-topic LLM output. `main financial-engine_v2/cockpit/core/chat.py:1205,1453,3154-3215`
- Committed cloud/session deterministic fallback only:
  - `_build_grounded_overview_brief()` and `_build_grounded_deep_analysis_brief()` are guardrails, not the primary path. `financial-engine_v2/cockpit/core/chat.py:4507-4540,4541-4589`
- Dirty local deterministic `company_dump` / `filestats` path:
  - `_build_filestats_response()` calls `backend_client.get_company_dump()`, collects cockpit-local memory, formats a deterministic text dump, and optionally writes a Plotly dashboard; no LLM is involved. `financial-engine_v2/cockpit/core/chat.py:2682-2777`
  - It is triggered by `/filestats ...` or direct `"<ticker> filestats"` phrases via `_try_filestats_shortcircuit()`. `financial-engine_v2/cockpit/core/chat.py:2779-2825`
  - The backend route then converts `company_dump` evidence into a chart event for the browser. `financial-engine_v2/backend/app/routes/cockpit_api.py:1239-1290`

## 9. Evidence Sources Used In Company Analysis
- `main` local-context path:
  - Canonical financial truth: `ToolRouter.gather_local_context()` via backend context or local DB-backed readers. `main financial-engine_v2/cockpit/core/chat.py:2890-2895`; current `financial-engine_v2/cockpit/core/tools.py:1382-1452`
  - Retrieval/docs/snippets: `docs`, `doc_snippets`, `qual_context`, optional web evidence JSON. `main financial-engine_v2/cockpit/core/chat.py:3073-3114`
  - Price/context: `price`, `price_state`, and optional web enrichment. `main financial-engine_v2/cockpit/core/chat.py:2700-2779,2990-3041`
  - Final synthesis: raw JSON prompt sent directly to `ollama_client.chat()`. `main financial-engine_v2/cockpit/core/chat.py:3073-3242`
- Committed cloud/session agent loop path:
  - Evidence comes from whichever tools the LLM calls through `ToolExecutor`: local-context payload, backend financials, announcements, news, price, data quality, analysis modules. `HEAD financial-engine_v2/cockpit/core/tool_definitions.py:22-220`, `HEAD financial-engine_v2/cockpit/core/tool_executor.py:127-460,579-637`
  - Final synthesis: inside the loop, the model responds after seeing tool results. `HEAD financial-engine_v2/cockpit/core/agent_loop.py:383-453`
- Committed cloud/session local-context fallback:
  - Canonical financial truth: backend `/api/context/ticker` via `BackendApiClient.get_ticker_context()`. `HEAD financial-engine_v2/cockpit/integrations/backend_api.py:208-251`
  - Retrieval/docs/snippets: `ToolRouter.gather_local_context()` merges docs, snippets, qual context, and local memory. `financial-engine_v2/cockpit/core/tools.py:1356-1652`
  - Final synthesis: readable evidence sections -> `ollama_client.chat(user_message, prior_messages=...)`. `financial-engine_v2/cockpit/core/chat.py:4139-4447`
- Dirty local orchestrated path:
  - Canonical financial truth: `_BackendFinancialTruthProvider.retrieve()` uses `/api/context/ticker` with limits 8/8/8. `financial-engine_v2/backend/app/services/cockpit_service.py:213-261`
  - Company memory: `CompanyMemoryStore.retrieve()` returns ranked active entries. `financial-engine_v2/backend/app/services/company_memory.py:285-306`
  - Market memory: `MarketMemoryStore.retrieve()` returns `sector_items`, `macro_items`, and combined `items`. `financial-engine_v2/backend/app/services/market_memory.py:332-359`
  - Direct prompt context: `QueryOrchestrator.build_answer_input()` deterministic scaffold. `financial-engine_v2/backend/app/services/query_orchestrator.py:416-535`
  - Final synthesis: `ChatController._build_orchestrated_response()` -> agent-loop synthesis helpers in dirty worktree. `financial-engine_v2/cockpit/core/chat.py:3562-3667`, `financial-engine_v2/cockpit/core/agent_loop.py:675-800`
- Dirty local deterministic company dump:
  - Canonical financial truth plus risk notes, 1Y price history, company memory, and market memory from `/api/context/company_dump`. `financial-engine_v2/backend/app/api/context.py:440-560`
  - Cockpit-local memory: `agent_memory`, `watchlist_history`, `dossier_findings`, `strategy_criteria`, `strategy_decision`. `financial-engine_v2/cockpit/core/chat.py:2082-2145`

## 10. Deterministic vs LLM-Composed Boundaries

| Path | Deterministic parts | LLM-composed parts |
|---|---|---|
| `main` TUI local-context | ticker detection, context assembly, web/rag gating, operational brief, fallback builders | deep analysis prompt answer via `ollama_client.chat()` |
| `cloud/session` committed agent-loop | tool schemas, tool dispatch, tool result formatting, route/status plumbing | tool selection, intermediate reasoning, final response inside `AgentLoop` |
| `cloud/session` committed local-context fallback | context assembly, evidence-section rendering, fallback builders | direct answer via `ollama_client.chat(user_message, prior_messages=...)` |
| `cloud/session` committed browser route | SSE framing and message assembly | none beyond underlying `ChatController` path |
| local dirty orchestrator | query classification, entity resolution, source plan, answer_input, company_dump formatting | final NL synthesis after orchestration, if agent-loop synthesis helpers run |
| backend `/chat` route | retrieval, context row normalization, prompt building, quality scoring | JSON answer via `generate_json()` |

## 11. Active Risks / Architectural Gaps
- Committed cloud/session has dormant orchestrator scaffolding in `ChatController`, but no committed `QueryOrchestrator` implementation or `CockpitService` wiring. `HEAD financial-engine_v2/cockpit/core/chat.py:175,2703-2755,3002-3033`, `HEAD financial-engine_v2/backend/app/services/cockpit_service.py:228-235`
- Even if someone manually injected an orchestrator into committed cloud/session, committed `AgentLoop` lacks the `synthesize_final_answer*()` helpers that `_build_orchestrated_response()` expects. `HEAD financial-engine_v2/cockpit/core/chat.py:2720-2755`; no committed `synthesize_final_answer` in `HEAD financial-engine_v2/cockpit/core/agent_loop.py`
- The Cockpit browser/backend `mode` field is effectively dead for routing; browser always sends `"analysis"`, and `/api/cockpit/chat` ignores it. `cockpit-ui/components/cockpit/chat/chat-screen.tsx:264,307`, `HEAD financial-engine_v2/backend/app/routes/cockpit_api.py:802-811,1226-1234,1280-1289`
- Direct Textual Cockpit bypasses backend Cockpit service on both `main` and committed cloud/session, so there are parallel runtime paths for “Cockpit company analysis.” `main financial-engine_v2/cockpit/ui/app.py:2055-2062`, `HEAD financial-engine_v2/cockpit/ui/app.py:1391-1414`
- Retrieval-first legacy paths are still active:
  - committed/local-context fallback uses `qual_context` and backend context
  - backend `/chat` uses `query_rag` + `HybridRetriever` + `generate_json()`. `financial-engine_v2/cockpit/core/tools.py:1005-1126,1356-1652`, `financial-engine_v2/backend/app/services/tenn_chat.py:336-410`
- Provenance/source handling is inconsistent:
  - Textual source footer is post-response display only. `financial-engine_v2/cockpit/core/sources.py:1-5`, `financial-engine_v2/cockpit/ui/app.py:1803-1812`
  - Browser `sources` events only understand `local_context.qual_context.hits`, so orchestrator/company-memory evidence would not populate browser sources cleanly. `financial-engine_v2/backend/app/routes/cockpit_api.py:1696-1714`
- Local dirty memory stores are query-wired, but their population path is also local/WIP through `memory_signal_router` and memo extractors, so a locally wired runtime may still surface empty or unavailable memory stores. `financial-engine_v2/backend/app/services/memory_signal_router.py:214-241`, `financial-engine_v2/backend/app/services/commentary_memo_extractor.py:324-332`, `financial-engine_v2/backend/app/services/news_memo_extractor.py:222-230`
- Local `main` differs from `origin/main` by one lane file (`backend/app/api/context.py`), so “main” is slightly ambiguous in this workspace. `git diff --name-status origin/main..main`

## 12. Branch / PR / Recent Work Findings
- `cloud/session-20260319` local branch is ahead of `origin/cloud/session-20260319` by 68 commits; the committed analysis path inspected here is local `HEAD` `9b7773c`.
- Local `main` is `3c700c7`, ahead of `origin/main` by one lane file (`financial-engine_v2/backend/app/api/context.py`).
- Recent lane commits on the active cloud/session branch include:
  - `abf10dc` `milestone(cockpit-routing): defer chat to API under GPU contention`
  - `8d99002` `milestone(cockpit): add /sources slash command parity and source inspection`
  - `aa7e2ae` `refactor(cockpit): update core agent loop and chat`
  - `6e37b00` `refactor(backend): update cockpit service`
  - `22c96e9` `milestone(cockpit): stabilize web chat execution and status visibility`
  - `4d3c7b8` `milestone(cockpit-ui): show GPU temps and chat execution stages`
- Recent lane history for `main` shows older cockpit context work but not the cloud/session web/backend service stack. `git log -- financial-engine_v2/cockpit/core/chat.py`, `git log -- financial-engine_v2/backend/app/api/context.py`
- Open PRs currently visible are:
  - `#25` docs-only against `main`
  - `#24` runtime hardening against `cloud/session-20260319`
- No open PR surfaced for `QueryOrchestrator`, `company_memory`, `market_memory`, or `provenance`.
- The only recent merged cockpit-related PR surfaced by `gh` was `#21` (“QA harness: make cockpit boot work in cloud”), which is infrastructure/boot oriented, not a company-analysis orchestrator rollout.

## 13. Confirmed / Inferred / Speculative

**Confirmed**
- Browser Cockpit chat uses `/api/cockpit/chat` and reaches backend via Next rewrite, not a dedicated Next route. `cockpit-ui/lib/api-client.ts:103-125,165-193`, `cockpit-ui/next.config.mjs:16-30`
- Committed cloud/session browser route ends at `cockpit_api.py -> CockpitService.chat_stream() -> ChatController.build_chat_response()`. `HEAD financial-engine_v2/backend/app/routes/cockpit_api.py:1218-1290`, `HEAD financial-engine_v2/backend/app/services/cockpit_service.py:475-526`
- Committed cloud/session `ChatController` defaults to structured agent mode and constructs `AgentLoop`. `HEAD financial-engine_v2/cockpit/core/chat.py:182-200,389-412`
- Committed cloud/session still has a live direct Textual path that bypasses backend Cockpit service. `HEAD financial-engine_v2/cockpit/ui/app.py:1391-1414`
- Committed cloud/session contains `_query_orchestrator` scaffolding but does not wire a provider. `HEAD financial-engine_v2/cockpit/core/chat.py:175,2703-2755,3002-3033`, `HEAD financial-engine_v2/backend/app/services/cockpit_service.py:228-235`
- `QueryOrchestrator` and backend company/market memory services are only visible in local dirty state.
- `main` has no committed browser `cockpit-ui`, no committed `cockpit_api.py`, no committed `CockpitService`, and no committed `AgentLoop`. `git diff --name-status main..HEAD`
- The Cockpit browser/backend `mode` field is ignored on `/api/cockpit/chat`. `HEAD financial-engine_v2/backend/app/routes/cockpit_api.py:802-811,1226-1234,1280-1289`
- The separate backend `/chat` route still uses `mode` to choose analysis vs strategy. `financial-engine_v2/backend/app/routes/chat.py:27-33,151-164`

**Inferred**
- If the current dirty worktree backend were started, general company-analysis requests would hit the new orchestrator branch first, then fall back to agent loop or local-context path based on `prefer_local_context`. `financial-engine_v2/cockpit/core/chat.py:3866-3897`
- In the dirty worktree, browser “sources” output for orchestrated answers would likely be weaker or empty because the SSE route only converts `local_context.qual_context.hits` into source events. `financial-engine_v2/backend/app/routes/cockpit_api.py:1696-1714`
- The dirty worktree is moving toward a three-source formulation model:
  - financial truth for numbers
  - company memory for meaning
  - market memory for backdrop
  This is explicit in `QueryOrchestrator.build_answer_input()`. `financial-engine_v2/backend/app/services/query_orchestrator.py:424-535`

**Speculative**
- Which transport is most used in day-to-day practice today: browser vs Textual. Code proves both exist; it does not prove operator preference.
- Whether the dirty local orchestrator/memory stack currently runs cleanly end-to-end. The code is visibly wired, but I did not execute it.
- Whether the local memory stores actually contain material content in this workspace. The query path exists, but store population is also in-flight.

## 14. File-by-File Evidence
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
  - Browser chat entrypoint.
  - `handleSend()` posts normal chat via `streamChat()` and slash commands via `sendChatMessage()`, always with `mode: 'analysis'`. `189-314`, `315-418`
- `cockpit-ui/lib/api-client.ts`
  - Browser transport client.
  - `sendChatMessage()` and `streamChat()` both target `/api/cockpit/chat`. `103-125`, `165-193`
- `cockpit-ui/next.config.mjs`
  - Next rewrite layer.
  - `/api/:path*` rewrites straight to backend `${backendUrl}/api/:path*`. `16-30`
- `cockpit-ui/app/chat/route.ts`
  - Separate legacy browser proxy to backend `/chat`.
  - Not used by current `ChatScreen`, which targets `/api/cockpit/chat`. `17-37`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - Committed browser/backend Cockpit route.
  - `CockpitChatRequest` includes `mode`, but chat execution calls omit it. `HEAD ...:802-811,1226-1234,1279-1289`
  - Current dirty adds `company_dump` chart extraction for browser responses. `1239-1290` in working tree
- `financial-engine_v2/backend/app/services/cockpit_service.py`
  - Backend wrapper around `ChatController` for browser chat.
  - Committed `HEAD` wires backend API + tool router + chat controller, but no orchestrator. `HEAD ...:228-252`
  - Current dirty imports and constructs `QueryOrchestrator`, then injects it into `ChatController`. `15`, `374-378`, `431-440`, `551-563`
  - `chat_stream()` is the immediate controller entrypoint. `911-1034`
- `financial-engine_v2/cockpit/core/chat.py`
  - Core company-analysis controller across both TUI and backend service.
  - Committed `HEAD` has dormant `_query_orchestrator` injection and committed `AgentLoop` construction. `HEAD ...:175,389-412`
  - Committed `HEAD` primary branch order is: short-circuits -> dormant orchestrator hook -> structured agent loop -> legacy keyword/local-context path. `HEAD ...:2816-3035`
  - Current dirty adds deterministic `company_dump` / `filestats` path and active orchestrator callsite. `2682-2825`, `3562-3667`, `3866-3897`, `4139-4447`, `4507-4589`
  - `main` uses a different local-context JSON prompt path. `main ...:2545-3240`
- `financial-engine_v2/cockpit/core/agent_loop.py`
  - Structured tool-calling loop.
  - Committed `HEAD` collects tool evidence and expects the LLM to return a final response inside the loop. `HEAD ...:190-320,430-453`
  - Dirty local adds post-loop synthesis helpers and richer evidence summarization. `194-235`, `632-800`, `957-992`
- `financial-engine_v2/cockpit/core/tool_definitions.py`
  - Committed agent tool surface.
  - Includes `query_ticker_data`, `get_financials`, `search_news`, `search_announcements`, `get_data_quality`, `run_analysis`; no committed `get_company_dump`. `HEAD ...:22-220`
- `financial-engine_v2/cockpit/core/tool_executor.py`
  - Executes committed agent tools.
  - `query_ticker_data` uses `gather_local_context()`. `HEAD ...:127-144`
  - `get_financials`, `search_announcements`, and `get_data_quality` call backend context endpoints. `HEAD ...:228-262,372-460`
  - Dirty local adds `get_company_dump`. `financial-engine_v2/cockpit/core/tool_executor.py:146-171,930`
- `financial-engine_v2/cockpit/core/tools.py`
  - Local-context evidence assembly.
  - `_load_ticker_context_from_backend()` pulls authoritative ticker context from backend. `228-270`
  - `gather_local_context()` builds the raw local-context payload used by keyword fallback and some agent tools. `1356-1652`
  - News retrieval still prefers backend `/rag/query` with fallback to `qual_context_news_reader` SQLite. `1005-1126`, `1205+`
- `financial-engine_v2/cockpit/integrations/backend_api.py`
  - Backend API client.
  - Committed context methods are `get_ticker_context()` and `get_verification_context()`. `HEAD ...:208-251`
  - Dirty local adds `get_company_dump()`. `267-308`
- `financial-engine_v2/backend/app/api/context.py`
  - Backend-authoritative context API.
  - Committed `HEAD` exposes only `/ticker` and `/verification`. `HEAD ...:66-208,216-296`
  - Dirty local adds `/company_dump`, plus price/company-memory/market-memory loading. `159-209`, `212-283`, `440-560`
- `financial-engine_v2/cockpit/ui/app.py`
  - Textual Cockpit UI.
  - Both `main` and committed cloud/session call `ChatController.build_chat_response()` directly in-process, bypassing backend `CockpitService`. `main ...:2055-2062`, current dirty `1665-1718`
  - Textual source/provenance footer is appended after response via `SourcesFormatter`. `1798-1830`
- `financial-engine_v2/cockpit/core/sources.py`
  - Display-only source footer formatter.
  - Explicitly not part of prompt content. `1-5`
- `financial-engine_v2/backend/app/routes/chat.py`
  - Separate backend `/chat` route.
  - Uses `mode` to choose analysis vs strategy and calls `tenn_chat.chat_with_tenn()` for analysis. `27-33`, `57-69`, `151-164`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
  - Retrieval-first backend analysis path outside current browser Cockpit route.
  - Uses `query_rag`, `HybridRetriever`, `news_chunks`, `_build_prompt()`, and `generate_json()` to compose an answer. `243-273`, `291-484`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
  - Local-only WIP orchestrator.
  - Defines `QueryPlan`, `OrchestratedQueryResult`, provider retrieval, deterministic `answer_input`, and `QueryOrchestrator.orchestrate_query_with_context()`. `226-249`, `324-369`, `372-535`, `625-696`
- `financial-engine_v2/backend/app/services/company_memory.py`
  - Local-only WIP company memory store.
  - `retrieve()` returns ranked active entries for the ticker. `12`, `285-306`
- `financial-engine_v2/backend/app/services/market_memory.py`
  - Local-only WIP market memory store.
  - `retrieve()` returns `sector_items`, `macro_items`, and merged `items`. `12`, `332-359`
- `financial-engine_v2/backend/app/services/memory_signal_router.py`
  - Local-only WIP memory population router.
  - Routes memo-derived signals into company or market memory stores; not directly called by Cockpit company-analysis query handling. `214-241`
- `financial-engine_v2/backend/app/services/provenance.py`
  - Local-only WIP provenance adapter.
  - Has orchestrator and extraction provenance normalization, but no Cockpit query runtime callsite surfaced in this audit. `216-287`
