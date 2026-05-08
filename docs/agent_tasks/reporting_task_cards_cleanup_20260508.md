---
job_id: reporting_task_cards_cleanup_20260508
lane: Reporting
owner: Claude
allowed_files:
  - docs/agent_tasks/reporting_task_cards_cleanup_20260508.md
  - docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md
  - docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md
  - docs/agent_tasks/preserve_baseline_failure_classification_20260508.md
  - docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md
  - reports/agent_jobs/reporting_task_cards_cleanup_20260508/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/reporting_task_cards_cleanup_20260508
mutation_mode: safe_extension
production_data_access: false
---

# Task

Classify and safely resolve the four remaining Reporting/Cockpit dirty task-card artifacts. Do not touch source code or runtime files.
