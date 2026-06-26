# Validation

## Preflight

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue229-cockpit-chat-session-route-guard-current-base-v1-20260627 --topic issue229-cockpit-chat-session-route-guard --json`
  - Exit: 0
  - Result: `final_decision=pass`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_session_route_guard_v1_20260602.md`
  - Exit: 0
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_session_route_guard_v1_20260602.md --repo-root .`
  - Exit: 0
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_session_route_guard_v1_20260602.md --repo-root .`
  - Exit: 0
- `python3 scripts/agent_task_ledger.py append --fill-identity --entry-json ...`
  - Exit: 0

## RED

Temp red worktree:
`/tmp/tenn-issue229-red-current-base-20260627`

Setup:

- Detached at `origin/migration/clean-runtime-baseline-reconstruct-v1`
  (`7d6ab6c184332d5413700eb08e6790f530000942`).
- Applied only the backend test diff.
- Removed after the red run.

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream_keepalive.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Exit: 1

Expected result:

- `16 failed, 89 passed, 5 warnings`
- Failures showed missing 401s on chat/session routes, stateless-smoke reaching
  `chat_stream`, and missing route-level API-key dependency registration.

## GREEN

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream_keepalive.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Exit: 0

Result:

- `105 passed, 5 warnings`

## Static Checks

- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream_keepalive.py financial-engine_v2/backend/tests/test_local_api_key.py`
  - Exit: 0
  - Result: `All checks passed!`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream_keepalive.py financial-engine_v2/backend/tests/test_local_api_key.py`
  - Exit: 0
- `git diff --check`
  - Exit: 0
- `python3 scripts/agent_task_ledger.py validate`
  - Exit: 0
  - Result: no `DATA_MISSING`

## Frontend Validation

Command:

```bash
npm test -- --run lib/api-client.test.ts
```

Working directory: `cockpit-ui`

Exit: 127

Result:

- `sh: 1: vitest: not found`
- `node_modules/.bin/vitest` is absent.

Status: `DATA_MISSING`

No dependency install was run because the task did not explicitly approve
dependency installation.
