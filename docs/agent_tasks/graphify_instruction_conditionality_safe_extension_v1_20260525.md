---
job_id: graphify_instruction_conditionality_safe_extension_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/graphify_instruction_conditionality_safe_extension_v1_20260525.md
  - AGENTS.md
  - CLAUDE.md
  - reports/agent_jobs/graphify_instruction_conditionality_safe_extension_v1_20260525/README.md
  - reports/agent_jobs/graphify_instruction_conditionality_safe_extension_v1_20260525/status.json
  - reports/agent_jobs/graphify_instruction_conditionality_safe_extension_v1_20260525/validation.json
  - reports/agent_jobs/graphify_instruction_conditionality_safe_extension_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/graphify_instruction_conditionality_safe_extension_v1_20260525
mutation_mode: safe_extension
production_data_access: false
---

# Task

Implement the safe docs child task recommended by `graphify_artifact_contract_audit_v1_20260525`.

# Scope

Update the Graphify agent-instruction wording in `AGENTS.md` and `CLAUDE.md` so missing ignored `graphify-out/` artifacts are handled as `DATA_MISSING` instead of a literal required precondition.

# Hard Boundaries

- Do not generate, refresh, commit, or inspect generated `graphify-out/` artifacts beyond absence checks.
- Do not run `graphify update`.
- Do not add a new Graphify runbook in this task.
- Do not touch backend, frontend, runtime, config, service, DB, Qdrant, news, memory, extraction, financial-truth, or provenance implementation files.
- Mutate only this task card, `AGENTS.md`, `CLAUDE.md`, and listed report artifacts.

# Required Outputs

- Conditional Graphify wording in `AGENTS.md`.
- Conditional Graphify wording in `CLAUDE.md`.
- Report artifacts under `reports/agent_jobs/graphify_instruction_conditionality_safe_extension_v1_20260525/`.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release, Graphify absence checks, content inspection, JSON validation, `git diff --check`, and task-card check-diff.
