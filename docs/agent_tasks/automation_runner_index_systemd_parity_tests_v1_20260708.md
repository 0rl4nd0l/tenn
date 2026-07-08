---
job_id: automation_runner_index_systemd_parity_tests_v1_20260708
lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/automation_runner_index_systemd_parity_tests_v1_20260708
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/automation_runner_index_systemd_parity_tests_v1_20260708.md
  - docs/dev/automation_index.md
  - scripts/test_codex_automation_runner.py
  - reports/agent_jobs/automation_runner_index_systemd_parity_tests_v1_20260708/README.md
  - reports/agent_jobs/automation_runner_index_systemd_parity_tests_v1_20260708/STATE.md
  - reports/agent_jobs/automation_runner_index_systemd_parity_tests_v1_20260708/VALIDATION.md
  - reports/agent_jobs/automation_runner_index_systemd_parity_tests_v1_20260708/diff-check.json
---

# Automation Runner Index Systemd Parity Tests V1

## Objective

Add safe repo-side parity tests that fail when the Codex automation runner job
registry, `docs/dev/automation_index.md` timer table, and `systemd/user`
templates drift apart.

## Approval

USER_APPROVED: Orlando requested the safe repo-side follow-up task to add
parity tests before touching live timers. Live `daily-closeout` install and
stale automation worktree reconciliation require separate approval.

## Scope

- Extend the existing focused automation runner tests.
- Compare registered runner jobs with automation-index timer rows.
- Compare registered runner jobs with repo systemd service/timer templates.
- Ensure service templates call the matching runner job.
- Keep the task entirely repo-side and test-only outside report artifacts.

## Out Of Scope

- No edits to live user systemd files under `/home/l4nd0/.config/systemd/user`.
- No `systemctl` mutation, daemon reload, timer enable/start/stop/restart, or
  installed timer changes.
- No edits to `/home/l4nd0/tenn-codex-automations-v1-20260516`.
- No stale worktree preservation, cleanup, parking, merge, delete, reset,
  rebase, stash, or prune operations.
- No runtime, DB, Qdrant, Redis, news-store, memory-store, source-PDF,
  extraction prompt, gold-label, backfill, Docker, service, model/GPU, or secret
  mutation.
- No GitHub issue, PR, label, comment, close, reopen, merge, push, or branch
  cleanup.
- Durable docs edits are limited to `docs/dev/automation_index.md` only when
  the new parity tests prove the current index is inconsistent with the runner.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_runner_index_systemd_parity_tests_v1_20260708.md`
- `python3 -m unittest scripts.test_codex_automation_runner`
- `python3 scripts/codex_automation_runner.py list`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_runner_index_systemd_parity_tests_v1_20260708.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_runner_index_systemd_parity_tests_v1_20260708.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_runner_index_systemd_parity_tests_v1_20260708.md`
- `git diff --check`
- `git status --short --untracked-files=all`
