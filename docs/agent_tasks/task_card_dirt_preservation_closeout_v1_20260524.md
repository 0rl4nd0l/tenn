---
job_id: task_card_dirt_preservation_closeout_v1_20260524
lane: Reporting
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/task_card_dirt_preservation_closeout_v1_20260524
allowed_files:
  - docs/agent_tasks/task_card_dirt_preservation_closeout_v1_20260524.md
  - reports/agent_jobs/task_card_dirt_preservation_closeout_v1_20260524/
  - docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md
  - reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/
  - docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/
  - docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md
  - reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/
  - docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/
  - docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md
  - reports/agent_jobs/cockpit_ui_usefulness_current_head_reapply_v1_20260521/
  - docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md
  - reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521/
  - docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md
  - reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521/
  - docs/agent_tasks/fresh_session_repo_state_proof_v1_20260524.md
  - reports/agent_jobs/fresh_session_repo_state_proof_v1_20260524/
  - docs/agent_tasks/task_card_dirt_classification_audit_v1_20260524.md
  - reports/agent_jobs/task_card_dirt_classification_audit_v1_20260524/
  - docs/agent_tasks/runtime_topology_reconciliation_impl_v1_20260524.md
  - reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/
  - reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/README.md
  - reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/diff-check.json
  - reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/status.json
  - reports/agent_jobs/cockpit_ui_usefulness_current_head_reapply_v1_20260521/README.md
  - reports/agent_jobs/cockpit_ui_usefulness_current_head_reapply_v1_20260521/diff-check.json
  - reports/agent_jobs/cockpit_ui_usefulness_current_head_reapply_v1_20260521/status.json
  - reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521/README.md
  - reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521/diff-check.json
  - reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521/README.md
  - reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521/diff-check.json
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/README.md
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/diff-check.json
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/status.json
  - reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/validation.json
  - reports/agent_jobs/fresh_session_repo_state_proof_v1_20260524/README.md
  - reports/agent_jobs/fresh_session_repo_state_proof_v1_20260524/status.json
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/README.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/blocking_file_classification.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/diff-check.json
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/phase3g_unblock_options.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/preflight.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/recommendation.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/status.json
  - reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/README.md
  - reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/diff-check.json
  - reports/agent_jobs/runtime_topology_reconciliation_audit_v1_20260522/status.json
  - reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/README.md
  - reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/diff-check.json
  - reports/agent_jobs/task_card_dirt_classification_audit_v1_20260524/README.md
  - reports/agent_jobs/task_card_dirt_classification_audit_v1_20260524/status.json
  - reports/agent_jobs/task_card_dirt_preservation_closeout_v1_20260524/README.md
  - reports/agent_jobs/task_card_dirt_preservation_closeout_v1_20260524/diff-check.json
  - reports/agent_jobs/task_card_dirt_preservation_closeout_v1_20260524/status.json
---

# Task
Preserve the classified loose task-card/report evidence so shared-checkout overlap gates stop failing on untracked repo-hygiene artifacts.

# Context
The classification audit found current HEAD is `e170f6b255ca4229462d4167861775e82ea3df34` and all seven dirty task cards are untracked with corresponding report directories. Two additional untracked cards are the fresh-session proof card and classification card. This task is preservation/closeout only.

# Allowed work
- Validate this task card.
- Run registry list-active and check-overlap.
- Confirm the allowed task cards and report directories exist.
- Stage and commit only the allowed task cards and their allowed report directories.
- Do not change report content unless a JSON file is invalid and a metadata-only correction is required; report before correcting.
- After commit, rerun:
  - git status --short --untracked-files=all -- docs/agent_tasks reports/agent_jobs
  - python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/fresh_session_repo_state_proof_v1_20260524.md
  - git diff --check
  - python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/task_card_dirt_preservation_closeout_v1_20260524.md if supported

# Forbidden
Do not:
- edit product/runtime/backend/Cockpit code
- remove or archive any task card
- delete files
- merge/cherry-pick
- touch Tenn DB/Qdrant/news/memory/financial-truth stores
- start services
- install dependencies
- issue tokens
- access production data
- touch trading/paper/live execution
- make any runtime topology or mountpoint change

# Commit
If validation is clean and only allowed files are staged:
Commit subject:
chore(reporting): preserve repo hygiene task-card evidence

# Required report
Write README.md and status.json under output_dir with:
- Confirmed
- Inferred
- DATA_MISSING
- branch / HEAD before and after
- files staged/committed
- exact commit hash if created
- validation results
- post-commit overlap result for fresh-session repo proof
- remaining dirty/untracked files
- collision risk after closeout
- next safe step
- /save recommendation
