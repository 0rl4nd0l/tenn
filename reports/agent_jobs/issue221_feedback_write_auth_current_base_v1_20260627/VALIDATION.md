# Validation

## Passed

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue221_feedback_write_auth_current_base_v1_20260627.md
```

Result: PASS.

```text
python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/issue221_feedback_write_auth_current_base_v1_20260627.md
python3 scripts/agent_job_registry.py claim --repo-root . docs/agent_tasks/issue221_feedback_write_auth_current_base_v1_20260627.md
```

Result: PASS; registry claim active for this task.

```text
uv run --with pytest --with fastapi==0.115.6 --with httpx==0.27.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with PyYAML --with python-multipart --with celery --with qdrant-client --with pymupdf --with beautifulsoup4 --with pandas --with exchange_calendars pytest -q financial-engine_v2/backend/tests/test_response_feedback.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -k "feedback"
```

Result: 24 passed, 55 deselected, 1 existing warning.

```text
uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_feedback.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_response_feedback.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
```

Result: PASS.

```text
python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_feedback.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_response_feedback.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
```

Result: PASS.

```text
git diff --check
```

Result: PASS.

## Known Validation Gaps

- Initial focused pytest attempts failed during collection because the ephemeral
  uv environment lacked route-import dependencies (`celery`, `qdrant-client`,
  `pymupdf`, `beautifulsoup4`, `pandas`, `exchange_calendars`). The final
  focused pytest command above included only those import requirements and
  passed.
- Frontend check:
  `corepack pnpm --dir cockpit-ui exec vitest run lib/claim-verification-route.test.ts components/cockpit/chat/chat-screen.test.tsx`
  failed with `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL Command "vitest" not found`.
  `cockpit-ui/node_modules` and `cockpit-ui/node_modules/.bin/vitest` are
  absent in this worktree. No dependency install was run.
- No live backend/Cockpit runtime was started.
- No live feedback store was queried.
