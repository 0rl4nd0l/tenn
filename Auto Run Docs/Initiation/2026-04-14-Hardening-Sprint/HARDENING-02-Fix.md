# Phase 02: Fix Confirmed Vulnerabilities with Regression Tests

This phase consumes the audit report produced in Phase 01 (`docs/claude/audit/2026-04-14-silent-failure-audit.md`) and implements targeted fixes for every **Confirmed Vulnerability** and high-priority **Latent Risk** identified there. Each fix is paired with a regression test that would have caught the original bug. No fix is marked done until its test passes.

## Tasks

- [x] Read the Phase 01 audit report before touching any code:
  - Read: `docs/claude/audit/2026-04-14-silent-failure-audit.md`
  - Read the Fix Priority Order section — work top to bottom
  - Pre-flight contract check per CLAUDE.md: identify which pipeline layers each fix touches, which contract sections apply, and what invariants must not change
  - If the audit report is missing or empty, STOP and report — do not proceed without it
  - **Completed 2026-04-15**: Audit report read. 6 Confirmed Vulnerabilities + 5 Latent Risks identified. Pre-flight: touches layers 2–4 (LLM, tool execution, UI). Must not change `parse_llm_response`/`ParsedResponse` API or `AgentResult` fields. GPU process check N/A. All fixes additive.

- [x] Fix response_parser.py vulnerabilities (if any confirmed in audit):
  - Work on: `financial-engine_v2/cockpit/core/response_parser.py`
  - Common fixes to implement if confirmed:
    - Handle the case where `_try_split_multi_json` finds 3+ objects (thinking + tool_call + response) — ensure `response_obj` wins and thinking metadata is preserved
    - Handle `type` field present but not in `VALID_TYPES` — current `_infer_type` fallback should be exercised but confirm it is
    - Handle `_repair_json` being applied to multi-object strings — ensure repair doesn't merge two objects into one broken object
  - After each fix: run `python -m ruff check financial-engine_v2/cockpit/core/response_parser.py`
  - Do not change the public interface of `parse_llm_response` or `ParsedResponse`
  - **Completed 2026-04-15**: Audit findings verified. 3+ object case already handled; added `logger.debug` for non-thinking/non-response skipped objects (Latent Risk 7). `_infer_type` fallback confirmed working (Safe in audit). `_repair_json` clarified via docstring — trailing-comma repair cannot merge separate objects; limitation on unterminated strings documented. Ruff clean.

- [x] Write regression tests for response_parser.py:
  - File: `financial-engine_v2/cockpit/tests/test_response_parser.py` (create if missing, extend if exists)
  - Required test cases (write these regardless of whether fixes were needed above):
    - `test_multi_json_three_objects`: thinking + tool_call + response in one completion → response content returned, thinking metadata preserved
    - `test_multi_json_no_response_block`: two thinking objects, no response block → last object used
    - `test_invalid_type_field`: `{"type": "unknown_xyz", "content": "hi"}` → inferred as response type
    - `test_repair_trailing_comma_in_nested`: `{"type": "response", "content": {"key": "value",}}` → parsed correctly
    - `test_parse_llm_response_known_bug_regression`: the exact raw string that caused Bug 1 (two concatenated JSON objects) → returns response content, not raw JSON
  - Run tests: `pytest financial-engine_v2/cockpit/tests/test_response_parser.py -v`
  - All must pass before continuing
  - **Completed 2026-04-15**: Added `TestRegressions` class with all 5 required test cases. 19/19 tests pass (14 existing + 5 new).

- [x] Fix agent_loop.py vulnerabilities (if any confirmed in audit):
  - Work on: `financial-engine_v2/cockpit/core/agent_loop.py`
  - Common fixes to implement if confirmed:
    - Guard tool_calls multi-call branch against entries missing `id`, `tool`, or `arguments` keys — skip or substitute defaults rather than KeyError
    - Guard `on_thinking` callback against `None` assessment or plan — coerce to empty string before calling
    - Guard `evidence.append()` against non-dict tool results — wrap in type check and log if skipped
  - After each fix: run `python -m ruff check financial-engine_v2/cockpit/core/agent_loop.py`
  - Do not change `AgentResult` dataclass fields (would break callers)
  - **Completed 2026-04-15**: All three listed concerns confirmed "Safe / Already Handled" per audit report §Safe section. (1) `_normalize_tool_calls` uses `.get("tool", "unknown")` and `.get("arguments") or {}` — no KeyError possible (lines 817–818). (2) `on_thinking` receives `assessment = parsed.assessment or parsed.content or ""` and `plan = parsed.plan or ""` — null-coerced before callback (lines 324–325). (3) `_execute_tool` wraps non-dict results via `if not isinstance(result, dict): result = {"result": result}` (lines 836–837). No code changes required. Ruff clean confirmed.

