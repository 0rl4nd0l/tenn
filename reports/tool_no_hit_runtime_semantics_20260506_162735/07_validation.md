# Validation

Focused validation:

- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_build_ui_sources.py -q`
  - Result: 49 passed.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_tool_executor.py -q`
  - Result: 27 passed.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_agent_loop.py -k "degraded_tool_result or missing_financial_rows" -q`
  - Result: 2 passed, 36 deselected.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -k "zero_hit or degraded_runtime or tv_screener_empty or financial_truth_missing or web_tool_failure or holdings or memory or attached or a2m" -q`
  - Result: 10 passed, 39 deselected.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_agent_loop_synthesis_timeout.py -q`
  - Result: 6 passed.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -k "tv_screener_evidence or tv_screener_empty or financial_truth_missing or web_tool_failure or zero_hit or degraded_runtime" -q`
  - Result: 7 passed, 42 deselected.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_build_ui_sources.py financial-engine_v2/cockpit/tests/test_tool_executor.py financial-engine_v2/cockpit/tests/test_agent_loop.py -k "degraded_tool_result or missing_financial_rows or no_hit or degraded or search_web or financial_rows or tv_screener" -q`
  - Result: 20 passed, 94 deselected.

Static checks:

- `financial-engine_v2/.venv/bin/python -m ruff check <changed_python_files>`
  - Result: all checks passed.
- `git diff --check`
  - Result: passed.

Broader requested selectors:

- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests -k "source or label or evidence or no_hit or runtime or degraded or web or holdings or a2m or memory" -q`
  - Result after fix: 358 passed, 1124 deselected, 2 failed.
  - Failures are existing unrelated SQLite invariant failures:
    - `test_architecture_invariants.py::test_no_sqlite_usage_in_backend_runtime`
    - `test_cursor_rule_compliance.py::test_no_sqlite3_in_runtime`
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests -k "source or label or evidence or no_hit or runtime or degraded or web or holdings or a2m or memory" -q`
  - Result: 272 passed, 943 deselected, 3 failed.
  - Failures are existing unrelated event-loop failures in `test_subagents.py`.

UI validation:

- Not run. No Cockpit UI files were intentionally changed by this task.
