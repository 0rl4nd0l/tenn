---
job_id: apex_m40_runtime_stability_audit_v1_20260519
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md
  - reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit current APEX/M40 runtime stability and routing after the successful NVMe runtime relaunch.

Do not change model config, runtime config, scripts, services, Docker, CUDA settings, symlinks, data, reports, DBs, Qdrant, memory, or Cockpit UI.

# Context

The live Tenn stack has been relaunched from the NVMe runtime baseline.

Confirmed from recent relaunch report:
- `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- frontend cwd is `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/cockpit-ui`
- backend Docker compose points to the clean NVMe runtime baseline
- backend `/data` and `/reports` mounts point to `/mnt/tenn-nvme2/...`
- backend `/api/health` passes
- frontend `/api/cockpit/home` returns HTTP 200
- backend direct `/api/cockpit/home` and `/api/news/status` 404s are expected for this branch

Current Cockpit UI reports:
- Backend: RUNNING
- Host: RUNNING
- GPU visible: NVIDIA GeForce GT 1030
- Cockpit config route: adaptive
- selected: `model:qwen3.5-35b-a3b-apex`
- active: `model:qwen3.5-35b-a3b-apex`
- routing: `api_preferred`
- profile: `ops`
- Home state: `PARTIAL`, with honest `DATA_MISSING`

Concern:
- APEX appears selected/active, but GPU panel reports GT 1030 rather than M40.
- Prior CUDA/M40 instability means APEX must not be treated as reliable until bounded runtime evidence proves it.

# Required questions

Answer:

1. Is the M40 visible to the host?
2. Is the M40 visible to the llama.cpp/APEX runtime process?
3. Which process is serving `:8001`?
4. What model file is actually loaded by the `:8001` runtime?
5. Is the loaded model actually `qwen3.5-35b-a3b-apex`, or only selected in Cockpit config?
6. Which GPU has VRAM allocated to the llama/APEX process?
7. Is Cockpit reporting GT 1030 because:
   - GT 1030 is the display GPU,
   - M40 is invisible,
   - M40 is visible but idle,
   - status code only reports GPU 0,
   - or DATA_MISSING?
8. Does a small direct runtime smoke succeed?
9. Does a Cockpit chat/API smoke succeed without massive prompt amplification?
10. Are fresh NVIDIA Xid/CUDA errors present after the audit?
11. Should APEX/M40 be classified as reliable, degraded, or not trusted yet?

# Required preflight

Run and report:

- `pwd`
- `readlink -f /home/l4nd0/tenn-runtime`
- `cd /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md`
- registry/list-active if supported
- registry/check-overlap if supported
- claim if safe; otherwise continue report-only if no active conflicting runtime job exists

# Runtime inspection

Read-only commands to run and report:

- `ss -ltnp | rg ':8000|:8001|:8002|:8081' || true`
- `ps -ef | rg 'llama|qwen|apex|8001|8002' | rg -v rg || true`
- `nvidia-smi`
- `nvidia-smi -L`
- `nvidia-smi pmon -c 1 || true`
- `nvidia-smi --query-gpu=index,name,uuid,pci.bus_id,driver_version,memory.total,memory.used,temperature.gpu,utilization.gpu --format=csv`
- `journalctl -k --since "30 minutes ago" | rg -i 'nvrm|xid|cuda|gpu|nvidia' || true`
- `dmesg -T | rg -i 'nvrm|xid|cuda|gpu|nvidia' | tail -80 || true`

If permissions block kernel logs, record DATA_MISSING.

# Process/runtime proof

For the process listening on `:8001`:

- identify PID
- `ps -ww -fp <PID>`
- `readlink -f /proc/<PID>/cwd`
- `tr '\0' '\n' < /proc/<PID>/environ | rg 'CUDA|LLAMA|MODEL|APEX|QWEN|PORT|HOST|GPU|ROUTER|ROUTE' || true`
- inspect command line:
  - `tr '\0' ' ' < /proc/<PID>/cmdline`
- inspect open model file if possible:
  - `lsof -p <PID> | rg -i 'gguf|qwen|apex|model' || true`

Do not print secrets.

# API/runtime smoke

Use direct llama.cpp-compatible endpoint checks only. Keep prompts tiny.

Run and report:

- `curl -sS http://127.0.0.1:8001/health || true`
- `curl -sS http://127.0.0.1:8001/v1/models | head -200 || true`

