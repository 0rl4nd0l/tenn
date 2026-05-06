# Validation

## Passed

- `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/cockpit/storage/state.py financial-engine_v2/cockpit/tests/test_state_chat_sessions.py financial-engine_v2/cockpit/tests/test_chat_attached_sources.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_build_ui_sources.py financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py`
  - Result: passed
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_build_ui_sources.py financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py financial-engine_v2/cockpit/tests/test_state_chat_sessions.py financial-engine_v2/cockpit/tests/test_chat_attached_sources.py -q`
  - Result: 60 passed
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -k "attached or holdings or runtime" -q`
  - Result: 5 passed
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_news_retrieval_eval.py -k "A2M or local_news or degraded" -q`
  - Result: 1 passed
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests -k "source or label or evidence or session or attached or holdings or a2m or runtime" -q`
  - Result: 208 passed, 1006 deselected
- `pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/terminal-message.test.tsx components/cockpit/chat/sources-drawer.test.tsx`
  - Result: 13 passed
- `pnpm --dir cockpit-ui exec tsc --noEmit`
  - Result: passed
- `git diff --check`
  - Result: passed

## Broad Selector Failures Recorded

- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests -k "source or label or evidence or session or attached or holdings or a2m or runtime" -q`
  - Result: 320 passed, 1155 deselected, 2 failed
  - Failures: `test_no_sqlite_usage_in_backend_runtime`, `test_no_sqlite3_in_runtime`
  - Cause recorded: pre-existing architecture invariant failures for `sqlite3` imports in backend runtime files. This patch did not add an import or SQLite runtime dependency in `cockpit_api.py`.
- `pnpm --dir cockpit-ui test -- terminal-message`
  - Result: 118 passed, 1 failed
  - Failure: unrelated `components/cockpit/holdings/holdings-screen.test.tsx` expected `Cost Basis Known`.
  - Direct terminal-message and sources-drawer Vitest files passed.
