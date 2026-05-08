---
job_id: evaluation_task_cards_preservation_20260508
lane: Evaluation
owner: Claude
allowed_files:
  - docs/agent_tasks/evaluation_task_cards_preservation_20260508.md
  - docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md
  - docs/agent_tasks/metric_extraction_current_state_audit_v1.md
  - docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md
  - reports/agent_jobs/remaining_task_cards_classification_audit_20260508/**
  - reports/agent_jobs/evaluation_task_cards_preservation_20260508/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1200
output_dir: reports/agent_jobs/evaluation_task_cards_preservation_20260508
mutation_mode: safe_extension
production_data_access: false
---

# Task

Preserve only:
1. The remaining-task-cards classification audit task card.
2. The remaining-task-cards classification audit report bundle.
3. The two high-value Evaluation task cards:
   - metric_extraction_current_state_audit_v1
   - metric_extraction_runtime_contract_reconciliation_v1
4. This preservation task card and its report bundle.
