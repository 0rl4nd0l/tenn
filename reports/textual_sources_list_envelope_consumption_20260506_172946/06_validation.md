# Validation

## Commands Run

```text
financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/cockpit/core/chat.py financial-engine_v2/cockpit/tests/test_slash_commands.py financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py
```

Result:

```text
All checks passed!
```

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_slash_commands.py financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py -q
```

Result:

```text
147 passed, 6 warnings in 9.32s
```

Warnings were existing Pydantic namespace/deprecation warnings.

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_query_orchestrator.py financial-engine_v2/backend/tests/test_sources.py -q
```

Result:

```text
38 passed in 1.63s
```

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests -k "sources or textual or evidence or envelope or no_hit or degraded or holdings or memory or financial_truth or local_news" -q
```

Result:

```text
266 passed, 1226 deselected, 6 warnings in 24.32s
```

Warnings were existing `requests` dependency and FastAPI/Pydantic deprecation warnings.

```text
financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/cockpit/core/chat.py financial-engine_v2/cockpit/tests/test_slash_commands.py financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py
```

Result:

```text
All checks passed!
```

```text
git diff --check
```

Result:

```text
passed with no output
```

```text
financial-engine_v2/.venv/bin/python scripts/agent_job_contract.py validate docs/agent_tasks/reporting_textual_sources_list_v1.md
```

Result:

```text
ok: true
issues: []
```

```text
financial-engine_v2/.venv/bin/python scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_textual_sources_list_v1.md
```

Result:

```text
ok: false
report_path: reports/agent_jobs/reporting_textual_sources_list_v1/diff-check.json
```

Reason:

- The check-diff validator reported unrelated dirty files outside this task card, including Cockpit web/home/design files and unrelated task cards.
- The task files changed by Codex were within the intended Python/Textual source-display scope.
