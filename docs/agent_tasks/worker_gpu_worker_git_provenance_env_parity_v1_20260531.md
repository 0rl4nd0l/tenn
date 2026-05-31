---
job_id: worker_gpu_worker_git_provenance_env_parity_v1_20260531
lane: Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md
  - reports/agent_jobs/worker_gpu_worker_git_provenance_env_parity_v1_20260531/
  - reports/agent_jobs/worker_gpu_worker_git_provenance_env_parity_v1_20260531/README.md
  - reports/agent_jobs/worker_gpu_worker_git_provenance_env_parity_v1_20260531/status.json
  - reports/agent_jobs/worker_gpu_worker_git_provenance_env_parity_v1_20260531/validation.json
  - reports/agent_jobs/worker_gpu_worker_git_provenance_env_parity_v1_20260531/diff-check.json
  - financial-engine_v2/docker-compose.yml
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/worker_gpu_worker_git_provenance_env_parity_v1_20260531
mutation_mode: safe_extension
production_data_access: false
---

# Worker/GPU Worker Git Provenance Env Parity V1

Resolve GitHub issue #142 by wiring the worker and GPU worker compose services with the same git provenance environment keys already exposed by the backend service.

## Scope

- Add the backend `TENN_GIT_*` and `TENN_BUILD_TIME` environment entries to `worker`.
- Add the backend `TENN_GIT_*` and `TENN_BUILD_TIME` environment entries to `gpu_worker`.
- Preserve existing worker queues, commands, env files, volumes, dependencies, and runtime behavior.
- Do not start, stop, restart, or recreate containers in this task.

## Forbidden

- No production DB/Qdrant/news/memory writes.
- No canonical financial truth, parser routing, extraction prompt, or gold-label changes.
- No broad runtime topology changes.
- No service start/stop/restart/recreate.
- No secrets, `.env`, or credential changes.
- No unrelated dirty work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md`
- Compose static validation if available.
- Static diff proving backend, worker, and GPU worker expose the same provenance env keys.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md`
