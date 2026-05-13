# Runtime Topology NVMe Enablement

verdict: partial

## Branch / HEAD / Worktree

- execution branch: `fast/dev-storage-v1-20260513-170304`
- execution HEAD before source edits: `c8e0c00808cb52daa31df22cdeeb41f6c8d50d45`
- milestone commit subject: `milestone(evaluation): enable nvme runtime router path`
- execution worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- original preserve worktree: `/mnt/hdd-data/home/l4nd0/tenn`
- original preserve branch: `preserve/dirty-work-20260430T065748Z`

## Task Card Status

- Preserve task card created first at `docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md`.
- Validation initially failed because the repo schema requires `timeout_seconds`; added `timeout_seconds: 7200`.
- Preserve `check-overlap` was blocked by unrelated untracked task cards outside this job's `allowed_files`.
- Same task card was created in the clean NVMe worktree.
- NVMe task-card validation: `ok: true`.
- NVMe `check-overlap`: `ok: true`.

## Registry Claim / Release Status

- `list-active` before claim: `active_jobs: []`.
- Claim from NVMe worktree: `ok: true`.
- Heartbeats were refreshed while the Docker build ran.
- Release: `ok: true`.
- `list-active` after release: `active_jobs: []`.

## Contract / Collision Declaration

- Lane: Evaluation
- Execution mode: SAFE EXTENSION
- Collision risk: MEDIUM
- Contested surfaces touched: none
- Target system layer: runtime topology around backend/Cockpit/llama.cpp launch paths.
- Relevant contract rules: backend remains sole authority; Cockpit remains client/orchestration only; retrieval, storage, extraction, financial truth, memory stores, source labels, model weights, and model presets were not changed.

## Files Changed

Tracked/visible source artifacts:
- `docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md`
- `scripts/start_config.env`
- `reports/agent_jobs/runtime_topology_nvme_enablement_v1_20260513/README.md`
- `reports/agent_jobs/runtime_topology_nvme_enablement_v1_20260513/diff-check.json`
- `reports/agent_jobs/runtime_topology_nvme_enablement_v1_20260513/status.json`

Ignored runtime artifacts created in the NVMe worktree:
- `cockpit-ui/node_modules`
- `financial-engine_v2/.env.docker`

No product application logic, DB/Qdrant data/config, memory stores, extraction logic, model config/presets, source PDFs, Cockpit feature code, marketplace code, QueryOrchestrator, chat routes, or provenance/source-label logic were modified.

## Launcher Change

`scripts/start_config.env` now points the full-stack launcher at the NVMe worktree:

- `ENGINE_ROOT="/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2"`
- `COMPOSE_FILE="$ENGINE_ROOT/docker-compose.yml"`

It also exports:

- `LLAMA_SERVER_BIN="/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server"`

Reason: the NVMe worktree does not contain `tools/llama.cpp/build-cuda/bin/llama-server`; the shared HDD binary is valid and documented while the process CWD is NVMe.

## Dependency Strategy Used

- Frontend: installed NVMe-local ignored dependencies with `pnpm --dir cockpit-ui install --frozen-lockfile`.
- Backend: did not create `financial-engine_v2/.venv`; Docker compose was the intended backend path.
- llama.cpp: used the shared HDD binary through `LLAMA_SERVER_BIN`; runtime process CWD is NVMe.
- Compose env: `scripts/start_full_stack.sh` created `financial-engine_v2/.env.docker` from `.env.example` and wrote launcher feature flags.
- Backend/Cockpit Docker build became too broad and was interrupted: the cold image build spent ~32 minutes in `pip install -r /app/requirements.txt`, pulling large CUDA/PyTorch/docling/browser/news dependencies and entering resolver work. This triggered the task hard stop for broad dependency setup.

## Rollback Plan

If rollback to the previous HDD-rooted runtime is required:

1. Stop NVMe-launched services:
   - `cd /home/l4nd0/tenn-fast-dev-storage-v1 && scripts/cockpit kill root`
   - `cd /home/l4nd0/tenn-fast-dev-storage-v1 && scripts/cockpit kill backend`
   - `cd /home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2 && docker compose --env-file .env.docker -f docker-compose.yml down`
2. Restore HDD-backed llama/router:
   - `cd /mnt/hdd-data/home/l4nd0/tenn && LLAMA_SERVER_BIN=/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server setsid -f bash -lc 'cd /mnt/hdd-data/home/l4nd0/tenn && exec bash scripts/run_llama_server.sh >>/tmp/llama-server-8001.log 2>&1 </dev/null'`
