# Validation

## Preflight

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue242-context-diagnostics-guard-current-base-v1-20260627 --topic "issue242 context diagnostics guard current base" --json`: exit 0, `final_decision=pass`, `stop_reimplementation=false`, `path_ownership.classification=VALID_TASK_WORKTREE`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: exit 0, active jobs empty before claim.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- `python3 scripts/agent_task_ledger.py --repo-root . validate`: pending final check.

## RED

- Command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py -q`
- Exit: 1.
- Result: 5 failed, 2 passed.
- Expected failures: ticker context lacked `diagnostics_redacted`/redaction
  behavior, verification context returned 200 without a configured key, and
  verification run history opened `CockpitService` before auth.

## GREEN

- Command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py -q`
- Exit: 0.
- Result: 7 passed.

## Static Checks

- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py`: exit 0, all checks passed.
- `python3 -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py`: exit 0.
- `git diff --cached --check`: exit 0 before report files.

## Frontend Validation

- `pnpm --dir cockpit-ui exec vitest run lib/api-client.test.ts`: exit 254, blocked with `Command "vitest" not found`.
- `pnpm --dir cockpit-ui exec eslint lib/api-client.ts lib/api-client.test.ts components/cockpit/verification/verification-screen.tsx`: exit 254, blocked with `Command "eslint" not found`.
- Dependency evidence:
  `test -d cockpit-ui/node_modules` returned status 1,
  `test -x cockpit-ui/node_modules/.bin/vitest` returned status 1, and
  `test -x cockpit-ui/node_modules/.bin/eslint` returned status 1.
- Action: no dependency install was performed because the task card forbids
  project dependency installs and lockfile/package manifest mutation.

## Report Gates

- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md --repo-root .`: exit 0, no disallowed files.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- Registry release: exit 0; active record removed and report status updated.
- PR: https://github.com/0rl4nd0l/tenn/pull/438.
