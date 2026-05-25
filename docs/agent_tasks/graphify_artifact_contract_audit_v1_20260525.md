---
job_id: graphify_artifact_contract_audit_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/graphify_artifact_contract_audit_v1_20260525.md
  - reports/agent_jobs/graphify_artifact_contract_audit_v1_20260525/README.md
  - reports/agent_jobs/graphify_artifact_contract_audit_v1_20260525/status.json
  - reports/agent_jobs/graphify_artifact_contract_audit_v1_20260525/graphify_contract_matrix.json
  - reports/agent_jobs/graphify_artifact_contract_audit_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/graphify_artifact_contract_audit_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit GitHub #67: Graphify artifact contract audit v1.

# Scope

Classify whether missing `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` indicate stale instructions, missing generation workflow, ignored artifacts, or an actual contract breach.

# Hard Boundaries

- Do not generate Graphify artifacts.
- Do not edit AGENTS, CLAUDE, architecture docs, code, scripts, runtime config, data stores, or generated graph outputs.
- Mutate only this task card and the listed report artifacts.

# Required Outputs

- AGENTS/CLAUDE/SYSTEM_CONTRACT references to Graphify.
- Expected artifact paths and observed artifact status.
- Whether generation tooling exists.
- Whether artifacts are ignored, untracked, external, or absent.
- Recommended contract update or child generation task.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release, JSON validation, `git diff --check`, and task-card check-diff.
