# Rollback Plan (Data-Binding Migration)

## Stop condition
- Data-binding launch validation fails, or services do not start with populated-data mapping.

## Immediate rollback
1. Stop launched services for the isolated branch launch attempt.
2. Restore `scripts/start_config.env` launcher path to the known-good baseline (`/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2`) before any service restart.
3. Verify backend and frontend still launch with known-good sparse state (if this is acceptable for immediate recovery).
4. Remove/disable any partially-seeded empty `financial-engine_v2_fe_pgdata` and `financial-engine_v2_fe_qdrant` attachments only if they were confirmed to be non-production new-empty test volumes.

## Data rollback
1. If any copy/move occurred in a later implementation task, restore backed-up tarballs from `/mnt/nvme/tenn/migrations/` and re-import into prior compose volumes.
2. Repoint compose back to prior data and rerun backend health checks.

## Service rollback validation
1. Verify `postgres` and `qdrant` are reachable.
2. Verify backend `GET /api/health` returns healthy.
3. Verify frontend backend URL remains `http://localhost:8000` in the same launch surface.

## Documentation rollback artifacts
- Keep this plan and final evidence report updated with any delta from the attempted migration attempt.
- Do not edit data stores during this rollback unless specifically authorized in a follow-up execution task.
