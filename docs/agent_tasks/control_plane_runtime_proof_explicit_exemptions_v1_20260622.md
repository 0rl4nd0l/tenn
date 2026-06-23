---
job_id: control_plane_runtime_proof_explicit_exemptions_v1_20260622
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/control_plane_runtime_proof_explicit_exemptions_v1_20260622
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/control_plane_runtime_proof_explicit_exemptions_v1_20260622.md
  - scripts/agent_job_contract.py
  - scripts/test_agent_job_contract.py
  - scripts/test_agent_job_hook.py
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - reports/agent_jobs/control_plane_runtime_proof_explicit_exemptions_v1_20260622/DESIGN.md
  - reports/agent_jobs/control_plane_runtime_proof_explicit_exemptions_v1_20260622/STATE.md
  - reports/agent_jobs/control_plane_runtime_proof_explicit_exemptions_v1_20260622/VALIDATION.md
  - reports/agent_jobs/control_plane_runtime_proof_explicit_exemptions_v1_20260622/CODE_REVIEW.md
  - reports/agent_jobs/control_plane_runtime_proof_explicit_exemptions_v1_20260622/PR_REVIEW.md
  - reports/agent_jobs/control_plane_runtime_proof_explicit_exemptions_v1_20260622/diff-check.json
---

# Control Plane Runtime Proof Explicit Exemptions

## Objective

Tighten the Runtime Functionality Proof closeout gate so runtime-like task
cards are exempt only when they explicitly declare report-only, docs-only, or
control-plane-only closeout scope.

## Scope

- Control-plane validation and hook tests only.
- Preserve the PR #385 Runtime Functionality Proof gate.
- Update operator docs with the explicit exemption declaration format.

## Hard Boundaries

- Do not touch greyhound runtime.
- Do not touch Tenn product, runtime, data, extraction implementation,
  count-24, source-PDF, gold-label, prompt, service, DB, Qdrant, Redis, news,
  memory, model, GPU, or host-global files.
- Do not add new visible skills.
- Keep visible skill count at 10.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_runtime_proof_explicit_exemptions_v1_20260622.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py resolve-path`
- `python3 scripts/agent_task_ledger.py validate`
- Focused pytest for `scripts/test_agent_job_contract.py` and
  `scripts/test_agent_job_hook.py`.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_runtime_proof_explicit_exemptions_v1_20260622.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_runtime_proof_explicit_exemptions_v1_20260622.md --repo-root .`
- Product/runtime/data/extraction/count-24 path guard.
- Host-global path guard.

## Definition Of Done

- Runtime-like task cards that merely mention control-plane, report-only, or
  docs-only text no longer bypass proof.
- Explicit `closeout_scope` metadata and equivalent explicit closeout-scope
  body lines still exempt report-only, docs-only, and control-plane-only cards.
- Missing Runtime Functionality Proof keeps `DONE` blocked for runtime-like
  task cards.
- No forbidden runtime/product/data/extraction/count-24 or host-global files
  are changed.