3. Restore HDD-backed backend/Cockpit if needed:
   - `cd /mnt/hdd-data/home/l4nd0/tenn && scripts/cockpit restart backend`
   - `cd /mnt/hdd-data/home/l4nd0/tenn && scripts/cockpit start new`
4. Re-run health probes for `:8000`, `:8001`, and `:8081`.

Rollback used: no full rollback. The backend/Cockpit build attempt was interrupted cleanly. The llama router was intentionally left running from the NVMe worktree because it is healthier than the no-router state during the blocked Docker build and satisfies the NVMe CWD target for `:8001`.

## Before Process CWD / Root

| Service | PID | CWD | Root | Result |
| --- | ---: | --- | --- | --- |
| backend `:8000` | DATA_MISSING | DATA_MISSING | DATA_MISSING | no listener |
| llama router `:8001` | 3334861 | `/mnt/hdd-data/home/l4nd0/tenn` | `/` | HDD-rooted |
| llama child | 3336701 | `/mnt/hdd-data/home/l4nd0/tenn` | `/` | HDD-rooted |
| Cockpit `:8081` | DATA_MISSING | DATA_MISSING | DATA_MISSING | no listener |
| extraction `:8002` | DATA_MISSING | DATA_MISSING | DATA_MISSING | no listener |

## After Process CWD / Root

| Service | PID | CWD | Root | Result |
| --- | ---: | --- | --- | --- |
| backend `:8000` | DATA_MISSING | DATA_MISSING | DATA_MISSING | no listener |
| llama router `:8001` | 3601291 | `/home/l4nd0/tenn-fast-dev-storage-v1` | `/` | NVMe worktree CWD, shared HDD binary |
| Cockpit `:8081` | DATA_MISSING | DATA_MISSING | DATA_MISSING | no listener |
| extraction `:8002` | DATA_MISSING | DATA_MISSING | DATA_MISSING | no listener |

## Runtime Now Serves From NVMe?

| Service | NVMe-backed now? | Evidence |
| --- | --- | --- |
| backend `:8000` | no | offline; Docker build blocked before backend start |
| llama.cpp `:8001` | yes, process CWD only | PID 3601291 CWD `/home/l4nd0/tenn-fast-dev-storage-v1`; binary is shared HDD path by explicit config |
| Cockpit Next.js `:8081` | no | offline; backend/Cockpit start blocked by broad Docker build |
| extraction `:8002` | no | intentionally not started; remains offline |

## Health Probe Table

Before:

| Endpoint | Result | Latency | data_state |
| --- | --- | ---: | --- |
| `http://127.0.0.1:8000/api/health` | connection refused | 0.000122s | DATA_MISSING |
| `http://127.0.0.1:8001/health` | 200 | 0.000263s | DATA_MISSING |
| `http://127.0.0.1:8001/v1/models` | 200 | 0.000541s | DATA_MISSING |
| `http://127.0.0.1:8081/api/cockpit/health` | connection refused | 0.000110s | DATA_MISSING |
| `http://127.0.0.1:8081/api/cockpit/home` | connection refused | 0.000125s | DATA_MISSING |

After:

| Endpoint | Result | Latency | data_state |
| --- | --- | ---: | --- |
| `http://127.0.0.1:8000/api/health` | connection refused | 0.000131s | DATA_MISSING |
| `http://127.0.0.1:8001/health` | 200 | 0.000298s | DATA_MISSING |
| `http://127.0.0.1:8001/v1/models` | 200 | 0.000601s | DATA_MISSING |
| `http://127.0.0.1:8081/api/cockpit/health` | connection refused | 0.000144s | DATA_MISSING |
| `http://127.0.0.1:8081/api/cockpit/home` | connection refused | 0.000124s | DATA_MISSING |

## Docker Compose Volume Preservation Evidence

- Compose root basename remains `financial-engine_v2`.
- Named volumes still exist:
  - `financial-engine_v2_fe_pgdata`
  - `financial-engine_v2_fe_qdrant`
- Volume mountpoints from `docker volume inspect`:
  - `/mnt/nvme/docker/volumes/financial-engine_v2_fe_pgdata/_data`
  - `/mnt/nvme/docker/volumes/financial-engine_v2_fe_qdrant/_data`
- `docker ps -a` after interruption showed no containers.
- No `docker compose down -v`, `docker volume rm`, or volume replacement command was run.

## Validation Run