Then run one tiny direct completion/chat request against `:8001`, using the model name returned by `/v1/models` if required. Prompt:

`Reply exactly: ok`

Capture:
- status code
- elapsed time
- prompt tokens if response includes them
- completion tokens if response includes them
- whether output exactly contains `ok`
- whether any CUDA/Xid errors appeared afterward

Do not run long prompts.

# Cockpit/API smoke

Run one tiny Cockpit/backend route smoke only if an existing endpoint is known from current code. Prefer read-only health/config endpoints first.

Allowed:
- `/api/health`
- current Cockpit config/status endpoint if discoverable
- one tiny chat smoke only if endpoint and payload are obvious from tests/docs

Prompt if chat smoke is run:

`Reply exactly: ok`

Capture:
- route used
- status
- elapsed time
- whether prompt amplification occurs
- selected model
- active model
- runtime/provider
- degraded/runtime error fields

Do not run deep research, extraction, Qdrant/news backfills, or Home producer jobs.

# Files to inspect read-only

Inspect only as needed:

- `scripts/cockpit`
- `scripts/run_llama_server.sh`
- `scripts/start_full_stack.sh`
- `scripts/run_extraction_server.sh`
- `financial-engine_v2/.env.docker`
- `financial-engine_v2/backend/app/services/llm.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- Cockpit status/config route files
- task/report artifacts from the NVMe relaunch
- any runtime/model registry/config file that selects `qwen3.5-35b-a3b-apex`

Do not edit.

# Hard boundaries

Do not:
- restart services
- stop services
- launch a new model
- change CUDA_VISIBLE_DEVICES
- change model selection
- change runtime config
- edit scripts
- edit Docker Compose
- edit systemd
- edit `.env`
- mutate data, reports, DBs, Qdrant, news, memory, models, or embeddings
- run extraction jobs
- run long chat prompts
- run Home producer work
- benchmark heavily
- commit/stash/clean

# Required output

Write:

`reports/agent_jobs/apex_m40_runtime_stability_audit_v1_20260519/README.md`

Include:

- Confirmed facts
- Inferred facts
- Speculative claims
- DATA_MISSING
- live runtime map:
  - `:8000`
  - `:8001`
  - `:8002` if present
  - `:8081`
- GPU inventory:
  - GT 1030
  - M40
  - GPU indexes
  - VRAM used
  - process allocation
- APEX model proof:
  - config-selected model
  - runtime-loaded model
  - `/v1/models` result
  - process command/model file evidence
- stability evidence:
  - direct smoke status
  - latency
  - tokens
  - output
  - post-smoke Xid/CUDA log check
- Cockpit model status explanation:
  - why Cockpit says GT 1030 if APEX/M40 uses a different GPU, or DATA_MISSING
- verdict:
  - `APEX_M40_RELIABLE`
  - `APEX_M40_DEGRADED`
  - `APEX_SELECTED_BUT_NOT_PROVEN_ACTIVE`
  - `M40_NOT_IN_USE`
  - `DATA_MISSING`
- recommended next safe step
- final git status
- registry release status if claimed
- Project Memory save recommendation

# Hard stops

Stop and report if:
- active registry shows overlapping runtime/model/GPU work
- `:8001` is not listening
- M40 is not visible to `nvidia-smi`
- direct smoke causes fresh NVIDIA Xid/CUDA error
- direct smoke exceeds 120 seconds
- model process cannot be identified
- proving runtime state would require restart/config mutation
