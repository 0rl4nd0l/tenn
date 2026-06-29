# Worker/GPU Worker Git Provenance Env Parity V1

## Summary

Resolved GitHub issue #142 by wiring `worker` and `gpu_worker` in `financial-engine_v2/docker-compose.yml` with the same git provenance environment keys already present on `backend`.

## Scope

- Added `TENN_GIT_HEAD`, `TENN_GIT_HEAD_SHORT`, `TENN_GIT_BRANCH`, `TENN_GIT_DIRTY`, `TENN_GIT_STATUS_LINE_COUNT`, and `TENN_BUILD_TIME` to `worker`.
- Added the same provenance keys to `gpu_worker`.
- Preserved commands, queues, volumes, env files, dependencies, model/GPU settings, and runtime behavior.
- Did not start, stop, restart, recreate, or inspect containers as a runtime mutation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md`
- `docker compose -f financial-engine_v2/docker-compose.yml config --quiet` was attempted in the isolated worktree and blocked because untracked `financial-engine_v2/.env.docker` is absent there.
- `docker compose --project-directory /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2 -f /home/l4nd0/tenn-provenance-worker-git-env-parity-v1-20260531/financial-engine_v2/docker-compose.yml config --quiet`
- `python3 -c "import yaml; ..."` static env-key parity check for `backend`, `worker`, and `gpu_worker`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/worker_gpu_worker_git_provenance_env_parity_v1_20260531.md`

## Runtime Refresh

No runtime refresh was performed. Existing containers must be recreated by an approved runtime/operator task before `docker inspect` can show the new environment keys in live container metadata.

## Evidence

- Diff gate: `reports/agent_jobs/worker_gpu_worker_git_provenance_env_parity_v1_20260531/diff-check.json`
