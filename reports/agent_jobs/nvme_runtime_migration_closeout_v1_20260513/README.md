# NVMe Runtime Migration Closeout

## Final verdict
partial

## Branch / HEAD
- Branch: `fast/dev-storage-v1-20260513-170304`
- HEAD: `0d5dbcd30357`

## Scope and files changed
- Runtime/launcher/test scope touched in this closeout:
  - `scripts/cockpit`
  - `scripts/start_config.env`
  - `scripts/start_full_stack.sh`
- Report file:
  - `reports/agent_jobs/nvme_runtime_migration_closeout_v1_20260513/README.md`
- Unrelated modified files left untouched:
  - `cockpit-ui/app/globals.css`
  - `cockpit-ui/app/layout.tsx`

## Commit
- Commit hash (if committed): 51e2dd2

## Preflight checks
- `git branch --show-current`: `fast/dev-storage-v1-20260513-170304`
- `git rev-parse --short=12 HEAD`: `0d5dbcd30357`
- `python3 scripts/agent_job_registry.py list-active`
  - `{"active_jobs":[], "registry_scope":"shared", "ok":true}`
- Listeners on 8000/8001/8081/8002 from `ss`:
  - `LISTEN ... 0.0.0.0:8001 ... llama-server`
  - `LISTEN ... 0.0.0.0:8000 ...`
  - `LISTEN *:8081 ... next-server (v1)`
  - No active listener on `:8002`

## Runtime validation
- `curl -sS http://127.0.0.1:8000/api/health`
  - Response status: `200`
  - Body starts with `{"status":"healthy","services":[...` and includes healthy backend, llama, ollama, qdrant, redis, cockpit_service, gpu, host
- `curl -sS http://127.0.0.1:8001/health`
  - Response: `{"status":"healthy","services":[...],"responseTimeMs":7.4}` for local llama runtime
- `curl -sS http://127.0.0.1:8001/v1/models`
  - Response status: `200`
  - Notable paths:
    - `/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-APEX-I-Compact.gguf`
    - `/mnt/nvme/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf`
    - `/mnt/nvme/tenn/models/Qwen3.5-35B-A3B-Q4_K_M.gguf`
    - `/mnt/nvme/tenn/models/...qwen3.5...` (NVMe-backed aliases)
    - `model:gpt-oss-20b` points at `/mnt/ssd/log/ssd_data/l4nd0_cache/.cache/llmfit/models/gpt-oss-20b-mxfp4.gguf`
- `curl -sS http://127.0.0.1:8081/api/cockpit/health`
  - Response: `{"status":"healthy","ok":true,"service":"cockpit-ui"}`
- `curl -m 30 -sS -w '\nHTTP %{http_code} time %{time_total}\n' http://127.0.0.1:8081/api/cockpit/home`
  - Response code: `200`
  - Time: `0.017208`
  - Body present with `data_state` values, including known data_missing entries (`news`, `market_movers`, home narrative producers)

## Runtime inventory
- `docker compose -f financial-engine_v2/docker-compose.yml --env-file financial-engine_v2/.env.docker ps`
  - `fe_backend` `financial-engine_v2-backend` Up
  - `fe_gpu_worker` `financial-engine_v2-gpu_worker` Up
  - `fe_postgres` `postgres:16` Up (healthy)
  - `fe_qdrant` `qdrant/qdrant:latest` Up
  - `fe_redis` `redis:7` Up
  - `fe_worker` `financial-engine_v2-worker` Up
- `docker images | rg -P 'financial-engine_v2-(backend|worker|gpu_worker|fe_beat)'`
  - `financial-engine_v2-backend:latest`
  - `financial-engine_v2-fe_beat:latest`
  - `financial-engine_v2-gpu_worker:latest`
  - `financial-engine_v2-worker:latest`
- `docker volume inspect financial-engine_v2_fe_pgdata financial-engine_v2_fe_qdrant`
  - `financial-engine_v2_fe_pgdata` mountpoint `/mnt/nvme/docker/volumes/financial-engine_v2_fe_pgdata/_data`
  - `financial-engine_v2_fe_qdrant` mountpoint `/mnt/nvme/docker/volumes/financial-engine_v2_fe_qdrant/_data`

## NVMe / HDD backed status
- Backend/runtime:
  - Core compose volumes are on NVMe mountpoints as above.
  - Backend service health checks are healthy.
- Llama backend:
  - `llama-server` process and model registry use `/mnt/nvme/tenn/models/...` for the runtime migration aliases.
  - One model alias (`model:gpt-oss-20b`) remains on `/mnt/ssd/...`, which is an outlier but not currently the active chat model.
- Cockpit UI:
  - Running on host port 8081 with healthy `api/cockpit/health` and `api/cockpit/home`.

## Tests / checks
- `scripts/test_cockpit_launcher_helpers.py`: skipped in this environment (`/usr/bin/python3: No module named pytest`).
- `financial-engine_v2/backend/tests/test_llm_fallback_policy.py`: skipped in this environment (`/usr/bin/python3: No module named pytest`).
- `git diff --check`: clean (no whitespace/trailing-break issues in tracked diffs)

## Final git status (at end of this pass)
- Modified: `cockpit-ui/app/globals.css`, `cockpit-ui/app/layout.tsx`, `scripts/cockpit`, `scripts/start_config.env`, `scripts/start_full_stack.sh`
- Untracked: `docs/agent_tasks/nvme_runtime_build_missing_compose_images_v1_20260513.md`, `docs/agent_tasks/nvme_runtime_taskcard_dirt_closeout_and_gpu_worker_build_v1_20260513.md`, `docs/agent_tasks/runtime_topology_nvme_backend_cockpit_cached_start_v1_20260513.md`

## Remaining blockers
- `pytest` is not installed as `python3` module in this runtime, so requested launcher/backend tests could not be executed here.
- Unrelated cockpit UI font/layout edits are present in working tree and intentionally excluded from this closeout commit.

## Remaining HDD-backed assets
- `model:gpt-oss-20b` remains mapped to `/mnt/ssd/...` in llama registry data.

## Project memory save recommendation
- Keep this report and closeout state in project memory as a successful runtime migration verification artifact, with an open follow-up to install `pytest` in the session and complete the requested test files.
