# Validation

## Passed

```text
$ financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/cockpit/core/agent_loop.py financial-engine_v2/backend/tests/test_build_ui_sources.py financial-engine_v2/backend/tests/test_cockpit_api_models.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/cockpit/tests/test_agent_loop_synthesis_timeout.py
All checks passed!
```

```text
$ financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_build_ui_sources.py financial-engine_v2/backend/tests/test_cockpit_api_models.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q
93 passed in 9.22s
```

```text
$ financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -q
47 passed in 10.81s
```

```text
$ financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_agent_loop_synthesis_timeout.py -q
6 passed in 0.28s
```

```text
$ financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q
70 passed in 9.91s
```

```text
$ financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_agent_loop.py financial-engine_v2/cockpit/tests/test_chat_holdings_intent_routing.py financial-engine_v2/cockpit/tests/test_agent_loop_synthesis_timeout.py -q
50 passed, 6 warnings in 12.15s
```

```text
$ financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_preferences.py -q
4 passed in 2.27s
```

```text
$ pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/terminal-message.test.tsx
1 passed, 10 tests
```

```text
$ pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/terminal-message.test.tsx components/cockpit/chat/sources-drawer.test.tsx
2 passed, 12 tests
```

```text
$ pnpm --dir cockpit-ui exec tsc --noEmit
passed with no output
```

```text
$ git diff --check
passed with no output
```

## Broad Selector With Unrelated Existing Failures

```text
$ financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests -k "source or label or evidence or a2m or news or holdings or runtime" -q
302 passed, 1158 deselected, 6 warnings
2 failed
```

Failures:

- `financial-engine_v2/backend/tests/test_architecture_invariants.py::test_no_sqlite_usage_in_backend_runtime`
- `financial-engine_v2/backend/tests/test_cursor_rule_compliance.py::test_no_sqlite3_in_runtime`

Failure cause recorded from test output:

- pre-existing `sqlite3` imports in runtime files including `cockpit_api.py`, `market_memory.py`, `ops_store.py`, `response_feedback.py`, `company_memory.py`, `user_thesis_memory.py`, `marketplace_price_intelligence.py`, and `api/context.py`.

These failures are outside this lane and were not fixed.

## UI Broad Command With Unrelated Existing Failure

```text
$ pnpm --dir cockpit-ui test -- terminal-message
failed
```

This command ran broader unrelated UI tests. The unrelated failure observed was in a holdings-screen test expecting `Cost Basis Known`. File-specific Vitest for `terminal-message` and `sources-drawer` passed after the focused fixes.