- [x] Write regression tests for agent_loop.py:
  - File: `financial-engine_v2/cockpit/tests/test_agent_loop.py` (create if missing, extend if exists)
  - Required test cases:
    - `test_tool_calls_missing_id_key`: tool_calls response with a call dict missing `id` → loop continues, doesn't raise KeyError
    - `test_tool_result_non_dict`: tool executor returns a string/list instead of dict → evidence entry skipped, loop continues
    - `test_on_thinking_none_fields`: LLM emits `{"type":"thinking","assessment":null,"plan":null}` → on_thinking called with empty strings, no AttributeError
    - `test_evidence_collects_from_mixed_formats`: one orchestrator-format and one agent-loop-format evidence entry → both survive in AgentResult.evidence
  - Run tests: `pytest financial-engine_v2/cockpit/tests/test_agent_loop.py -v`
  - All must pass
  - **Completed 2026-04-15**: Created `test_agent_loop.py` with `TestAgentLoopRegressions` class covering all 4 required cases. Note: `test_tool_result_non_dict` verifies the result is *wrapped* (not skipped) since `_execute_tool` wraps non-dict via `{"result": value}` — evidence entry is present with wrapped content. All 4 tests pass.

- [x] Fix `tool_executor.py` and `tools.py` vulnerabilities (if any confirmed in audit):
  - `search_news` handler (`_exec_search_news`) lives in: `financial-engine_v2/cockpit/core/tool_executor.py` (line ~292)
  - `gather_local_context` lives in: `financial-engine_v2/cockpit/core/tools.py`
  - Common fixes to implement if confirmed:
    - Ensure `_exec_search_news` attaches `freshness_warning` even when result has 0 hits (current fix only fires when hits is non-empty — the 0-hits path may be silent)
    - For any tool handler that calls an HTTP endpoint: ensure the error branch always returns a dict with at minimum `{"error": "...", "hits": [], "docs": []}` so callers don't KeyError on missing keys
    - If `gather_local_context` and cloud path return different key shapes, add a normalization layer so `_build_ui_sources` sees a consistent shape regardless of routing
  - After each fix: run `python -m ruff check financial-engine_v2/cockpit/core/tool_executor.py financial-engine_v2/cockpit/core/tools.py`
  - **Completed 2026-04-15**: Confirmed vulnerability: `_exec_search_news` 0-hit path emitted no `freshness_warning` (audit §1, HIGH). Added `else` branch after `if compact_hits:` block that injects today's date and corpus-absence caveat. HTTP error path already safe (outer `execute()` try/except — audit §Safe). `tools.py` has no confirmed vulnerability. Ruff clean.

- [x] Write regression tests for tool_executor.py / tools.py:
  - File: `financial-engine_v2/cockpit/tests/test_tool_executor.py` (extend if exists; see also `test_tool_executor_extraction.py` and `test_tool_executor_silent_degradation.py` for existing patterns)
  - Required test cases:
    - `test_exec_search_news_zero_hits_has_freshness_key`: mock backend returns `{"hits": []}` → result dict still contains `freshness_warning` key (even if empty/None)
    - `test_exec_search_news_freshness_warning_stale_news`: mock backend returns articles all older than 2 days → `freshness_warning` is a non-empty string
    - `test_exec_search_news_freshness_warning_fresh_news`: mock backend returns article from today → `freshness_warning` is absent or empty
    - `test_tool_http_error_returns_safe_dict`: mock backend returns 500 → handler returns dict without raising, with `hits` and/or `docs` keys present as empty lists
    - `test_known_bug_regression_empty_sources`: the exact evidence shape that caused Bug 2 (agent-mode `{tool:"search_news", result:{hits:[...]}}`) → `_build_ui_sources` returns non-empty list
  - Run tests: `pytest financial-engine_v2/cockpit/tests/test_tool_executor_extraction.py financial-engine_v2/cockpit/tests/test_tool_executor_silent_degradation.py -v`
  - All must pass
  - **Completed 2026-04-15**: Created `test_tool_executor.py` with all 5 required tests. 5/5 pass. 32 existing regression tests still green.

