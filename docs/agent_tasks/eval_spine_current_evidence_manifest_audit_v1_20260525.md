---
job_id: eval_spine_current_evidence_manifest_audit_v1_20260525
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/eval_spine_current_evidence_manifest_audit_v1_20260525.md
  - reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525/README.md
  - reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525/status.json
  - reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525/report_bundle_inventory.json
  - reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525/evidence_manifest.json
  - reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525/data_missing_map.json
  - reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/eval_spine_current_evidence_manifest_audit_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit GitHub #62: current evidence manifest audit v1.

# Scope

Create a normalized current evidence manifest across current May 25 report bundles so agents can distinguish Confirmed, Inferred, Speculative, and DATA_MISSING states without relying on stale project memory.

# Hard Boundaries

- Audit only.
- No production DB, Qdrant, news, memory, service, ingestion, extraction, reindexing, migration, restart, package install, parser, source-label, UI, or runtime changes.
- Mutate only this task card and the listed report artifacts.

# Required Outputs

- Report bundle inventory.
- Evidence manifest.
- DATA_MISSING map.
- PR/CI status snapshot.
- Report freshness map.
- Recommended next tasks.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release, JSON validation, `git diff --check`, and task-card check-diff.
