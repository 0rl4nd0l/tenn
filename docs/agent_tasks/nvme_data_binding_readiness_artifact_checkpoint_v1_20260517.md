---
job_id: nvme_data_binding_readiness_artifact_checkpoint_v1_20260517
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme_data_binding_readiness_artifact_checkpoint_v1_20260517.md
  - docs/agent_tasks/nvme_data_binding_readiness_v1_20260517.md
  - reports/agent_jobs/nvme_data_binding_readiness_v1_20260517/
  - reports/agent_jobs/nvme_data_binding_readiness_artifact_checkpoint_v1_20260517/
approval_required: false
timeout_seconds: 900
output_dir: reports/agent_jobs/nvme_data_binding_readiness_artifact_checkpoint_v1_20260517
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Checkpoint the prior data-binding readiness audit task card/report artifacts so they no longer block the next migration implementation task.

# Hard boundaries

- Do not edit runtime/data config.
- Do not edit docker-compose.yml.
- Do not edit scripts/start_config.env.
- Do not move/copy/delete data.
- Do not stop/start/restart services.
- Do not mutate DBs, Qdrant, news stores, PDFs, models, caches, memory stores, or gold labels.
- Do not touch files outside allowed_files.
- Do not proceed to populated-data binding implementation in this task.
