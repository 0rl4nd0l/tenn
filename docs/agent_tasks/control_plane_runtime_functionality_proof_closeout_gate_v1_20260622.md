---
job_id: control_plane_runtime_functionality_proof_closeout_gate_v1_20260622
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md
  - scripts/agent_job_contract.py
  - scripts/test_agent_job_contract.py
  - scripts/agent_job_hook.py
  - scripts/test_agent_job_hook.py
  - docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - reports/agent_jobs/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622/DESIGN.md
  - reports/agent_jobs/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622/STATE.md
  - reports/agent_jobs/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622/VALIDATION.md
  - reports/agent_jobs/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622/PR_REVIEW.md
  - reports/agent_jobs/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622/CODE_REVIEW.md
  - reports/agent_jobs/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622/diff-check.json
---

# Control Plane Runtime Functionality Proof Closeout Gate

## Objective

Add a small closeout gate so runtime-like task cards cannot silently close as
`DONE` without Runtime Functionality Proof evidence in their report artifacts,
unless the task explicitly declares report-only or docs-only scope.

## Scope

- Control-plane validation and hook tooling only.
- Focused tests for task-card/report closeout validation.
- Update control-plane docs to describe the new enforcement surface.
- Preserve PR #382 policy/docs behavior; this task adds enforcement on top of
  the existing Runtime Functionality Proof instructions.

## Hard Boundaries

- Do not touch greyhound runtime.
- Do not touch Tenn product, runtime, data, extraction implementation,
  count-24, source-PDF, gold-label, prompt, service, DB, Qdrant, Redis, news,
  memory, model, GPU, or host-global files.
- Do not start services, run backfills, mutate production data, or install
  dependencies.
- Do not widen beyond control-plane task-card/report validation.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py resolve-path`
- `python3 scripts/agent_task_ledger.py validate`
- Focused pytest for agent job contract and hook tests.
- `python3 scripts/check_runtime_functionality_proof_docs.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md --repo-root .`
- Product/runtime/data/extraction/count-24 path guard.
- Host-global path guard.

## Definition Of Done

- Runtime-like task-card closeout/report artifacts fail validation when `DONE`
  appears without Runtime Functionality Proof fields.
- Missing intended live-output proof prevents `DONE`; acceptable statuses are
  `PARTIAL`, `BROKEN`, `DATA_MISSING`, or `DONE_WITH_RISK`.
- Docs-only and report-only control-plane tasks are exempt when explicitly
  declared.
- Stop-hook closeout warnings surface the failure for active runtime-like task
  cards.
- No forbidden runtime/product/data/extraction/count-24 or host-global files
  are changed.
