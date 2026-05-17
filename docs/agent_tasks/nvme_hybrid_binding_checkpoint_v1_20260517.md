---
job_id: nvme_hybrid_binding_checkpoint_v1_20260517
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme_hybrid_binding_checkpoint_v1_20260517.md
  - reports/agent_jobs/nvme_hybrid_binding_checkpoint_v1_20260517/
  - docs/agent_tasks/nvme_hybrid_runtime_data_binding_v1_20260517.md
  - reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/
  - scripts/start_config.env
  - financial-engine_v2/docker-compose.yml
approval_required: false
timeout_seconds: 1200
output_dir: reports/agent_jobs/nvme_hybrid_binding_checkpoint_v1_20260517
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Checkpoint the completed hybrid runtime data binding changes so launch smoke can run from a clean worktree.

# Hard boundaries

- Do not start services.
- Do not stop services.
- Do not copy/move/delete data.
- Do not mutate DBs, Qdrant, news stores, PDFs, models, caches, or memory stores.
- Do not integrate deferred commits.
- Do not edit files outside allowed_files.
- Do not alter the hybrid binding logic unless needed to fix task-card/report formatting.
