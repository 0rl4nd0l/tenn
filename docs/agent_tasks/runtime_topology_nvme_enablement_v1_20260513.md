---
job_id: runtime_topology_nvme_enablement_v1_20260513
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_NVME_RUNTIME_ENABLEMENT_20260513_GPT
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/runtime_topology_nvme_enablement_v1_20260513
allowed_files:
  - docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md
  - scripts/start_config.env
  - scripts/cockpit
  - scripts/**
  - financial-engine_v2/docker-compose.yml
  - financial-engine_v2/.env.docker
  - reports/agent_jobs/runtime_topology_nvme_enablement_v1_20260513/**
---

# Task

Enable a safe NVMe-backed runtime launch path for Tenn, or stop with a precise blocker report.

Primary lane: Evaluation
Supporting lanes: Runtime / Repo Hygiene
Mode: SAFE EXTENSION
Expected collision risk: MEDIUM

# Background

The previous runtime migration audit was correctly BLOCKED. It confirmed:
- live runtime still serves from HDD preserve;
- NVMe worktree `/home/l4nd0/tenn-fast-dev-storage-v1` is clean/current;
- NVMe runtime artifacts are missing:
  - `tools/llama.cpp/build-cuda/bin/llama-server`
  - `cockpit-ui/node_modules`
  - `financial-engine_v2/.venv`
- copied launcher config still points `ENGINE_ROOT` / compose paths at `/home/l4nd0/tenn`, which resolves to HDD preserve;
- existing HDD runtime health mostly passes, but `/api/cockpit/home` times out and `:8002` is offline.

Goal: create or verify an explicit NVMe-backed runtime path without changing product behavior, DBs, Qdrant, model config, memory stores, extraction/gold labels, or application logic.

# Required preflight

Run and report:

- date -Iseconds
- pwd
- readlink -f /home/l4nd0/tenn
- readlink -f /home/l4nd0/tenn-fast-dev-storage-v1
- git -C /home/l4nd0/tenn-fast-dev-storage-v1 rev-parse --show-toplevel
- git -C /home/l4nd0/tenn-fast-dev-storage-v1 branch --show-current
- git -C /home/l4nd0/tenn-fast-dev-storage-v1 rev-parse HEAD
- git -C /home/l4nd0/tenn-fast-dev-storage-v1 status --short --untracked-files=all
- git worktree list
- registry/list-active if available
- task-card validate
- registry/check-overlap if available
- claim task if safe
- current listeners for :8000, :8001, :8081, :8002
- current process CWD/root evidence for backend, llama.cpp, and Cockpit
- current health probes for:
  - http://127.0.0.1:8000/api/health
  - http://127.0.0.1:8001/health
  - http://127.0.0.1:8001/v1/models
  - http://127.0.0.1:8081/api/cockpit/health
  - http://127.0.0.1:8081/api/cockpit/home with timeout + latency captured

# Allowed work

You may do only what is needed to establish an equivalent NVMe runtime launch path:

1. Inspect and minimally adjust host-local launcher config so canonical startup can point to:
   `/home/l4nd0/tenn-fast-dev-storage-v1`

2. Choose the safest dependency strategy and report it before applying:
   - install/build NVMe-local ignored runtime dependencies if needed;
   - or symlink/reuse existing dependency artifacts only if safe and clearly documented;
   - or stop if dependency setup is too broad.

3. If safe, recreate/restart runtime processes so:
   - backend compose root/bind mounts resolve to NVMe worktree;
   - Cockpit Next.js cwd resolves to NVMe `cockpit-ui`;
   - llama.cpp router launches from a valid NVMe-compatible binary path or a clearly documented shared binary path;
   - endpoints remain `:8000`, `:8001`, `:8081`.

4. Preserve named Docker volumes and existing service endpoints.

5. Write a rollback plan before stopping any existing service.

# Explicitly forbidden

Do not modify:

- product application logic
- QueryOrchestrator
- chat routes
- provenance/source-label logic
- memory cleanup code or company_memory.sqlite
- Qdrant data or config
- Postgres data
- news stores
- extraction prompts/parsers/gold labels
- model weights/config/presets
- source PDFs
- Cockpit UI feature code
- marketplace code

Do not start or fix `:8002` unless the only action is reporting that it remains offline.

Do not investigate `/api/cockpit/home` timeout beyond recording before/after latency and data_state. That is a separate Home performance task.

# Hard stops

Stop and report only if:

- NVMe worktree is dirty in product/source files.
- Launcher config changes would be broad or ambiguous.
- Runtime dependency installation/build would modify tracked product files unexpectedly.
- Docker compose recreation risks data loss or volume replacement.
- Active registry shows overlapping runtime/evaluation job.
- Existing runtime cannot be safely restored.
- Any health probe regresses and rollback fails.
- Any required restart command remains DATA_MISSING.

# Validation required

After any change/restart, run and report:

- process CWD/root table for backend, llama.cpp, Cockpit
- confirm whether each service now resolves to NVMe or not
- current listeners for :8000, :8001, :8081, :8002
- health probes:
  - :8000 /api/health
  - :8001 /health
  - :8001 /v1/models
  - :8081 /api/cockpit/health
  - :8081 /api/cockpit/home with timeout + latency + data_state if available
- git status for both preserve and NVMe worktrees
- git diff --check
- task-card check-diff
- registry release if claimed

# Rollback requirement

Before stopping/restarting anything, write the exact rollback steps in the report.

If a restart is attempted and probes regress, execute rollback to the previous HDD-backed runtime unless rollback itself is unsafe, then stop and report.

# Final report

Write:

reports/agent_jobs/runtime_topology_nvme_enablement_v1_20260513/README.md

Include:

- verdict: completed / partial / blocked / rolled back
- branch / HEAD / worktree
- task card status
- registry claim/release status
- before and after process CWD/root table
- exact files changed
- exact commands run
- dependency strategy used
- Docker compose volume preservation evidence
- health probe table before/after
- runtime now serves from NVMe? yes/no per service
- rollback plan and whether used
- remaining blockers
- DATA_MISSING
- final git status
- Project Memory save recommendation
