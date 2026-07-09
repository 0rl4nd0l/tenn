# Validation

## Completed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md`
  - exit status: 0
  - result: task card valid
- `python3 -m unittest scripts.test_automation_github_dedupe scripts.test_automation_candidate_store`
  - exit status: 0
  - result: 15 tests passed
- `python3 scripts/automation_github_dedupe.py --help`
  - exit status: 0
  - result: CLI help printed
- `python3 scripts/automation_github_dedupe.py check --repo 0rl4nd0l/tenn --title "Add automation candidate store layer" --root-cause "candidate state suppression" --label state:ready --json`
  - exit status: 0
  - result: `duplicate_pr` for PR #492 by exact title; labels did not filter
    the search query
- `python3 scripts/automation_github_dedupe.py check --repo 0rl4nd0l/tenn --title "Automation candidate store" --root-cause "candidate state suppression" --label state:ready --json`
  - exit status: 0
  - result: `needs_review` for PR #492 by token overlap; no automatic duplicate
- `python3 -m py_compile scripts/automation_github_dedupe.py scripts/automation_candidate_store.py scripts/test_automation_github_dedupe.py`
  - exit status: 0
  - result: compile check passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md`
  - exit status: 0
  - result: changed files are within `allowed_files`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md`
  - first parallel run exit status: 1
  - first result: `diff-check.json` was checked before the parallel
    `check-diff` command finished writing it
  - rerun exit status: 0
  - rerun result: required report artifacts exist
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md`
  - exit status: 0
  - result: closeout check passed
- `git diff --check`
  - exit status: 0
  - result: no tracked-diff whitespace errors
- code-reviewer pass
  - result: no critical findings, warnings, or suggestions after review fixes

## Pending

- final `git status --short --untracked-files=all`
- branch push and draft PR creation
