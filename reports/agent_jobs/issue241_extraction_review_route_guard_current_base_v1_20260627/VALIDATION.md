# Validation

## Preflight

- `git fetch origin`: exit 0.
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue241-extraction-review-route-guard-current-base-v1-20260627 --topic "issue241 extraction review route guard current base" --json`: exit 0, `final_decision=pass`, `stop_reimplementation=false`, `path_ownership.classification=VALID_TASK_WORKTREE`.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: exit 0, active jobs empty before claim.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md`: exit 0.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- `python3 scripts/agent_task_ledger.py validate`: exit 0.

## RED

- Command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_review_route_auth.py`
- Exit: 1.
- Result: 6 failed, 8 passed.
- Expected failures: missing-key reads returned 200 instead of 401 for runs,
  sessions, session contents, errors, run status, and snippet images.

## GREEN

- Command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_review_route_auth.py`
- Exit: 0.
- Result: 14 passed.

- Command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_review_route_auth.py financial-engine_v2/backend/tests/test_extraction_review_service.py`
- Exit: 0.
- Result: 34 passed.

## Static Checks

- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/extraction_review.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py`: exit 0, all checks passed.
- `python3 -m py_compile financial-engine_v2/backend/app/api/extraction_review.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py`: exit 0.
- `git diff --check`: exit 0.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md --repo-root .`: exit 0, no disallowed files.

## Frontend Validation

- Command:
  `pnpm --dir cockpit-ui exec vitest run lib/api-client.test.ts`
- Exit: 254.
- Result: blocked locally with `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL Command "vitest" not found`.
- Dependency evidence:
  `test -d cockpit-ui/node_modules` returned status 1 and
  `test -x cockpit-ui/node_modules/.bin/vitest` returned status 1.
- Action: no dependency install was performed because the task card forbids
  project dependency installs and lockfile/package manifest mutation.

## Report Gates

- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- `python3 scripts/agent_task_ledger.py validate`: exit 0.
- `python3 scripts/agent_job_registry.py release issue241_extraction_review_route_guard_current_base_v1_20260627 --repo-root .`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: exit 0, active jobs empty.
- PR #436: opened at https://github.com/0rl4nd0l/tenn/pull/436; live checks were in progress at creation.
