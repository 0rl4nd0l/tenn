# Extraction PR129 CI Test Harness Second Slice V1

## Summary

- PR: #129
- Branch: `safe/extraction-real-gold-corpus-baseline-v1-20260529`
- Lane: Evaluation
- Mode: SAFE EXTENSION, test/report files only
- Production code changed: no
- Runtime/canary/datastore/source mutation: no

## CI Failures Addressed

This slice addresses four bounded test-harness drifts from the GitHub Actions
`lint-and-test` failure set:

- `test_cockpit_api_preferences.py`: expected response now includes the
  production `chat_runtime_target` field.
- `test_cockpit_conversation_continuity.py`: fake chat-controller builder now
  accepts the current `llm_client=` keyword.
- `test_process_document_api.py`: sync-path test explicitly pins
  `settings.task_mode` to `sync`, avoiding Redis/Celery contact in CI.
- `test_subagents.py`: async tests use `asyncio.run()` instead of relying on a
  pre-existing default event loop in the main thread.

## Validation

Passed:

- Task-card validation for
  `docs/agent_tasks/extraction_pr129_ci_test_harness_second_slice_v1_20260529.md`
- Registry overlap check and claim
- Focused repro after fix:
  - `test_cockpit_api_preferences.py`
  - `test_cockpit_conversation_continuity.py`
  - `test_process_document_api.py`
  - `test_subagents.py`
  - Result: `33 passed, 5 warnings`
- Targeted Ruff on touched test files: passed
- `py_compile` on touched test files: passed
- Focused extraction regression suite:
  - `test_extraction_gold_eval.py`
  - `test_extraction_pre_canary_truth_gates.py`
  - `test_extraction_gold_eval_scorecard.py`
  - `test_multipass_extraction.py`
  - `test_metric_ontology_bridge.py`
  - Result: `252 passed, 5 warnings`
- `git diff --check`: passed
- Code-reviewer pass over the test-only diff: no blocking findings

## Remaining CI Risk

The GitHub run also reported marketplace, memo-routing, query-orchestrator,
agent/router, and broader Cockpit failures outside this slice's allowlist.
Those remain separate CI-harness or product-lane follow-ups unless the next run
proves this slice exposes a narrower residual failure.

## Files Changed

- `docs/agent_tasks/extraction_pr129_ci_test_harness_second_slice_v1_20260529.md`
- `financial-engine_v2/backend/tests/test_cockpit_api_preferences.py`
- `financial-engine_v2/backend/tests/test_cockpit_conversation_continuity.py`
- `financial-engine_v2/backend/tests/test_process_document_api.py`
- `financial-engine_v2/cockpit/tests/test_subagents.py`
- `reports/agent_jobs/extraction_pr129_ci_test_harness_second_slice_v1_20260529/README.md`
- `reports/agent_jobs/extraction_pr129_ci_test_harness_second_slice_v1_20260529/status.json`
- `reports/agent_jobs/extraction_pr129_ci_test_harness_second_slice_v1_20260529/diff-check.json`
- `docs/claude/STATE.md`

## Next Safe Step

Push this slice and re-check PR #129. If `lint-and-test` remains red, inspect
the new logs and create another bounded task card for the next failure cluster.
