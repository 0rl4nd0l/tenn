---
task_id: nvme2_live_stack_relaunch_from_runtime_v1_20260519
job_id: nvme2_live_stack_relaunch_from_runtime_v1_20260519
lane: Evaluation
owner: Codex
status: completed
mutation_mode: safe_extension
production_data_access: false
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
created_at: "2026-05-19"
allowed_files:
  - docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md
  - reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/
output_dir: reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519
---

# NVMe2 Live Stack Relaunch From Runtime

## Goal

Stop the currently running HDD-backed Tenn live stack and relaunch the backend
and Cockpit frontend from the intended NVMe runtime baseline:

`/home/l4nd0/tenn-runtime`

## Scope

This is a controlled live relaunch task. Runtime process/container state may be
changed only through existing repository-supported commands from
`/home/l4nd0/tenn-runtime`.

No source code, Docker Compose files, scripts, symlinks, `.env` files, databases,
Qdrant state, memory files, data files, or existing reports may be edited.

## Allowed Files

- `docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md`
- `reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/`

## Required Preflight

- `pwd`
- `readlink -f /home/l4nd0/tenn`
- `readlink -f /home/l4nd0/tenn-runtime`
- `cd /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `findmnt /mnt/tenn-nvme2 || true`
- `df -h /mnt/tenn-nvme2 /mnt/hdd-data || true`
- `sudo ss -ltnp | rg ':8000|:8081' || true`
- `docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}'`
- `docker inspect fe_backend --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' || true`

## Required Action

1. From `/home/l4nd0/tenn-runtime`, identify the repo-supported command for a
   full Cockpit/backend restart.
2. Stop the current HDD-backed backend/frontend services using the supported
   script only.
3. Relaunch backend/frontend from `/home/l4nd0/tenn-runtime` using the supported
   script only.
4. Do not manually edit paths or symlinks.
5. If supported scripts force `/home/l4nd0/tenn` or HDD paths, stop and report.

## Hard Stops

- Stop if `/home/l4nd0/tenn-runtime` is missing.
- Stop if `/mnt/tenn-nvme2` is not mounted.
- Stop if git status in `/home/l4nd0/tenn-runtime` shows unexpected source dirt
  outside known route-audit artifacts and this task card/report output.
- Stop if scripts force `/home/l4nd0/tenn` or HDD paths.
- Stop if relaunch would require editing compose/scripts/symlinks.
- Stop if services fail health after one supported relaunch attempt.
- Stop if Docker mounts still resolve to `/mnt/hdd-data` after relaunch.

## Validation

- `:8000` is listening.
- `:8081` is listening.
- The frontend PID cwd resolves to an NVMe runtime path.
- Backend Docker mounts use `/home/l4nd0/tenn-runtime` or
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`, not
  `/home/l4nd0/tenn`.
- Backend `/data` resolves to the intended NVMe2 data target.
- Backend `/reports` resolves to the intended NVMe2 reports target.
- `GET /api/health` passes.
- Frontend `GET /api/cockpit/home` returns 200.
- Backend direct `/api/cockpit/home` 404 is acceptable and expected.
- Backend `/api/news/status` 404 is acceptable and expected.

## Report

Write the final report to:

`reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/README.md`
