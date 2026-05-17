# NVMe Data Binding Migration Implementation Plan (Draft)

## Objective
Prepare backend/frontend launch from isolated baseline for populated runtime data without copying or mutating data in this task.

## Source data paths
- Source canonical dataset: `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data`
- Source ASX docs: `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/asx/docs`
- Source reports: `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/reports`
- Source models/runtime context (already NVMe): `/mnt/nvme/tenn/models`, `/mnt/nvme/tenn/runtime-data`

## Target 2TB NVMe paths
- Code-independent backend data root: `/mnt/nvme/tenn/financial-engine_v2/data`
- Postgres volume target (compose-named): `financial-engine_v2_fe_pgdata` -> `/mnt/nvme/docker/volumes/financial-engine_v2_fe_pgdata/_data`
- Qdrant volume target (compose-named): `financial-engine_v2_fe_qdrant` -> `/mnt/nvme/docker/volumes/financial-engine_v2_fe_qdrant/_data`
- Backend worktree for migration execution: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` (if continuing from isolated branch)

## Required pre-copy backup list
- Backup source dataset root and key subtrees before migration.
- Snapshot compose volumes if they contain seeded runtime data.
- Capture a run ledger (before/after file hashes, counts, and compose status).

## Services to stop before copy
- PostgreSQL
- Redis (if involved in in-flight jobs)
- Qdrant
- Backend and worker services

## Draft copy commands (do not execute in this task)
- Validate target directories and permissions before copy.
- Suggested data copy:

```bash
# Example (audit-only draft)
rsync -aHAXx --info=progress2 --numeric-ids \
  /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/ \
  /mnt/nvme/tenn/financial-engine_v2/data/

rsync -aHAXx --info=progress2 --numeric-ids \
  /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/reports/ \
  /mnt/nvme/tenn/financial-engine_v2/reports/
```

## Draft Docker volume backup/export method (do not execute in this task)
- Export existing populated volumes (if any) to tar stream.

```bash
# PG
# docker run --rm -v financial-engine_v2_fe_pgdata:/data busybox tar -C /data -czf - . > /mnt/nvme/tenn/migrations/fe_pgdata-${DATE}.tar.gz
# Qdrant
# docker run --rm -v financial-engine_v2_fe_qdrant:/data busybox tar -C /data -czf - . > /mnt/nvme/tenn/migrations/fe_qdrant-${DATE}.tar.gz
```

## Compose/env binding strategy
- Current issue: launch scripts currently point `ENGINE_ROOT` to `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2`, so `./data` resolves there.
- For a clean isolated launch, align:
  - `scripts/start_config.env` `ENGINE_ROOT` to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2`
  - Ensure compose env generated/used for `.env.docker` sets `DATA_ROOT` and DB URLs as intended.
  - Keep `TENN_MODELS_NVME_DIR=/mnt/nvme/tenn/models` in runtime env.
  - Keep frontend `NEXT_PUBLIC_API_URL` defaulting to `http://localhost:8000` only when co-located.

## Validation commands after launch (draft)
- `cd /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2 && docker compose ps`
- `... docker compose up -d postgres qdrant backend worker`
- `python3 - <<'PY'` checks on startup DB/collection existence (backend-only, do not run locally unless task continues)
- `curl -sS http://127.0.0.1:8000/api/health`
- smoke checks for data-bound artifacts (ASX docs path reachable + sample report reads)

## Rollback actions
- Preserve original fast-dev launcher and data bindings.
- Keep source-only copy for rapid reversion.
- If launch fails, stop all services and revert compose launch target bindings to fast-dev path before restart.
