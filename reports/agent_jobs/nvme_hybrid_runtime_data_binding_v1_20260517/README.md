# NVMe Hybrid Runtime Data Binding

## Verdict
**HYBRID_BINDING_IMPLEMENTED**

## Branch / HEAD
- branch: migration/clean-runtime-baseline-reconstruct-v1
- starting_head: 28b6bb71e2bd483cb9abc45f178ad7f19864b3cd
- final_head: 28b6bb71e2bd483cb9abc45f178ad7f19864b3cd

## Data tiering
- copied to NVMe:
  - `/mnt/nvme/tenn/financial-engine_v2/data/ops`
  - `/mnt/nvme/tenn/financial-engine_v2/data/cockpit`
  - `/mnt/nvme/tenn/financial-engine_v2/data/raw`
  - `/mnt/nvme/tenn/financial-engine_v2/data/db_recovery`
  - `/mnt/nvme/financial-engine_v2/data/asx/importance`
  - `/mnt/nvme/tenn/financial-engine_v2/data/resource_library`
- kept on HDD:
  - `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/asx/docs`
  - `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/extraction_gold_real/pdfs`
  - `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/benchmark/pdfs`
  - `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/marketindex/pdfs`
- symlinked or bind-mounted:
  - Large document/PDF paths are bind-mounted read-only via docker-compose into:
    - `/data/asx/docs`
    - `/data/extraction_gold_real/pdfs`
    - `/data/benchmark/pdfs`
    - `/data/marketindex/pdfs`
- deferred until 2TB NVMe:
  - `data/reports` remains mixed and partially unavailable to copy from source due source file permission constraints in current environment.

## Binding changes
- `scripts/start_config.env`
  - Updated `ENGINE_ROOT` to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2`.
- `financial-engine_v2/docker-compose.yml`
  - Backend and worker services now mount `/mnt/nvme/tenn/financial-engine_v2/data` at `/data`.
  - Backend and workers mount `/mnt/nvme/tenn/financial-engine_v2/reports` at `/reports`.
  - Added explicit read-only bind mounts from HDD for large document/PDF trees listed above.
  - Kept `fe_pgdata` and `fe_qdrant` volume names unchanged.

## Docker volume safety
- Postgres: unchanged named volume `financial-engine_v2_fe_pgdata`.
- Qdrant: unchanged named volume `financial-engine_v2_fe_qdrant`.
- empty-volume risk: resolved.

## Launch readiness
- `READY_FOR_LAUNCH_SMOKE`

## Validation results
- `git diff --check`: passed.
- `agent_job_contract.py check-diff`: passed.
- Bind target checks: `/data` and `/reports` now resolve to explicit NVMe paths in effective config.
- Large docs: reachable through read-only bind mounts.
- Named DB/Qdrant volumes preserved.
- `data/reports` copy attempt failed due source permission restrictions (`root` owned files under source); no further blocker for launch path.

## Rollback plan
- See `rollback_plan.md` for exact steps.

## Tomorrow 2TB NVMe migration follow-up
- After 2TB install, copy deferred/permission-blocked folders into NVMe as policy allows.
- Revisit `/mnt/nvme/.../data/reports` and `data/reports` runtime requirements for optional completion.

## what to move later
- Reattempt `data/reports` copy with corrected source-read access policy or direct bind approach as allowed.
- Verify full `data/reports` ownership and permissions.

## how to remove temporary HDD binds later
- Restore config to pure NVMe mounts in `financial-engine_v2/docker-compose.yml` and `scripts/start_config.env` when migration complete.
- Keep DB/Qdrant volumes unchanged.

## Project Memory save recommendation
- Preserve this task card and report artifacts under:
  - `reports/agent_jobs/nvme_hybrid_runtime_data_binding_v1_20260517/`
- Keep `data_tier_inventory.json` and `post_binding_validation.json` as launch evidence for the next 2TB migration.
