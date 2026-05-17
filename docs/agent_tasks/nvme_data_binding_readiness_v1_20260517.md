---
job_id: nvme_data_binding_readiness_v1_20260517
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme_data_binding_readiness_v1_20260517.md
  - reports/agent_jobs/nvme_data_binding_readiness_v1_20260517/
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/nvme_data_binding_readiness_v1_20260517
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit the data/runtime bindings required for frontend and backend launched from the isolated clean baseline to use populated Tenn data. Do not move or mutate data.

# Hard boundaries

- Do not move/copy/delete data.
- Do not edit docker-compose.yml.
- Do not edit env files.
- Do not create symlinks.
- Do not stop/start/restart services.
- Do not mutate DBs, Qdrant, news stores, PDFs, models, caches, memory stores, or gold labels.
- Do not integrate deferred commits.
- Do not claim launch-ready unless evidence proves populated data binding.
