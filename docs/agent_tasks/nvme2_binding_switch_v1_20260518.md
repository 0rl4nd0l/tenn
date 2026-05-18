---
job_id: nvme2_binding_switch_v1_20260518
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme2_binding_switch_v1_20260518.md
  - reports/agent_jobs/nvme2_binding_switch_v1_20260518/
  - scripts/start_config.env
  - financial-engine_v2/docker-compose.yml
approval_required: false
timeout_seconds: 2400
output_dir: reports/agent_jobs/nvme2_binding_switch_v1_20260518
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Switch Tenn runtime binding from temporary hybrid storage to full NVMe2 data/report paths.

# Hard boundaries

- Do not delete source HDD data.
- Do not use rsync --delete.
- Do not copy full data again.
- Do not mutate DB/Qdrant/news/PDF/model stores.
- Do not run ingestion/backfill/extraction/import jobs.
- Do not integrate deferred commits.
- Do not edit backend/frontend source code.
- Do not rename Docker named volumes.
- Do not launch broad workers/schedulers.
- Do not claim final runtime success until validation/smoke proves it.
