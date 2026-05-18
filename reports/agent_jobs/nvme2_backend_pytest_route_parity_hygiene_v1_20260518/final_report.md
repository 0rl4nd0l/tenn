# NVMe2 Backend Pytest + Route-Parity Validation Report

## Task card
- `docs/agent_tasks/nvme2_backend_pytest_route_parity_hygiene_v1_20260518.md`

## Context
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Expected branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `03d1fa42`
- Expected HEAD: `03d1fa42`
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Lane: Evaluation
- Supporting lanes: Repo Hygiene, Reporting
- Mode: SAFE EXTENSION
- Collision risk declared: MEDIUM

## Registry state
- `agent_job_registry list-active` before claim: none
- Job claim: `ok: true`
- `agent_job_contract validate`: `ok: true`
- `agent_job_contract check-diff`: `ok: true`
- `agent_job_registry release`: `ok: true`
- `agent_job_registry list-active` after release: none

## Hygiene classification
| path | lane | status | reason |
|---|---|---|---|
| `docs/agent_tasks/nvme2_route_parity_tests_only_v1_20260518.md` | Evaluation | retained | Existing route-parity task artifact from prior NVMe2 route parity work; no longer blocks current focused backend test run. |
| `reports/agent_jobs/nvme2_route_parity_tests_only_v1_20260518/` | Reporting | retained | Historical validation artifacts for prior parity task; not required input for this command path. |
| `reports/agent_jobs/nvme2_route_parity_followup_audit_v1_20260518/` | Evaluation | retained | Historical route-parity follow-up evidence; not blocking this focused backend pytest restore. |
| `financial-engine_v2/backend/requirements-dev.txt` | Evaluation | blocker (resolved) | Missing pytest tooling prevented command execution until dev dependencies were restored. |
| `docs/agent_tasks/nvme2_backend_pytest_route_parity_hygiene_v1_20260518.md` | Evaluation | retained | New task card for this bounded lane. |

## Cleanup performed
- No stale report/task artifacts were deleted.
- Cleanup was limited to none; no bound cleanup was required to complete the focused route-parity test command.
- All stale-looking artifacts identified were retained as historical reference because they are not blocking this validation.

## Dependency/env restore
- Updated `financial-engine_v2/backend/requirements-dev.txt`:
  - Added `pytest>=8.3.3`
  - Added `pytest-asyncio>=0.24.0`
- Installed dev requirements into existing backend venv:
  - `financial-engine_v2/.venv/bin/pip install -r financial-engine_v2/backend/requirements-dev.txt`

## Test command and results
1) Initial attempt
- Command: `PATH="$PWD/financial-engine_v2/.venv/bin:$PATH" pytest financial-engine_v2/backend/tests/test_route_parity_contract.py -q`
- Result: command failed (`pytest: command not found`) because `pytest` was not installed in the venv.

2) Focused route-parity validation (success)
- Command: `PATH="$PWD/financial-engine_v2/.venv/bin:$PATH" financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_route_parity_contract.py -q`
- Result: `2 passed, 5 warnings in 3.06s`
- Classification: pass

3) Broad `-k route` attempt (unrelated collection blocker)
- Command: `PATH="$PWD/financial-engine_v2/.venv/bin:$PATH" financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests -q -k route`
- Result: collection failed before route tests completed.
- Blocker: `financial-engine_v2/backend/tests/test_load_news_to_qdrant.py` cannot import `load_news_to_qdrant` from `scripts`.
- Classification: unrelated News substrate/test-import blocker; not a route parity blocker and not an NVMe2 migration blocker.

4) Route-scoped backend file set (success)
- Command: `PATH="$PWD/financial-engine_v2/.venv/bin:$PATH" financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_*route* financial-engine_v2/backend/tests/test_route_parity_contract.py -q`
- Result: `28 passed, 5 warnings in 3.34s`
- Classification: pass

## Route parity scope
- Focused command passed against backend route profile for the NVMe2 baseline.
- No backend route-contract regressions were hit in this run.
- No unrelated marketplace/frontend pytest paths were executed.
- The broad `-k route` collection blocker is logged as News substrate/test-import follow-up work.

## Repository health checks
- `git diff --check`: no issues
- `agent_job_contract check-diff`: passed after task-card allowed_file update

## Required safety confirmation
- No mutation of `/data`, `/reports`, HDD source data, Qdrant, Postgres/SQLite stores, or Docker volumes.
- No runtime launch scripts or binding paths were changed.
- NVMe2 bindings `/data` and `/reports` were not edited.

## Worktree state
- `git status --short --untracked-files=all`:
  - ` M financial-engine_v2/backend/requirements-dev.txt`
  - `?? docs/agent_tasks/nvme2_backend_pytest_route_parity_hygiene_v1_20260518.md`

## Files changed/deleted
### Changed
- `financial-engine_v2/backend/requirements-dev.txt`
- `docs/agent_tasks/nvme2_backend_pytest_route_parity_hygiene_v1_20260518.md`
### Deleted
- none

## Final status
- Backend pytest is now restored in this worktree for focused backend route-parity command use.
- Route parity backend pytest now passes in this environment after restore.
- Route-scoped backend file set now passes: `28 passed, 5 warnings in 3.34s`.
- Unrelated blocker: `financial-engine_v2/backend/tests/test_load_news_to_qdrant.py` import path for `load_news_to_qdrant`.
- No data-binding/runtime side effects were introduced.
