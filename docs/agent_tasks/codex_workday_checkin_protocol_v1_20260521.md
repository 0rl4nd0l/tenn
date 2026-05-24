---
job_id: codex_workday_checkin_protocol_v1_20260521
lane: Evaluation
owner: Codex
mutation_mode: audit_only
approval_required: false
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/codex_workday_checkin_protocol_v1_20260521
allowed_files:
  - docs/agent_tasks/codex_workday_checkin_protocol_v1_20260521.md
  - reports/agent_jobs/codex_workday_checkin_protocol_v1_20260521/**
---

# Codex Workday Check-In Protocol

## Objective

Audit the existing local Tenn `tenn-codex-*` automation reports and produce a simple workday check-in protocol after confirming PR #35 removed the scheduled Sloppy Fix risk.

## Scope

- Confirm current repo branch, HEAD, dirty state, worktrees, recent commits, active task card state, registry state, and overlap status.
- Read existing `/home/l4nd0/.codex/automations/tenn/reports/**`.
- Read local user-systemd status for `tenn-codex-*` timers.
- Inspect relevant repo docs/scripts that define the local automation runner.
- Write only this task card and report artifacts under the declared output directory.

## Forbidden

- Do not create a scheduler, daily sentinel, systemd timer, GitHub Action, Codex app automation, or duplicate automation layer.
- Do not run, cancel, disable, delete, or edit GitHub Action settings.
- Do not touch source code, backend runtime, Cockpit UI, parser routing, extraction prompts, canonical financial truth, production databases, Qdrant, news databases, Tenn memory stores, migrations, data copies, reindexing, or backfills.
- Do not touch Strategy Lab or Cockpit UI dirty files.

## Deliverables

- `reports/agent_jobs/codex_workday_checkin_protocol_v1_20260521/README.md`
- `reports/agent_jobs/codex_workday_checkin_protocol_v1_20260521/status.json`

## Validation

- Validate this task card.
- Run registry `list-active` and `check-overlap`.
- Claim and release the registry job if overlap checks pass.
- Run `git diff --check`.
- Run task-card `check-diff` if supported.
- Validate JSON report artifacts.
