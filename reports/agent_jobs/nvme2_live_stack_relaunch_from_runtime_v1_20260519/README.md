# NVMe2 Live Stack Relaunch From Runtime - 2026-05-19

## Confirmed Facts

- Task card created and contract-validated:
  `docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md`.
- Runtime root exists and resolves to:
  `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `/home/l4nd0/tenn` was not repointed and still resolves to:
  `/mnt/hdd-data/home/l4nd0/tenn`.
- `/mnt/tenn-nvme2` is mounted:
  `/dev/nvme0n1p1 on /mnt/tenn-nvme2 type ext4 (rw,noatime)`.
- Branch:
  `migration/clean-runtime-baseline-reconstruct-v1`.
- HEAD:
  `5dd7ee84b49e`.
- Supported relaunch command used:
  `scripts/cockpit reboot full` from `/home/l4nd0/tenn-runtime`.
- Supported detached frontend restart used after the foreground Next.js process was tied to the Codex PTY:
  `scripts/cockpit kill root`, then `scripts/cockpit start new` from `/home/l4nd0/tenn-runtime`.
- `:8000` is listening.
- `:8081` is listening.
- Frontend PID:
  `169855`.
- Frontend cwd:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/cockpit-ui`.
- Backend compose labels now point to the NVMe runtime baseline:
  - config: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/docker-compose.yml`
  - working dir: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2`
  - env file: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.env.docker`
- Backend Docker mounts have no `/home/l4nd0/tenn` or `/mnt/hdd-data` source paths.
- Backend `/data` mount source:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data -> /data`.
- Backend `/reports` mount source:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports -> /reports`.
- Backend `/workspace` mount source:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1 -> /workspace`.
- Backend `/workspace/reports` mount source:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports -> /workspace/reports`.
- `GET http://127.0.0.1:8000/api/health` returned:
  `{"status":"ok"}`.
- `GET http://127.0.0.1:8081/api/cockpit/home` returned HTTP 200 with:
  `ok=true`, `data_state=PARTIAL`, and explicit `data_missing` entries.
- Direct backend `GET http://127.0.0.1:8000/api/cockpit/home` returned HTTP 404.
- Direct backend `GET http://127.0.0.1:8000/api/news/status` returned HTTP 404.
- Those direct backend 404s are expected for this branch; `/api/cockpit/home` is a frontend BFF route here.

## Inferred Facts

- Tenn is now live from the intended NVMe runtime baseline for the requested backend/frontend stack criteria.
- The relaunch did not require editing Docker Compose, scripts, symlinks, source code, databases, Qdrant, memory, or data.
- `scripts/start_full_stack.sh` rewrote existing `.env.docker` keys to their current values during startup, but `git diff` showed no file content changes afterward.
- The original empty `cockpit_reboot_full.log` came from a detached background launch attempt that exited without touching the old live stack. The subsequent direct `scripts/cockpit reboot full` was the effective relaunch attempt.

## DATA_MISSING

- `sudo ss -ltnp | rg ':8000|:8081'` could not run non-interactively:
  `sudo: a terminal is required to read the password`.
  Plain `ss -ltnp` provided the visible listener evidence.
- The registry job was not claimed because `check-overlap` was blocked by pre-existing untracked route-audit card dirt:
  `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md`.
- Registry release therefore returned `active job not found`.
- External secrets still inject:
  `TENN_RESEARCH_MEMORY_ROOT=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory`.
  This is not a Docker mount source and was not edited due the task constraints. If research-memory routing is in scope for a future relaunch definition, it needs a separate secrets-only task.
- Container env still has `DATA_ROOT=./data`, but the actual container `/data` mount source is the required NVMe2 target.

## Commands Run

