---
job_id: long_running_issue_resolution_batch_v1_20260526
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
  - Provenance
  - Query Orchestration
  - Runtime
owner: Codex
allowed_files:
  - docs/agent_tasks/long_running_issue_resolution_batch_v1_20260526.md
  - docs/agent_tasks/automation_topology_reconciliation_v1_20260525.md
  - docs/agent_tasks/nightly_news_observability_systemd_migration_v1_20260525.md
  - docs/agent_tasks/llama_server_8001_ownership_provenance_audit_v1_20260525.md
  - docs/agent_tasks/registry_readonly_no_lock_integration_review_v1_20260526.md
  - reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526/README.md
  - reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526/status.json
  - reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526/issue_matrix.md
  - reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526/followup_map.md
  - reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526/branch_parking_map.md
  - reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526/validation_summary.md
  - reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526/data_missing.md
  - reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526/diff-check.json
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/README.md
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/status.json
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/evidence.md
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/finding_classification.md
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/reviewer_verdict.md
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/closeout_comment.md
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/validation_summary.md
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/data_missing.md
  - reports/agent_jobs/automation_topology_reconciliation_v1_20260525/diff-check.json
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/README.md
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/status.json
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/evidence.md
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/finding_classification.md
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/reviewer_verdict.md
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/closeout_comment.md
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/validation_summary.md
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/data_missing.md
  - reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/diff-check.json
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/README.md
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/status.json
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/evidence.md
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/finding_classification.md
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/reviewer_verdict.md
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/closeout_comment.md
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/validation_summary.md
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/data_missing.md
  - reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/diff-check.json
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/README.md
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/status.json
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/evidence.md
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/finding_classification.md
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/reviewer_verdict.md
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/status_comment.md
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/validation_summary.md
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/data_missing.md
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/diff-check.json
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/long_running_issue_resolution_batch_v1_20260526
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# Long Running Issue Resolution Batch

Supervisor task card for a bounded GitHub-native Tenn issue closeout batch.

## Scope

- Review issues #79, #81, #82, and #85.
- Create report artifacts and per-issue task cards only.
- Add GitHub comments, labels, follow-up issues, or closure actions only when the closeout gates pass.

## Contract

Target system layer: agent/reporting control plane only.

Relevant contract rules: SYSTEM_CONTRACT sections 1, 7, 8, and 10. Backend remains the sole authority; no alternate pipelines, silent fallbacks, or product/runtime mutations are allowed.

What must not change: product/backend/frontend/runtime code, DB/Qdrant/news/memory stores, canonical financial truth, parser routing, extraction prompts, gold labels, model/runtime/GPU/service config, branch cleanup, or unrelated dirty work.

Why safe: the task is limited to report/task-card artifacts and GitHub issue metadata after reviewer gates. It does not spawn, restart, or depend on llama-server; #82 inspects runtime state read-only and uses GPU guard only as a read-only check.

## Validation

- Validate all task cards.
- Run registry list/check-overlap.
- Run report JSON parse checks.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Run GitHub readback for any issues commented, created, or closed.
