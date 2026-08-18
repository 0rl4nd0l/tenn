---
job_id: tenn_done_gate_v0_m1_docs_20260629
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Dev Flow
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/tenn_done_gate_v0_m1_docs_20260629
mutation_mode: safe_extension
production_data_access: false
task_scope: docs_only
closeout_scope: docs_only
allowed_files:
  - docs/dev_flow/DONE_GATE_V0.md
  - docs/dev_flow/templates/DONE_GATE_EVIDENCE_PACKET.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/agent_tasks/tenn_done_gate_v0_m1_docs_20260629.md
  - reports/agent_jobs/tenn_done_gate_v0_m1_docs_20260629/README.md
  - reports/agent_jobs/tenn_done_gate_v0_m1_docs_20260629/VALIDATION.md
---

# Tenn Done Gate V0 M1 Docs

## Objective

Promote the report-only Done Gate V0 design into durable Tenn docs and a
reusable closeout evidence-packet template. Do not implement scripts.

Source design:

- `reports/agent_jobs/tenn_done_gate_v0_design_20260629/README.md`
- `reports/agent_jobs/tenn_done_gate_v0_design_20260629/DONE_GATE_CONTRACT.md`
- `reports/agent_jobs/tenn_done_gate_v0_design_20260629/EVIDENCE_PACKET_TEMPLATE.md`
- `reports/agent_jobs/tenn_done_gate_v0_design_20260629/EXAMPLES.md`
- `reports/agent_jobs/tenn_done_gate_v0_design_20260629/IMPLEMENTATION_PLAN.md`
- `reports/agent_jobs/tenn_done_gate_v0_design_20260629/TASK_CARD_DRAFT.md`
- `reports/agent_jobs/tenn_done_gate_v0_design_20260629/RISK_REGISTER.md`

## Scope

Allowed:

- Create `docs/dev_flow/DONE_GATE_V0.md`.
- Create `docs/dev_flow/templates/DONE_GATE_EVIDENCE_PACKET.md`.
- Add a short Done Gate section to `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`.
- Create this task card.
- Create the ignored closeout report files under
  `reports/agent_jobs/tenn_done_gate_v0_m1_docs_20260629/`.

Forbidden:

- Editing `AGENTS.md`.
- Implementing scripts or modifying `scripts/tenn_dev_status.py`.
- Editing `docs/agent_tasks/tenn_dev_status_v0.md`.
- Staging, committing, pushing, opening PRs, mutating GitHub, merging,
  rebasing, resetting, stashing, cleaning, deleting branches, or deleting
  worktrees.
- Installing dependencies or starting services.
- Touching product, runtime, data, extraction, DB, Qdrant, news, memory,
  source-PDF, gold-label, prompt, service, model/GPU, Docker, or secret
  surfaces.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_done_gate_v0_m1_docs_20260629.md`
- `python3 scripts/tenn_dev_status.py`
- `git diff --check -- docs/dev_flow/DONE_GATE_V0.md docs/dev_flow/templates/DONE_GATE_EVIDENCE_PACKET.md docs/dev_flow/CODEX_OPERATOR_GUIDE.md docs/agent_tasks/tenn_done_gate_v0_m1_docs_20260629.md`
- Structural checks confirming:
  - Done Gate contract has required fields.
  - Template has `DONE`, `NOT DONE`, `BLOCKED`, `DATA_MISSING`, and
    `OWNER_DECISION_REQUIRED`.
  - Operator guide mentions Dev Status and Done Gate.
  - Task card `allowed_files` matches the intended tracked and ignored files.
- `git status --short --untracked-files=all`
- Final `python3 scripts/tenn_dev_status.py`

## Closeout Scope

Closeout scope: docs-only.
