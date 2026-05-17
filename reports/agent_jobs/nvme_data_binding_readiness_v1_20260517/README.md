# NVMe Data Binding Readiness

## Verdict
- DATA_BINDING_READY_WITH_WARNINGS
- Launch is **not** currently ready to use populated data from the isolated branch without a pre-migration binding change.
- A controlled migration plan is now defined, but no data mutations were performed in this task.

## Code baseline
- worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `fc1d077bd5b9060e57f4bf550e1e4db158e45086`
- clean/dirty status: clean tracked state with task-card and report artifacts generated for this audit

## Deferred commits accepted for this planning phase
The following were explicitly accepted as deferred and are not treated as migration blockers for this phase:
- `c102f3f21505a01a8333b2f442dc2403cf67b509`
- `d147dad8ca67688d6a08b200c3a7e9fff95605ec`
- `80f71c50cdff151cea014a36a865e34b1331622e`

## Backend data binding
- current branch-local backend path (from clean branch launch configuration): `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/data`
  - source of truth: `scripts/start_config.env` sets `ENGINE_ROOT="/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2"`.
- populated source data path identified for migration baseline: `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data`
- future target data path (2TB NVMe): `/mnt/nvme/tenn/financial-engine_v2/data` (newly provisioned path for populated runtime copy)
- risk: launching from the isolated worktree with current config will still resolve `./data` under `ENGINE_ROOT` in fast-dev storage, not the isolated worktree data directory, so population is not guaranteed.

## Docker volume binding
- backend compose defines named volumes:
  - `fe_pgdata` → `/var/lib/postgresql/data`
  - `fe_qdrant` → `/qdrant/storage`
  - project-scoped names become `financial-engine_v2_fe_pgdata` and `financial-engine_v2_fe_qdrant`
- current compose project name defaults to `financial-engine_v2` (no explicit `project_name`); launch scripts do not pass `-p`.
- current host mountpoints: `/mnt/nvme/docker/volumes/financial-engine_v2_fe_pgdata/_data` and `/mnt/nvme/docker/volumes/financial-engine_v2_fe_qdrant/_data`
- would launch path create empties: likely **yes** at first run because those mountpoint directories currently do not exist.

## Frontend/backend binding
- `cockpit-ui/next.config.mjs` and `cockpit-ui/lib/proxy.ts` both default to:
  - `NEXT_PUBLIC_API_URL` if set
  - otherwise `http://localhost:8000`
- isolated-branch frontend launched from same machine expects backend on `http://localhost:8000` unless env override is supplied.
- backend from this baseline launch path can serve on `localhost:8000` only after backend stack is correctly bound to populated data and running.

## Llama/model/runtime binding
- current defaults and evidence:
  - `LLAMACPP_URL` / `LLM_URL` defaults resolve to `http://127.0.0.1:8001` in `.env.example` and runtime scripts.
  - `scripts/start_full_stack.sh` will set runtime values in engine compose env (`OLLAMA_URL`, `LLAMACPP_URL`) from `scripts/start_config.env` and default startup.
  - no explicit dependency on `/home/l4nd0/tenn-m40-8001-validation-v1` appears in checked backend/frontend binding evidence.
- model/runtime path currently present and write-ready on NVMe target disk is `/mnt/nvme/tenn/models` (read-only mounted as `${TENN_MODELS_NVME_DIR}` in compose for backend).
- repo and runtime data should remain separate from code worktree paths.

## Data inventory summary
- populated source dataset path: `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data` (large, `153G`, mounted on `/dev/sdc2`, populated)
- ASX docs: `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/asx/docs` (`152G`, /dev/sdc2, populated)
- reports: `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/reports` (`786M`, /dev/sdc2)
- fast-dev/sparse baseline paths are tiny relative to source:
  - `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/data` (`76K`, /dev/nvme0n1p1)
  - `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/data` (`716K`, /dev/nvme0n1p1)

## Required backup list
- backup/ snapshot populated source:
  - `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data`
  - `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/reports`
  - docker volume seeds `financial-engine_v2_fe_pgdata`, `financial-engine_v2_fe_qdrant` (if already populated in target environment)
- model/runtime directories that may be required for immediate launch continuity:
  - `/mnt/nvme/tenn/models`
  - `/mnt/nvme/tenn/runtime-data`

## Future implementation plan (draft-only)
- see `future_migration_plan.md`

## Rollback plan
- see `rollback_plan.md`

## Hard stops before actual migration
- Do not launch from the isolated worktree into compose as-is because backend data mount resolves to old fast-dev source path in config.
- Do not create `financial-engine_v2_fe_pgdata` and `financial-engine_v2_fe_qdrant` in new empty state without migration/export/import; this would lose production continuity.

## Launch readiness verdict
- `LAUNCH_READY_AFTER_DATA_BINDING_IMPLEMENTATION`

## Next safe step
- Implement and execute a dedicated **data binding migration prep** task in a non-mutating dry-run mode first (script and launch command verification), then execute planned rsync/export + compose migration under controlled window.

## Project Memory save recommendation
- Save binding evidence and final migration plan as a required handoff artifact before any runtime mutation.
