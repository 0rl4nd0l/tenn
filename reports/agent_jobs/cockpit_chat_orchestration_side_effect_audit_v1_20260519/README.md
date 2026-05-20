# Cockpit Chat Orchestration Side-Effect Audit

Job: `cockpit_chat_orchestration_side_effect_audit_v1_20260519`
Mode: `audit_only`
Worktree: `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

## Confirmed Facts

- Preflight resolved the live runtime symlink to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Current branch is `migration/clean-runtime-baseline-reconstruct-v1`; HEAD is `2e73de32ac77` with subject `milestone(evaluation): checkpoint nvme runtime audit artifacts`.
- Preflight `git status --short` showed only this audit task card as new: `?? docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md`.
- Task card validation passed with `ok: true` and no issues.
- Registry `list-active` was initially empty; `check-overlap` returned `ok: true`; this job was claimed safely.
- Runtime health/config checks were read-only and passed:
  - `GET http://127.0.0.1:8000/api/health` returned `{"status":"ok"}`.
  - `/api/cockpit/config` reports active `llm_model: model:qwen3.5-35b-a3b-apex`, `llm_endpoint: http://127.0.0.1:8001`, `runtime_target: local`, `runtime_target_source: operator_preference`, `routing_policy: api_preferred`, web/RAG enabled, DB diagnostics disabled.
  - `/api/cockpit/models` reports `model:qwen3.5-35b-a3b-apex` available and active, with the local runtime target healthy at `http://127.0.0.1:8001`.
  - `GET http://127.0.0.1:8001/v1/models` returned the loaded APEX model.
- The optional Cockpit chat smoke was not run. Current code shows that `/api/cockpit/chat` persists chat messages, updates delivered assistant metadata, can write session memory/entity observations, and can create persistent auto-diagnostic report artifacts. That crosses the task hard stop for a route smoke that would mutate data or diagnostics.

## Inferred Facts

- The prior direct `:8001` APEX/M40 stability result remains valid for the direct runtime layer. This audit found the behavioral difference in the Cockpit application route, not in llama.cpp model serving.
- A tiny direct local request and a tiny Cockpit route request are not equivalent. The Cockpit route wraps the prompt in system instructions, structured agent protocol, session context, routing metadata, source visibility enforcement, persistence, and auto-diagnostics.
- For a generic control prompt like `Reply exactly: ok`, the route-level visible-source contract can treat the request as requiring visible sources because the route small-talk/non-substantive regex does not match that phrasing.
- The separate larger llama.cpp request observed in prior logs is consistent with Cockpit auto-diagnostic bundle analysis, not with the direct answer request.

## Speculative Claims

- The previously observed core Cockpit request around 542 prompt tokens was likely the structured agent/system envelope for the user request, not retrieval or GPU instability. This is inferred from the code path and prior log shape, not from a fresh Cockpit smoke.
- The previously observed side-effect request around 976 tokens was likely `_analyze_flagged_bundle()` reviewing an auto-diagnostic flag bundle. The exact token count was not reproduced because the audit intentionally avoided running a mutating route smoke.

## DATA_MISSING

- No fresh `/api/cockpit/chat` response body, elapsed time, route-selected model, or before/after llama.cpp token delta was captured because the route smoke would mutate persistent chat/diagnostic state.
- No fresh proof was gathered that the currently live route would still trigger auto-flagging for `Reply exactly: ok`; code inspection shows the path and trigger, but the one-shot runtime confirmation was skipped by boundary.
- The exact owner of any prior canceled side-effect request cannot be proven from current logs alone without replaying the route or inspecting persistent flagged report artifacts outside this audit's data-access scope.

## Direct Runtime Baseline

Direct local APEX is not the owner of this issue unless new evidence appears. The direct llama.cpp API at `:8001` accepts the prompt through `cockpit/core/integrations/llamacpp_client.py::LlamaCppClient.chat()`, which posts to `/v1/chat/completions` with the supplied prompt and optional prior messages. It does not apply Cockpit source visibility enforcement, does not persist chat state, and does not run auto-flag diagnostics.

The established `APEX_M40_DIRECT_STABLE` baseline therefore remains meaningful: it proves the direct model serving layer can answer tiny local prompts. It does not prove that `/api/cockpit/chat` will deliver that raw model text to the UI.

## Live Route Map

`POST /api/cockpit/chat` is handled in `financial-engine_v2/backend/app/routes/cockpit_api.py`.