- `bash scripts/gpu_process_guard.sh --check`: exit code 0.
- `ss -ltnp '( sport = :8000 or sport = :8001 or sport = :8081 or sport = :8002 )'`: only `:8001` listening.
- `/proc` process CWD/root table captured before and after.
- Health probes captured before and after with bounded `curl -m 5`.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md`: `ok: true`.
- `python3 scripts/agent_job_registry.py release runtime_topology_nvme_enablement_v1_20260513`: `ok: true`.
- `python3 scripts/agent_job_registry.py list-active`: `active_jobs: []`.

## Commands Run

- `date -Iseconds`
- `pwd`
- `readlink -f /home/l4nd0/tenn`
- `readlink -f /home/l4nd0/tenn-fast-dev-storage-v1`
- `git -C /home/l4nd0/tenn-fast-dev-storage-v1 rev-parse --show-toplevel`
- `git -C /home/l4nd0/tenn-fast-dev-storage-v1 branch --show-current`
- `git -C /home/l4nd0/tenn-fast-dev-storage-v1 rev-parse HEAD`
- `git -C /home/l4nd0/tenn-fast-dev-storage-v1 status --short --untracked-files=all`
- `git worktree list`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md`
- `bash scripts/gpu_process_guard.sh --check`
- `ss -ltnp '( sport = :8000 or sport = :8001 or sport = :8081 or sport = :8002 )'`
- process CWD/root inspection through `/proc`
- bounded `curl` probes for `:8000`, `:8001`, and `:8081`
- `pnpm --dir cockpit-ui install --frozen-lockfile --lockfile-only`
- `pnpm --dir cockpit-ui install --frozen-lockfile`
- `scripts/cockpit reboot`
- `setsid -f bash -lc 'cd /home/l4nd0/tenn-fast-dev-storage-v1 && source scripts/start_config.env && exec bash scripts/run_llama_server.sh >>/tmp/llama-server-8001.log 2>&1 </dev/null'`
- `kill -INT -3577536`
- `docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'`
- `docker volume ls`
- `docker volume inspect financial-engine_v2_fe_pgdata financial-engine_v2_fe_qdrant`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md`
- `python3 scripts/agent_job_registry.py release runtime_topology_nvme_enablement_v1_20260513`

## DATA_MISSING

- Backend NVMe process root: DATA_MISSING because backend did not start.
- Cockpit NVMe process root: DATA_MISSING because Cockpit did not start.
- `/api/cockpit/home` `data_state`: DATA_MISSING because `:8081` was offline before and after.
- Complete backend/Cockpit NVMe runtime enablement: DATA_MISSING until a narrower backend image/dependency strategy is provided or the cold Docker image build is allowed to finish.

## Final Git Status

NVMe worktree:

```text
clean after milestone commit, aside from ignored runtime artifacts
```

Preserve worktree:

```text
?? docs/agent_tasks/current_state_collision_runtime_remediation_audit_v1_20260513.md
?? docs/agent_tasks/nvme_hot_dev_base_sync_v1_20260513.md
?? docs/agent_tasks/overview_home_audit_closeout_blocker_classification_v1_20260513.md
?? docs/agent_tasks/overview_home_wiring_completion_audit_v1_20260513.md
?? docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md
```

Reports and `.env.docker` are ignored by repo exclude rules unless force-added.

## Files Intentionally Not Touched

- product application logic
- QueryOrchestrator
- chat routes
- provenance/source-label logic
- memory cleanup code or company_memory.sqlite
- Qdrant data/config
- Postgres data
- news stores
- extraction prompts/parsers/gold labels
- model weights/config/presets
- source PDFs
- Cockpit UI feature code
- marketplace code
- `:8002`

## Remaining Blockers

1. Backend/Cockpit NVMe enablement needs a narrower dependency path than a cold `docker compose up -d --build` of the full backend/worker image, or explicit approval to let that broad build finish.
2. The NVMe worktree still lacks a local llama.cpp build artifact; current safe path uses the shared HDD binary with NVMe CWD.
3. Preserve checkout has unrelated untracked task-card drafts that block preserve-side task-card overlap checking.

## Next Safe Step

Use the existing Docker image/cache without `--build`, or prebuild the backend image in a separate explicit dependency task, then run NVMe compose startup from `/home/l4nd0/tenn-fast-dev-storage-v1` and validate `:8000`/`:8081`. Keep the current `:8001` router as-is unless a rollback to HDD-rooted CWD is explicitly required.

## Project Memory Save Recommendation

Save that `runtime_topology_nvme_enablement_v1_20260513` partially enabled the NVMe runtime path for llama.cpp only: `scripts/start_config.env` in `/home/l4nd0/tenn-fast-dev-storage-v1` points `ENGINE_ROOT` at the NVMe worktree and exports a documented shared HDD `LLAMA_SERVER_BIN`; `:8001` runs with NVMe CWD. Backend/Cockpit remained blocked because cold Docker build dependency setup was too broad and was interrupted during backend image `pip install`.
