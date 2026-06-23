---
job_id: control_plane_task_ledger_status_refresh_v1_20260623
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/control_plane_task_ledger_status_refresh_v1_20260623
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/control_plane_task_ledger_status_refresh_v1_20260623.md
  - docs/agent_registry/task_ledger/LEDGER.jsonl
  - docs/agent_registry/task_ledger/LEDGER.md
  - docs/agent_registry/task_ledger/README.md
  - docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - reports/agent_jobs/control_plane_task_ledger_status_refresh_v1_20260623/STATE.md
  - reports/agent_jobs/control_plane_task_ledger_status_refresh_v1_20260623/VALIDATION.md
  - reports/agent_jobs/control_plane_task_ledger_status_refresh_v1_20260623/CODE_REVIEW.md
  - reports/agent_jobs/control_plane_task_ledger_status_refresh_v1_20260623/PR_REVIEW.md
  - reports/agent_jobs/control_plane_task_ledger_status_refresh_v1_20260623/diff-check.json
---

# Control Plane Task Ledger Status Refresh

## Objective

Refresh the committed Agent Task Ledger snapshot for the current control-plane
PR state after PR #386, while preserving the live ledger as `DATA_MISSING` when
the resolved live ledger file is absent.

## Scope

- Control-plane ledger/docs/report artifacts only.
- Use verified GitHub PR state for PR #380, #382, #383, #385, and #386.
- Do not mutate the live registry/ledger path when it is missing.

## Hard Boundaries

- Do not touch greyhound runtime.
- Do not touch Tenn product, runtime, data, extraction implementation,
  count-24, source-PDF, gold-label, prompt, service, DB, Qdrant, Redis, news,
  memory, model, GPU, or host-global files.
- Do not add new visible skills.
- Keep visible skill count at 10.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_task_ledger_status_refresh_v1_20260623.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py resolve-path`
- `python3 scripts/agent_task_ledger.py validate`
- `python3 scripts/agent_task_ledger.py summarize --format markdown`
- `python3 scripts/agent_task_ledger.py validate --entry-file docs/agent_registry/task_ledger/LEDGER.jsonl`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_task_ledger_status_refresh_v1_20260623.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_task_ledger_status_refresh_v1_20260623.md --repo-root .`
- Product/runtime/data/extraction/count-24 path guard.
- Host-global path guard.

## Definition Of Done

- Committed ledger snapshot records current merged control-plane PR state.
- `CONTROL_PLANE_OPEN_WORK.md` no longer says the committed ledger snapshot is
  empty.
- `CONTROL_PLANE_STATUS.md` reflects the current live-ledger `DATA_MISSING`
  state and committed snapshot status.
- Report bundle preserves validation and `DATA_MISSING` evidence.