1. `CockpitChatRequest` accepts `message`, `mode`, `ticker`, `session_id`, `stream`, `model`, `web_search`, `rag`, `db_diagnostics`, `attached_sources`, and `runtime_target`.
2. The route calls `CockpitService.get_instance()`.
3. For non-streaming requests, the route runs `CockpitService.chat_stream()` in a worker thread and consumes its chunks into a `ChatResponse`.
4. `CockpitService.chat_stream()` builds the chat controller, resolves local/API routing, persists the user message, calls `ChatController.build_chat_response()`, merges routing metadata, persists the assistant response, and remembers recent turn diagnostics.
5. Back in the route, `_enforce_visible_source_contract()` can replace the model text with the source-contract refusal and set `routing_metadata["grounding_guard"] = "missing_visible_sources"`.
6. `_build_chat_ui_metadata()` derives UI metadata, including evidence labels and `source_coverage_status`.
7. `_finalize_delivered_chat_response()` updates the persisted latest assistant message with the delivered text and metadata.
8. `_maybe_auto_flag_chat_response()` can call `CockpitService.auto_flag_chat_response()`.
9. If findings exist, `flag_chat_feedback(... capture_kind="auto_diagnostic")` writes a flagged-session report bundle and schedules background LLM analysis.

The legacy `financial-engine_v2/backend/app/routes/chat.py` `/chat` route is a separate route and is not the owner of `/api/cockpit/chat`.

## Component Map

### 1. `POST /api/cockpit/chat` owner

- Route: `financial-engine_v2/backend/app/routes/cockpit_api.py::cockpit_chat`
- Service: `financial-engine_v2/backend/app/services/cockpit_service.py::CockpitService.chat_stream`
- Core controller: `financial-engine_v2/cockpit/core/chat.py::ChatController.build_chat_response`
- Structured agent path: `financial-engine_v2/cockpit/core/chat.py::_run_agent_loop` and `financial-engine_v2/cockpit/core/agent_loop.py::AgentLoop`
- Local model transport: `financial-engine_v2/cockpit/integrations/llamacpp_client.py::LlamaCppClient.chat`

### 2. Prompt builder sent to local APEX

The actual local request is assembled by `AgentLoop._call_llm()`, routed through `HybridRouter._call_local()`, and posted by `LlamaCppClient.chat()`. The prompt includes all prior messages passed by the agent loop, not just the raw user text.

For the structured path, `AgentLoop._run_inner()` builds:

- system prompt from `ChatController._build_system_instruction()`
- structured JSON/tool-output instructions
- optional prior conversation history
- optional current ticker context
- final user message

For the legacy keyword path, `ChatController.build_chat_response()` builds a system instruction, optional OpenViking/session history, local context evidence sections, and then calls the local LLM completion helper.

### 3. System/context/source instruction injection

- `ChatController._build_system_instruction()` injects ASX domain scope, current date, financial truth requirements, source visibility requirements, and no-fabrication rules.
- `AgentLoop` adds structured output instructions requiring JSON responses, tool calls, and current-turn evidence for substantive factual answers.
- `_run_agent_loop()` can prepend OpenViking prior session context, strategy context, attached-source context, request-standard guidance, and prior research memory.
- The legacy keyword path can inject local context payloads from `ToolRouter.gather_local_context()`, recent conversation history, and evidence/source sections before final LLM completion.

### 4. Retrieval/diagnostic flags

Flags are accepted by the frontend and backend:

- Frontend defaults live in `cockpit-ui/lib/cockpit-store.ts`: web on, RAG on, DB diagnostics off, runtime target local, default model APEX.
- Frontend sends `web_search`, `rag`, `db_diagnostics`, and `stream` in `cockpit-ui/lib/api-client.ts`.
- Backend request fields are defined in `CockpitChatRequest`.
- `CockpitService.chat_stream()` passes them into `ChatController.build_chat_response()`.

They are not currently a single global side-effect disable:

- `web_search=false` blocks explicit web-search shortcuts and legacy automatic web enrichment. Structured `AgentLoop` web tool availability still depends on `ToolRouter.web_default_enabled`, which is global controller state, not the per-request flag.
- `rag=false` gates the deep-analysis "RAG required" check, but `QueryOrchestrator.orchestrate_query_with_context()` is called before the structured agent path without per-request RAG flags, and `ToolRouter.gather_local_context()` has no per-request `enable_rag` argument.
- `db_diagnostics=false` is passed through request metadata, but the observed code path for DB diagnostics is primarily controller/tool-router state toggled by `/dbdiag on|off`; this flag does not prevent auto-flag diagnostics.
- These flags do not disable route-level source guarding, response delivery finalization, turn diagnostics, or auto-flag reporting.

### 5. Visible-source guard owner

`financial-engine_v2/backend/app/routes/cockpit_api.py::_enforce_visible_source_contract()` owns `grounding_guard: missing_visible_sources`.

The function:

- builds UI-visible sources from response evidence
- skips guard for allowed operational/tool acknowledgements, marketplace UI, holdings answers, non-substantive messages, and certain safe response classifications
- allows explicit unverified refusals without financial claims
- otherwise replaces `response.text` with `_SOURCE_CONTRACT_REFUSAL`
- sets `routing_metadata["grounding_guard"] = "missing_visible_sources"`
- returns no UI sources

