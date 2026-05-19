---
job_id: nvme_full_system_functionality_v1_20260518
lane: Reporting
owner: Codex
mutation_mode: safe_extension
production_data_access: false
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 28800
output_dir: reports/agent_jobs/nvme_full_system_functionality_v1_20260518
allowed_files:
  - docs/agent_tasks/nvme_full_system_functionality_v1_20260518.md
  - reports/agent_jobs/nvme_full_system_functionality_v1_20260518/**
  - docs/agent_tasks/overnight_nvme2_runtime_normalization_v1_20260518.md
  - reports/agent_jobs/overnight_nvme2_runtime_normalization_v1_20260518/**
  - README.md
  - AGENTS.md
  - CLAUDE.md
  - docs/**
  - financial-engine_v2/README.md
  - financial-engine_v2/backend/README.md
  - financial-engine_v2/docker-compose.yml
  - financial-engine_v2/docker-compose*.yml
  - financial-engine_v2/.env.example
  - financial-engine_v2/scripts/**
  - financial-engine_v2/scripts/run_local_backend.sh
  - financial-engine_v2/backend/app/**
  - financial-engine_v2/backend/tests/**
  - cockpit-ui/README.md
  - cockpit-ui/next.config.mjs
  - cockpit-ui/package.json
  - cockpit-ui/pnpm-lock.yaml
  - scripts/**
  - scripts/run_llama_server.sh
  - scripts/run_extraction_server.sh
  - scripts/start_config.env
  - scripts/setup_nvme2_host_aliases.sh
  - scripts/verify_nvme_runtime_endpoints.sh
  - scripts/runtime/m40_llama_router_8001_conservative.sh
  - scripts/runtime/m40_known_good_llama_server_qwen25_14b.sh
  - scripts/test_run_local_backend_script.py
  - scripts/test_cockpit_launcher_helpers.py
  - scripts/run_ticker_expansion_batch.py
  - financial-engine_v2/scripts/run_batch_extract.py
  - financial-engine_v2/scripts/monitor_extraction.py
---

# NVMe full system functionality validation

## Objective

Ensure Tenn is functional from the validated NVMe root and NVMe2 data/report endpoints, with usable populated data and consistent runtime paths.

## Baseline assumptions to prove or correct

- Runtime root should be `/home/l4nd0/tenn-runtime` pointing at `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Active worktree should remain `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` on `migration/clean-runtime-baseline-reconstruct-v1` at `a99c1762bb72` or a direct descendant created by this task.
- `/home/l4nd0/tenn` must not be repointed.
- `/data` and `/reports` should resolve to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data` and `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports` respectively.

## Safety rails

- Audit before mutation.
- Do not delete or prune branches, worktrees, source HDD data, DBs, Qdrant stores, Docker named volumes, news stores, memory stores, parser outputs, gold labels, or Marketplace code.
- Data checks are metadata/read-only probes only. Do not mutate production data under this card.
- External mutation is limited to reversible runtime-root symlink and user systemd unit path corrections if inactive, backed up, and path-only.
- Service starts must be bounded; stop anything started by this task.
- If a fix requires data migration, DB rebuild, Qdrant rebuild, source HDD rewrite, or model/GPU flag tuning, stop and report instead of doing it.

## Planned stages

1. Contract, registry, branch, dirty-state, and endpoint preflight.
2. NVMe/NVMe2 data population and usability audit.
3. Runtime path and service audit.
4. Minimal path/root corrections if safe.
5. Backend/frontend/service validation from NVMe root.
6. Final report, status JSON, rollback notes, and registry release.

## Addendum: runtime model asset tier

Runtime model assets may be copied from `/mnt/nvme/tenn/models` to `/mnt/tenn-nvme2/tenn/models` if all of the following hold:

- source and target are existing directories;
- target has sufficient free space;
- no model/source files are deleted;
- services are stopped before config path changes;
- changes are limited to launcher/env/preset path references and report artifacts;
- no DB, Qdrant, news, memory, parser, gold, or source HDD data is modified.