- `pwd`
- `readlink -f /home/l4nd0/tenn`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `findmnt /mnt/tenn-nvme2 || true`
- `df -h /mnt/tenn-nvme2 /mnt/hdd-data || true`
- `sudo ss -ltnp | rg ':8000|:8081' || true`
- `ss -ltnp | rg ':8000|:8081' || true`
- `docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Ports}}'`
- `docker inspect fe_backend --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'`
- `docker inspect fe_backend --format 'config={{index .Config.Labels "com.docker.compose.project.config_files"}} working_dir={{index .Config.Labels "com.docker.compose.project.working_dir"}} env_file={{index .Config.Labels "com.docker.compose.project.environment_file"}}'`
- `scripts/cockpit reboot full`
- `scripts/cockpit kill root`
- `setsid -f bash -lc 'cd /home/l4nd0/tenn-runtime && exec scripts/cockpit start new >> reports/agent_jobs/nvme2_live_stack_relaunch_from_runtime_v1_20260519/cockpit_start_new_detached.log 2>&1' </dev/null`
- `ps -fp 169855`
- `readlink -f /proc/169855/cwd`
- `curl -fsS http://127.0.0.1:8000/api/health`
- `curl -i http://127.0.0.1:8081/api/cockpit/home | head -40`
- `curl -i http://127.0.0.1:8000/api/cockpit/home | head -20 || true`
- `curl -i http://127.0.0.1:8000/api/news/status | head -20 || true`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md --no-write-report`
- `python3 scripts/agent_job_registry.py release nvme2_live_stack_relaunch_from_runtime_v1_20260519`
- `python3 scripts/agent_job_registry.py list-active`

## Old Live Service Map

- `/home/l4nd0/tenn -> /mnt/hdd-data/home/l4nd0/tenn`.
- Old frontend:
  - PID: `109739`
  - command: `next-server (v16.2.0)`
  - cwd: `/mnt/hdd-data/home/l4nd0/tenn/cockpit-ui`
  - listener: `*:8081`
- Old backend:
  - container: `fe_backend`
  - compose config: `/home/l4nd0/tenn/financial-engine_v2/docker-compose.yml`
  - compose working dir: `/home/l4nd0/tenn/financial-engine_v2`
  - representative mounts:
    - `/home/l4nd0/tenn/financial-engine_v2/backend -> /app`
    - `/home/l4nd0/tenn/financial-engine_v2/data -> /data`
    - `/home/l4nd0/tenn/reports -> /workspace/reports`
    - `/home/l4nd0/tenn -> /workspace`

## New Live Service Map

- Frontend:
  - PID: `169855`
  - command: `next-server (v16.2.0)`
  - cwd: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/cockpit-ui`
  - listener: `*:8081`
- Backend:
  - container: `fe_backend`
  - compose config: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/docker-compose.yml`
  - compose working dir: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2`
  - listener: `0.0.0.0:8000`
- Supporting containers:
  - `fe_worker`
  - `fe_gpu_worker`
  - `fe_qdrant`
  - `fe_postgres`
- Llama server:
  - PID: `160535`
  - command path: `/home/l4nd0/tenn-runtime/tools/llama.cpp/build-cuda/bin/llama-server`
  - model dir: `/mnt/tenn-nvme2/tenn/models`
  - listener: `0.0.0.0:8001`

## Backend Container Mounts

Key mounts:

- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1 -> /workspace`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/backend -> /app`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/shared -> /app/shared`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/cockpit -> /app/cockpit`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/config -> /config`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/scripts -> /scripts`
- `/mnt/tenn-nvme2/tenn/financial-engine_v2/data -> /data`
- `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports -> /reports`
- `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports -> /workspace/reports`
- `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports -> /workspace-reports`

No backend mount source matched `/home/l4nd0/tenn`, `/home/l4nd0/tenn/*`, or `/mnt/hdd-data/*`.

## Health And Home Smoke Results

- Backend health:
  - HTTP 200
  - body: `{"status":"ok"}`
- Frontend Home BFF:
  - HTTP 200
  - body includes `ok=true`
  - body includes `data_state=PARTIAL`
  - `DATA_MISSING` entries are explicit and non-fatal.
- Backend direct `/api/cockpit/home`:
  - HTTP 404
  - expected on this branch.
- Backend direct `/api/news/status`:
  - HTTP 404
  - expected on this branch.

## NVMe2 Live Verdict

YES: Tenn is now live from the NVMe runtime baseline for the requested live stack criteria:

- frontend cwd is the clean NVMe runtime worktree;
- backend compose labels point to the clean NVMe runtime worktree;
- backend `/data` and `/reports` mount sources are the intended `/mnt/tenn-nvme2` targets;
- backend health passes;
- frontend Home BFF returns HTTP 200;
- direct backend aggregate route 404s are expected.

Residual caveat: one external secrets env variable still references the HDD research-memory path, but it is not a backend Docker mount source and was not changed under this task.

## Final Git Status

`git status --short --untracked-files=all`:

```text
?? docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md
?? docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md
```

The route-parity card was pre-existing route-audit dirt and was not touched.

## Registry Release Status

- `check-overlap`: blocked by pre-existing untracked route-audit card outside this task card's allowed files.
- `release`: not released because no active registry claim existed for this job.
- `list-active`: no active jobs.

## Project Memory Save Recommendation

Save a project-memory note that the controlled relaunch from `/home/l4nd0/tenn-runtime` succeeded on 2026-05-19, with live frontend PID/cwd and backend mounts proving NVMe runtime root plus NVMe2 `/data` and `/reports`. Also save the residual follow-up that `TENN_RESEARCH_MEMORY_ROOT` in `/home/l4nd0/.config/tenn/tenn-secrets.env` still points at HDD and should be handled only in a separate secrets task if it matters.
