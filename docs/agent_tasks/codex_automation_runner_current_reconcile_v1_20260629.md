---
job_id: codex_automation_runner_current_reconcile_v1_20260629
lane: Query Orchestration
supporting_lanes:
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/codex_automation_runner_current_reconcile_v1_20260629.md
  - docs/dev/automation_index.md
  - scripts/codex_automation_runner.py
  - scripts/test_codex_automation_runner.py
  - systemd/user/tenn-codex-automation-health.service
  - systemd/user/tenn-codex-automation-health.timer
  - systemd/user/tenn-codex-bug-regression.service
  - systemd/user/tenn-codex-bug-regression.timer
  - systemd/user/tenn-codex-daily-closeout.service
  - systemd/user/tenn-codex-daily-closeout.timer
  - systemd/user/tenn-codex-doc-drift.service
  - systemd/user/tenn-codex-doc-drift.timer
  - systemd/user/tenn-codex-extraction-regression.service
  - systemd/user/tenn-codex-extraction-regression.timer
  - systemd/user/tenn-codex-future-opportunities.service
  - systemd/user/tenn-codex-future-opportunities.timer
  - systemd/user/tenn-codex-memory-drift.service
  - systemd/user/tenn-codex-memory-drift.timer
  - systemd/user/tenn-codex-repo-hygiene.service
  - systemd/user/tenn-codex-repo-hygiene.timer
  - reports/agent_jobs/codex_automation_runner_current_reconcile_v1_20260629/README.md
  - reports/agent_jobs/codex_automation_runner_current_reconcile_v1_20260629/status.json
  - reports/agent_jobs/codex_automation_runner_current_reconcile_v1_20260629/diff-check.json
approval_required: false
timeout_seconds: 2400
output_dir: reports/agent_jobs/codex_automation_runner_current_reconcile_v1_20260629
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Codex Automation Runner Current Reconcile

## Scope

Adopt the validated Jun 7 Codex automation runner mainline-port commit onto the
current canonical branch, then harden the runner so a failed Codex child process
still writes an explicit failure report when `--output-last-message` does not.

## Safety Boundary

- Repo writes are limited to this task card, the automation runner, focused
  runner tests, repo-local user-systemd templates, automation index docs, and
  this report bundle.
- The runner must keep Codex jobs audit/proposal-only and use the Codex
  read-only sandbox.
- This task must not install, enable, start, stop, restart, reload, or edit
  live user-systemd units.
- This task must not run live automation jobs except dry-runs that write only to
  temporary output roots.
- This task must not mutate GitHub issues or PRs.
- This task must not write product runtime, DBs, Qdrant, Redis, news stores,
  memory stores, source PDFs, gold labels, canonical financial truth, model/GPU
  config, runtime state, service state, or production data.
- Sloppy Fix and Sloppy scan workflows are out of scope.

## Validation

- Validate this task card.
- Run `python3 -m unittest scripts/test_codex_automation_runner.py`.
- Run `python3 scripts/codex_automation_runner.py list`.
- Run focused dry-runs using a temporary `TENN_CODEX_AUTOMATION_OUTPUT_ROOT`.
- Run `python3 -m py_compile scripts/codex_automation_runner.py scripts/test_codex_automation_runner.py`.
- Run `XDG_RUNTIME_DIR=/run/user/$(id -u) systemd-analyze verify --user` for
  repo-local `systemd/user/tenn-codex-*` templates if available.
- Run `git diff --check`.
- Run `python3 scripts/agent_job_contract.py check-diff <this task card>
  --no-write-report`.
