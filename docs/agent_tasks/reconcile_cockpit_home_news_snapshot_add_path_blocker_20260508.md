---
job_id: reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md
  - docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md
  - reports/agent_jobs/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508
  - reports/agent_jobs/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508/README.md
  - reports/agent_jobs/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508/local_blocking_task_card_backup.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1200
output_dir: reports/agent_jobs/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508
mutation_mode: safe_extension
production_data_access: false
---

# Reconcile Cockpit Home News Snapshot Add-Path Blocker

## Scope

Audit and, only if safe, reconcile the local untracked task-card artifact blocking a fast-forward merge of `integrate/cockpit-home-news-snapshot-v1-20260508`.

## Blocking File

- `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`

## Integration Candidate

- Branch: `integrate/cockpit-home-news-snapshot-v1-20260508`
- Commit: `c0549d754cb501254873b34c66d9aec7d12b95d8`

## Constraints

- Do not touch code directly.
- Do not touch reports except this job report.
- Do not touch unrelated untracked files.
- Stop on active registry overlap, unclassifiable local task-card content, non-fast-forward merge, unexpected overwritten untracked files, unexpected merge file set, or hook failures outside known import issues.