### 6. Why route can refuse instead of returning `ok`

The model may produce `ok`, but the route is allowed to replace it after model completion. `Reply exactly: ok` is not matched by the current non-substantive route regex, so the route can classify it as requiring visible sources. If the response has no UI-visible sources and is not classified as a safe clarification/planning/system-failure response, `_enforce_visible_source_contract()` replaces the delivered text with the visible-source refusal.

This is route output replacement, not a provider/runtime error.

### 7. `source_coverage_status: missing_required_evidence` owner

There are two owners depending on path:

- Route-level source guard path: `_response_evidence_labels()` adds `missing_required_evidence` when routing metadata contains `grounding_guard`, and `_source_coverage_status()` returns `missing_required_evidence`.
- Query orchestration path: `backend/app/services/query_orchestrator.py::build_evidence_envelope()` also sets `missing_required_evidence` when required source categories are absent or analysis is insufficient.

For the prior local-source visible-source refusal, the route-level guard is the direct owner of the final UI `source_coverage_status`.

### 8. Auto-diagnostic side-effect owner

The route calls `_maybe_auto_flag_chat_response()` after delivery finalization. That calls `CockpitService.auto_flag_chat_response()`, which:

- reconstructs the latest turn diagnostics
- runs `detect_auto_flag_findings()`
- flags `grounding_guard == "missing_visible_sources"` as category `missing_sources`
- deduplicates by fingerprint
- calls `flag_chat_feedback(... capture_kind="auto_diagnostic")`

`flag_chat_feedback()` writes a bundle under `reports/cockpit/flagged_sessions/...` and schedules `_analyze_flagged_bundle()`. `_analyze_flagged_bundle()` builds a review prompt over the flagged turn bundle and calls the LLM. That is the likely owner of the separate larger/canceled side-effect request seen in llama.cpp logs.

### 9. Side-effect classification

- Source guard: expected product safety behavior for substantive/source-dependent answers.
- Refusal for `Reply exactly: ok`: overzealous guard / route smoke mismatch.
- Auto-diagnostic report creation and second LLM analysis after a generic control prompt: operator diagnostic behavior, but bug-like/noisy when triggered by source-free smoke/control prompts.
- Test-only leak: not indicated. The auto-flagger has direct backend tests and is wired into the live route.
- DATA_MISSING: exact prior side-effect report id and full prior request body were not inspected.

### 10. Prompt/token amplification

The core prompt is amplified mostly by necessary Cockpit orchestration envelope:

- system instruction and source safety rules
- structured JSON/tool protocol
- session/history/request-standard context
- optional ticker/context injection
- routing metadata and evidence scaffolding

Source guard instructions contribute to prompt size, but the final visible-source guard itself is a post-model route enforcement step.

The separate auto-diagnostic prompt is diagnostic feedback/reporting, not the user-answer prompt. It serializes a flagged-turn bundle into a JSON-review instruction and calls the LLM again.

### 11. Scope of impact

This is easiest to reproduce on source-free meta/control prompts because they intentionally produce no visible evidence. It can also affect normal financial queries whenever the route delivers a substantive answer without UI-visible sources. For normal financial queries, that is intended safety behavior. The bug-like part is the generic-control prompt mismatch and the auto-diagnostic noise that follows it.

### 12. Smallest safe next step

Add tests first, then apply a narrow safe-extension patch only if the tests prove the intended behavior.

The patch should not weaken financial evidence/source safety. It should narrow only source-free control/meta prompt handling and/or auto-flag gating so route smoke prompts do not trigger visible-source refusal or diagnostic report generation.

## Classification

### Direct Runtime

- Expected stable.
- Not owner of issue unless new runtime/provider evidence appears.

### Cockpit Route

- Prompt envelope: owned by `ChatController._build_system_instruction()`, `AgentLoop._run_inner()`, and legacy keyword prompt assembly in `ChatController.build_chat_response()`.
- Source guard: owned by route function `_enforce_visible_source_contract()`.
- Retrieval flags: accepted by frontend/API/service/controller, but not a global disable for all orchestration/context paths.
- Diagnostic side effects: owned by `_maybe_auto_flag_chat_response()`, `CockpitService.auto_flag_chat_response()`, `detect_auto_flag_findings()`, and `flag_chat_feedback()`.
- Output replacement: owned by `_enforce_visible_source_contract()`.
- Route metadata: merged in `CockpitService.chat_stream()` and finalized by `_build_chat_ui_metadata()`.
- Owner files/functions:
  - `financial-engine_v2/backend/app/routes/cockpit_api.py::cockpit_chat`
  - `financial-engine_v2/backend/app/routes/cockpit_api.py::_enforce_visible_source_contract`
  - `financial-engine_v2/backend/app/routes/cockpit_api.py::_build_chat_ui_metadata`
  - `financial-engine_v2/backend/app/routes/cockpit_api.py::_maybe_auto_flag_chat_response`
  - `financial-engine_v2/backend/app/services/cockpit_service.py::CockpitService.chat_stream`
  - `financial-engine_v2/backend/app/services/cockpit_service.py::CockpitService.auto_flag_chat_response`
  - `financial-engine_v2/backend/app/services/cockpit_service.py::CockpitService.flag_chat_feedback`
  - `financial-engine_v2/backend/app/services/cockpit_auto_flagger.py::detect_auto_flag_findings`
  - `financial-engine_v2/cockpit/core/chat.py::ChatController.build_chat_response`
  - `financial-engine_v2/cockpit/core/agent_loop.py::AgentLoop`
  - `financial-engine_v2/cockpit/integrations/llamacpp_client.py::LlamaCppClient.chat`

