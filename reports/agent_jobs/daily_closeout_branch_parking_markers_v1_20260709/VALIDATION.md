# Validation

## Planned

- task-card validation
- report-review marker validation for both daily-closeout report directories
- report-review marker scan
- task-card diff/report/closeout checks
- marker JSON syntax checks
- whitespace check
- final git status

## Completed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/daily_closeout_branch_parking_markers_v1_20260709.md`
  - exit status: 0
  - result: task card valid after changing primary lane from `Repo Hygiene` to
    accepted lane `Query Orchestration`
- `python3 scripts/report_review_status.py validate reports/agent_jobs/daily_closeout_execution_worktree_reconcile_v1_20260708 --repo-root . --require-existing-source-paths`
  - exit status: 0
  - result: marker valid; status `PARKED`
- `python3 scripts/report_review_status.py validate reports/agent_jobs/daily_closeout_live_timer_install_v1_20260708 --repo-root . --require-existing-source-paths`
  - exit status: 0
  - result: marker valid; status `PARKED`; `runtime_functionality_proven=true`
- `python3 -m json.tool reports/agent_jobs/daily_closeout_execution_worktree_reconcile_v1_20260708/REPORT_REVIEW_STATUS.json`
  - exit status: 0
  - result: JSON syntax valid
- `python3 -m json.tool reports/agent_jobs/daily_closeout_live_timer_install_v1_20260708/REPORT_REVIEW_STATUS.json`
  - exit status: 0
  - result: JSON syntax valid
- `python3 scripts/report_review_status.py scan reports/agent_jobs --repo-root .`
  - exit status: 0
  - result: scan ok; both daily-closeout reports show `PARKED`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/daily_closeout_branch_parking_markers_v1_20260709.md`
  - exit status: 0
  - result: changed files are inside `allowed_files`; wrote
    `reports/agent_jobs/daily_closeout_branch_parking_markers_v1_20260709/diff-check.json`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/daily_closeout_branch_parking_markers_v1_20260709.md`
  - exit status: 0
  - result: required report artifacts exist
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/daily_closeout_branch_parking_markers_v1_20260709.md`
  - exit status: 0
  - result: closeout check passed
- `git diff --check && git diff --cached --check`
  - exit status: 0
  - result: no whitespace errors after removing extra blank EOF lines

- post-commit `git status --short --untracked-files=all`
  - exit status: 0
  - result: clean
- post-commit `python3 scripts/tenn_dev_status.py`
  - exit status: 0
  - result: `STATE: CLEAN`, guard passed, registry passed, ledger passed
