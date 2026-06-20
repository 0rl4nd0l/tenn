# No-Write Harness Git Status Audit Repair

State: DONE

Repaired the PR #379 code-review finding where `git_status_after` was recorded
but did not affect the no-write side-effect verdict.

Change summary:

- Added git-status path parsing for replay side-effect audits.
- Added `unexpected_git_status_changes` to the audit payload.
- Added forbidden `repo_worktree_write` detection for new non-report-local git
  status rows.
- Preserved report-local artifact writes under the selected report directory.
- Added focused regression tests for both non-report and report-local git status
  changes.

Validation:

- task-card validate: PASS
- red regression before runner fix: FAIL as expected, 1 failure and 1 error
- focused unit tests after runner fix: PASS, 19 tests
- `py_compile`: PASS
- pre-report `check-diff --no-write-report`: PASS
- full `check-diff`: PASS
- report artifact check: PASS
- `git diff --check`: PASS
- repeat read-only review: PASS

Docs Impact Check:

- docs_impact: DOCS_UPDATED
- docs_checked:
  - docs/agent_tasks/extraction_no_write_harness_git_status_audit_repair_v1_20260619.md
- docs_changed:
  - docs/agent_tasks/extraction_no_write_harness_git_status_audit_repair_v1_20260619.md
- docs_followup: NONE
- reason: task card documents the side-effect audit behavior repair.

Model/Worker Routing:

- task_tier: medium
- recommended_model: standard coding model
- actual_model: Codex GPT-5
- worker_model_allowed: false
- worker_decision_limit: no workers used
- escalation_needed: false

Task Ledger:

- live registry preflight: active_jobs empty
- committed ledger: DATA_MISSING on this branch
- ledger update: DATA_MISSING because `scripts/agent_task_ledger.py` is not
  present on this PR branch

Residual facts unchanged:

- WHC remains extraction-red in the saved no-write replay.
- Docling-backed replay remains `DATA_MISSING` until an approved venv exists.
