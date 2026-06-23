# Validation

## Completed

- `gh pr view 388 --repo 0rl4nd0l/tenn --json number,state,title,headRefName,baseRefName,mergeCommit,mergedAt,mergeStateStatus,mergeable,statusCheckRollup,commits,updatedAt,reviewDecision,reviews`: passed; PR #388 is merged at `d8be998e0d1aae992c12b1d5bf7ca42229f46508`.
- `gh pr checks 388 --repo 0rl4nd0l/tenn`: passed; `lint-and-test` and `scan` passed.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: passed; no active jobs.
- `python3 scripts/agent_task_ledger.py resolve-path`: passed; resolved shared live ledger path.
- `python3 scripts/agent_task_ledger.py validate`: passed before append with live `DATA_MISSING` and committed entries=5.
- `python3 scripts/agent_task_ledger.py search --text task_ledger_current_state_refresh_v1_20260623`: passed before append; no matches and live `DATA_MISSING`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/task_ledger_current_state_refresh_v1_20260623.md`: passed after lane adjustment.
- `python3 scripts/agent_task_ledger.py validate --entry-file reports/agent_jobs/task_ledger_current_state_refresh_v1_20260623/ledger/LEDGER_ENTRY.json`: passed.
- `python3 scripts/agent_task_ledger.py append --entry-file reports/agent_jobs/task_ledger_current_state_refresh_v1_20260623/ledger/LEDGER_ENTRY.json --fill-identity`: passed; live ledger path written.
- `python3 scripts/agent_task_ledger.py export-summary --write`: passed; committed ledger markdown and JSONL exported from live entries=1 after the initial append.
- Final `python3 scripts/agent_task_ledger.py append --entry-file reports/agent_jobs/task_ledger_current_state_refresh_v1_20260623/ledger/LEDGER_ENTRY.json --fill-identity`: passed; appended latest `done` state.
- Final `python3 scripts/agent_task_ledger.py export-summary --write`: passed; committed ledger markdown and JSONL exported from live raw entries=2.
- `python3 scripts/agent_task_ledger.py validate`: passed after final export with live entries=2 and committed entries=2.
- `python3 scripts/agent_task_ledger.py search --text task_ledger_current_state_refresh_v1_20260623`: passed after export; live and committed matches found.
- `python3 scripts/agent_task_ledger.py summarize --format markdown`: passed after export.

## Final Gate

- JSON parse generated JSON files: passed for
  `reports/agent_jobs/task_ledger_current_state_refresh_v1_20260623/ledger/LEDGER_ENTRY.json`,
  `reports/agent_jobs/task_ledger_current_state_refresh_v1_20260623/diff-check.json`,
  and `docs/agent_registry/task_ledger/LEDGER.jsonl`.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/task_ledger_current_state_refresh_v1_20260623.md --no-write-report`: passed; no disallowed files.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/task_ledger_current_state_refresh_v1_20260623.md --repo-root .`: passed during pre-commit working-tree validation; wrote `diff-check.json` for the non-ignored changed files. Report bundle artifacts were validated separately with `check-report-artifacts` and force-added for preservation.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/task_ledger_current_state_refresh_v1_20260623.md`: passed; all listed report artifacts exist and are non-empty.
- Product/runtime/extraction/data path guard: passed by changed-path review; only
  task-card, ledger/status docs, and report bundle files changed.
- Post-commit code-review check, `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/task_ledger_current_state_refresh_v1_20260623.md --repo-root .`: passed with a clean working tree. The post-commit empty changed-file output was not retained over the pre-commit evidence artifact.
- PR branch diff review against `origin/migration/clean-runtime-baseline-reconstruct-v1`: passed; 14 changed files, all under task-card allowlist.
- Live PR #392 check after push: draft open, `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`, `lint-and-test` success, and `scan` success.
