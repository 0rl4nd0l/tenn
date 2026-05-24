---
job_id: docker_builder_cache_broad_prune_v1_20260524
title: Docker builder cache broad prune
lane: Evaluation
supporting_lanes:
  - Runtime/Ops
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/docker_builder_cache_broad_prune_v1_20260524.md
  - reports/agent_jobs/docker_builder_cache_broad_prune_v1_20260524/
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/docker_builder_cache_broad_prune_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Docker Builder Cache Broad Prune

## Objective

Run the approved broad Docker builder-cache prune only, then verify Tenn runtime health and root disk recovery.

## Mode

`SAFE IMPLEMENTATION / DISK RELIEF`

## Allowed Mutation

Only this Docker cleanup command is allowed:

```bash
docker builder prune --force --all
```

Optional dry-run and inspection commands are allowed. Report artifacts may be written only under:

- `reports/agent_jobs/docker_builder_cache_broad_prune_v1_20260524/`

## Forbidden

- no `docker system prune`
- no `docker system prune -a`
- no `docker volume prune`
- no `docker container prune`
- no `docker image prune`
- no `docker rm`
- no `docker rmi`
- no `docker compose down`
- no service restarts unless health is broken and user approval is obtained
- no `rm -rf`
- no `git clean`
- no worktree prune
- no model deletion or move
- no `/tenn` cleanup
- no `/mnt` cleanup
- no data, report, DB, Qdrant, news, or memory mutation
- no dependency or lockfile changes
- no source code edits other than this task card and report artifacts

## Required Preflight

- `pwd`
- `readlink -f /home/l4nd0/tenn`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short --untracked-files=all`
- `python3 scripts/agent_job_registry.py list-active` if available
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/docker_builder_cache_broad_prune_v1_20260524.md` if available
- claim if safe
- `df -hT /`
- `docker ps --format '{{.Names}} {{.Image}} {{.Status}}'`
- `docker system df`
- `docker system df -v > reports/agent_jobs/docker_builder_cache_broad_prune_v1_20260524/docker-system-df-before.txt`
- `curl -fsS http://127.0.0.1:8000/api/health || true`
- `curl -fsS http://127.0.0.1:8081/api/cockpit/health || true`
- `ss -ltnp 'sport = :8001' || true`
- `nvidia-smi || true`

## Hard Stops

- Docker daemon unavailable.
- Backend, Cockpit, or llama already unhealthy before cleanup.
- Active registry job overlaps Docker, runtime, or Repo Hygiene surfaces.
- Any command would prune volumes, containers, images, source files, worktrees, models, or data.
- Root filesystem free space is already healthy enough and Docker build cache no longer reports meaningful reclaimable space.
- The prune command prompts or indicates it will remove more than build cache.

## Implementation

Run exactly:

```bash
docker builder prune --force --all
```

Capture output to:

- `reports/agent_jobs/docker_builder_cache_broad_prune_v1_20260524/docker-builder-prune-output.txt`

## Post-Validation

- `df -hT /`
- `docker system df`
- `docker system df -v > reports/agent_jobs/docker_builder_cache_broad_prune_v1_20260524/docker-system-df-after.txt`
- `docker ps --format '{{.Names}} {{.Image}} {{.Status}}'`
- `curl -fsS http://127.0.0.1:8000/api/health`
- `curl -fsS http://127.0.0.1:8081/api/cockpit/health`
- `ss -ltnp 'sport = :8001'`
- `nvidia-smi`
- `git diff --check`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/docker_builder_cache_broad_prune_v1_20260524.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/docker_builder_cache_broad_prune_v1_20260524.md`
- final `git status --short --untracked-files=all`
- registry release and final list-active

## Report

Write:

- `reports/agent_jobs/docker_builder_cache_broad_prune_v1_20260524/README.md`

Include confirmed facts, inferred facts, `DATA_MISSING`, root disk before and after, Docker system df before and after, exact prune command run, exact space reclaimed according to Docker, actual root free-space change, runtime health before and after, backend/Cockpit/llama/GPU status after, warnings, final git status, registry release/list-active, recommendation whether root disk pressure is resolved or still needs non-Docker audit, and Project Memory save recommendation.