### User-Visible Behavior

- Correct safety behavior: refusing substantive factual claims without visible sources.
- Overzealous guard: generic route smoke/control prompts like `Reply exactly: ok`.
- Route smoke mismatch: direct APEX returns raw model text; Cockpit route delivers post-processed safety output.
- Debug side-effect leak: auto-diagnostic flagging/reporting can fire after route smoke/control prompt refusal.
- DATA_MISSING: no fresh route smoke because it would persist data/diagnostics.

## Recommended Follow-Up Safe Extension

Proposed next task: `cockpit_chat_control_prompt_guard_tests_v1`.

Goal: add tests that lock down control/meta prompt behavior before any implementation change.

Proposed allowed files:

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_auto_flagger.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py`
- optional only if flag semantics require core routing changes: `financial-engine_v2/cockpit/core/chat.py`

Tests to add before any patch:

- A route/source-contract unit test showing `Reply exactly: ok` with response text `ok` and no evidence is treated as non-substantive/control output and is not replaced by `missing_visible_sources`.
- A regression test showing a substantive financial claim without visible sources is still replaced by the source-contract refusal.
- An auto-flagger test showing `missing_visible_sources` still flags substantive/source-dependent turns.
- An auto-flagger or route-level test showing generic/control prompt smoke does not create `auto_diagnostic` output.
- A flag-semantics test documenting current `web_search=false`, `rag=false`, and `db_diagnostics=false` behavior, or asserting the intended no-retrieval behavior if the product wants those flags to be hard disables.

## Validation Commands Run

Preflight:

- `pwd` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `readlink -f /home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `git branch --show-current` -> `migration/clean-runtime-baseline-reconstruct-v1`
- `git rev-parse --short=12 HEAD` -> `2e73de32ac77`
- `git status --short` -> only the audit task card was untracked at preflight
- `git worktree list` -> current runtime worktree is `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1 2e73de32 [migration/clean-runtime-baseline-reconstruct-v1]`
- `git show --stat --oneline --no-renames HEAD` -> `2e73de32 milestone(evaluation): checkpoint nvme runtime audit artifacts`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md` -> `ok: true`

Registry:

- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime` -> initially empty
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md --repo-root /home/l4nd0/tenn-runtime` -> `ok: true`, no issues
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md --repo-root /home/l4nd0/tenn-runtime` -> `ok: true`

Runtime/API:

- `curl -fsS http://127.0.0.1:8000/api/health`
- `curl -sS http://127.0.0.1:8000/api/cockpit/config | python3 -m json.tool | head -120`
- `curl -sS http://127.0.0.1:8000/api/cockpit/models | python3 -m json.tool | head -120`
- `curl -sS http://127.0.0.1:8001/v1/models | head -120`

Read-only inspection used `rg`, `nl`, and `sed` on the files listed in the task card and adjacent owner modules.

## Final Git Status

- `git status --short` -> `?? docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md`
- `git status --short --ignored=matching reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519 docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md` -> task card untracked, report directory ignored as expected.
- Report artifacts present:
  - `reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/README.md`
  - `reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/status.json`
  - `reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/diff-check.json`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md` -> `ok: true`, no disallowed files.
- The task card includes repo-local `allow_audit_code_changes: true` so audit-only task/report artifacts validate under `check-diff`.

## Registry Release Status

- `python3 scripts/agent_job_registry.py release cockpit_chat_orchestration_side_effect_audit_v1_20260519 --repo-root /home/l4nd0/tenn-runtime` -> `ok: true`.
- Post-release `list-active` -> `active_jobs: []`.

## Project Memory Save Recommendation

Save this only if the user explicitly asks to update memory: Cockpit chat source refusal and auto-diagnostic side effects are route orchestration behavior, not direct APEX/M40 instability. Optional route smoke mutates chat state and can write auto-diagnostic artifacts, so future audits should prefer unit-level tests or an explicitly approved isolated runtime/data lane.
