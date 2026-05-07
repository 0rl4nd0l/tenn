---
job_id: marketplace_recency_final_promotion_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/marketplace_recency_final_promotion_v1.md
  - reports/agent_jobs/marketplace_recency_final_promotion_v1/README.md
  - reports/agent_jobs/marketplace_recency_final_promotion_v1/status.json
  - reports/agent_jobs/marketplace_recency_final_promotion_v1/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/marketplace_recency_final_promotion_v1
mutation_mode: safe_extension
production_data_access: false
---

# Marketplace Recency Final Promotion V1

Promotion-only task to fast-forward `preserve/dirty-work-20260430T065748Z` to the already-validated `integrate/marketplace-recency-current-target-v1` branch only if the current target branch remains an ancestor of the integration branch and dirty worktree files do not overlap the promoted files.
