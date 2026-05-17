---
job_id: nvme_isolated_partial_baseline_reconstruct_v1_20260517
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme_isolated_partial_baseline_reconstruct_v1_20260517.md
  - reports/agent_jobs/nvme_isolated_partial_baseline_reconstruct_v1_20260517/
  - docs/agent_tasks/nvme_required_conflict_resolution_v1_20260517.md
  - reports/agent_jobs/nvme_required_conflict_resolution_v1_20260517/
  - scripts/load_news_to_qdrant.py
  - scripts/test_load_news_qdrant_preflight.py
  - reports/agent_jobs/memory_integrity_audit_guard_v1_20260516/diff-check.json
  - reports/agent_jobs/memory_integrity_audit_guard_v1_20260516/status.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 2400
output_dir: reports/agent_jobs/nvme_isolated_partial_baseline_reconstruct_v1_20260517
mutation_mode: safe_extension
production_data_access: false
---

# Task

Create an isolated clean worktree for the NVMe migration baseline and reconstruct/checkpoint only the safe partial integration from the dirty worktree.
