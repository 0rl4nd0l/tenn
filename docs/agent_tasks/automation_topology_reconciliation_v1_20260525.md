---
job_id: automation_topology_reconciliation_v1_20260525
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Runtime
  - Query Orchestration
  - Evaluation
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
timeout_seconds: 7200
output_dir: reports/agent_jobs/automation_topology_reconciliation_v1_20260525
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# Automation Topology Reconciliation Audit

Issue: #79.

Mode: audit-only closeout. The expanded allowed-files list exists only so the supervisor batch can validate all report artifacts together; this issue's allowed operational surface remains this task card, its report directory, and GitHub issue metadata after closeout gates.

No installed service, timer, scheduler, product, runtime, or data mutation is allowed.
