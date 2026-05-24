---
job_id: task_card_dirt_classification_audit_v1_20260524
lane: Reporting
owner: Codex
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/task_card_dirt_classification_audit_v1_20260524
allowed_files:
  - docs/agent_tasks/task_card_dirt_classification_audit_v1_20260524.md
  - reports/agent_jobs/task_card_dirt_classification_audit_v1_20260524/
---

# Task
Classify dirty task-card files currently blocking overlap checks in `/home/l4nd0/tenn`. Do not clean, stage, remove, commit, merge, cherry-pick, or modify the dirty task cards.

# Context
The fresh-session repo proof task now validates, and registry `list-active` reports no active jobs. It remains blocked because `check-overlap` reports seven dirty task-card files outside the current task allowlist.

Dirty task-card files to classify:
- docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md
- docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md
- docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md
- docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md
- docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md
- docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md
- docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md

# Required preflight
- Confirm symlink-resolved repo path:
  `/home/l4nd0/tenn` -> `/home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Validate this task card.
- Run registry list-active.
- Run check-overlap for this task card.
- Run `git status --short --untracked-files=all -- docs/agent_tasks`
- For each of the seven files:
  - present/missing
  - tracked/untracked/modified/deleted
  - first ~80 lines or metadata summary
  - apparent lane
  - apparent purpose
  - whether it has a corresponding report path
  - whether it appears superseded, duplicate, active, or stale
  - recommended action: preserve / commit under separate task / archive / remove only after approval / leave alone
  - risk if left dirty

# Allowed writes
Only:
- this task card
- report artifacts under `reports/agent_jobs/task_card_dirt_classification_audit_v1_20260524/`

# Forbidden
Do not:
- modify any of the seven dirty task cards
- stage anything
- remove anything
- commit anything
- merge/cherry-pick
- clean worktree
- edit product/runtime/backend/Cockpit files
- touch Tenn DB/Qdrant/news/memory/financial-truth stores
- start services
- install dependencies
- issue tokens
- access production data
- touch trading/paper/live execution

# Required report
Write README.md and status.json with:
- Confirmed
- Inferred
- DATA_MISSING
- branch / HEAD
- registry state
- exact dirty task-card statuses
- per-file classification table
- recommended handling order
- collision risk after classification
- whether the original fresh-session repo proof can resume after approved handling
- `/save` recommendation