- [ ] Fix `_build_ui_sources` gaps (if any confirmed in audit):
  - Work on: `financial-engine_v2/backend/app/routes/cockpit_api.py` (the `_build_ui_sources` function only)
  - For each tool confirmed in the audit as producing evidence but not handled in the agent-evidence branch: add an `elif tool_name == "..."` branch with the correct key extraction
  - Ensure every new branch follows the same pattern as existing ones (no mutation, use `_append_source_item`)
  - Do not touch any code outside `_build_ui_sources` and its helper `_append_source_item`
  - After fix: run `python -m ruff check financial-engine_v2/backend/app/routes/cockpit_api.py`

- [ ] Write regression tests for `_build_ui_sources`:
  - File: `financial-engine_v2/backend/tests/test_build_ui_sources.py` (create if missing)
  - Required test cases (import `_build_ui_sources` directly from `app.routes.cockpit_api`):
    - `test_orchestrator_format_local_context`: evidence in `{type:"local_context", details:{hits:[...]}}` format → sources extracted
    - `test_agent_format_search_news`: evidence in `{tool:"search_news", result:{hits:[...]}}` format → sources extracted (regression for Bug 2)
    - `test_agent_format_gather_local_context`: evidence in `{tool:"gather_local_context", result:{rag_hits:[...]}}` format → sources extracted
    - `test_empty_evidence_list`: `[]` → returns `[]` without error
    - `test_non_dict_evidence_entry`: evidence list contains a string → skipped, no TypeError
    - One test for each new tool branch added in this phase
  - Run: `pytest financial-engine_v2/backend/tests/test_build_ui_sources.py -v`
  - All must pass

- [ ] Fix temporal anchoring vulnerabilities (if any confirmed in audit):
  - If tenn_chat system prompt does not inject current date: add it
    - Work on: `financial-engine_v2/backend/app/services/tenn_chat.py`
    - Inject `today_iso = datetime.now(timezone.utc).date().isoformat()` into the system prompt as `"Today's date is {today_iso}. Treat any dates in retrieved content as historical context."`
  - If retrieved chunks inject `published_at` / `created_at` fields into the prompt context without a freshness caveat: add one
  - If any Celery task calls the LLM with context that includes date fields but no declared current date: add the same injection
  - After each fix: run `python -m ruff check` on the changed file

- [ ] Write regression tests for temporal anchoring:
  - File: `financial-engine_v2/backend/tests/test_temporal_anchoring.py` (create if missing)
  - Required test cases:
    - `test_tenn_chat_system_prompt_contains_today`: call the function that builds the system prompt → assert "Today" or current ISO date appears in the result
    - `test_search_news_freshness_warning_injected_into_agent_context`: when `search_news` returns stale articles, the tool result includes `freshness_warning` → assert the warning text mentions the days-old gap and today's date (regression for Bug 3)
  - Run: `pytest financial-engine_v2/backend/tests/test_temporal_anchoring.py -v`
  - All must pass

- [ ] Fix extraction pipeline vulnerabilities (if any confirmed in audit):
  - For each confirmed finding in the Celery tasks / extraction layer:
    - Identify whether the failure mode is: (a) LLM returns bad JSON → unhandled, (b) key missing from LLM response → silent default, or (c) result processed as success when it should be failed
    - Apply fix per the bug-resolution rule: fix root cause first, then add error handling
    - Do NOT add a `try/except` around a broken call without also fixing why the call fails
  - After each fix: run `python -m ruff check` on changed files
  - Run existing backend tests: `pytest financial-engine_v2/backend/tests/ -v -x` — no regressions allowed

- [ ] Write regression tests for extraction pipeline vulnerabilities:
  - Add test cases to the appropriate existing test files or create `test_extraction_hardening.py`
  - One test per confirmed finding; test must fail before the fix and pass after
  - Run full test suite: `pytest financial-engine_v2/backend/tests/ -v`

- [ ] Run full test suite and verify no regressions:
  - Run: `pytest financial-engine_v2/backend/tests/ -v`
  - Run: `pytest financial-engine_v2/cockpit/tests/ -v` (if test dir exists)
  - Run: `python -m ruff check financial-engine_v2/backend financial-engine_v2/cockpit`
  - All must be green; investigate and fix any new failures before proceeding

- [ ] Log lessons and commit:
  - Append to `docs/claude/lessons.md`: one entry per confirmed bug pattern fixed, in the format:
    ```
    ## YYYY-MM-DD: [pattern name]
    Pattern: [what the latent assumption was]
    Rule: [what invariant prevents it recurring]
    Fixed in: [file(s)]
    ```
  - Stage all changed files and create a milestone commit:
    ```
    milestone(cockpit): harden silent-failure paths identified in 2026-04-14 audit

    Working: [brief list of what is now defended]
    Tested: pytest green on backend/tests and cockpit/tests
    ```
  - Do NOT commit unless all tests pass
