# Rollback Plan

## Immediate rollback (no destructive data changes)
1. Stop services:
   - `scripts/cockpit stop`
2. Restore runtime binding configuration:
   - `git checkout -- scripts/start_config.env financial-engine_v2/docker-compose.yml`
3. Re-claim pending agent claim if needed:
   - `python3 scripts/agent_job_registry.py release nvme_hybrid_runtime_data_binding_v1_20260517`

## Data-safe follow-up actions
- NVMe copies remain in place (incremental and small runtime folders).
- Large HDD doc/PDF trees remain unchanged.

## Optional full rollback of copied data (use only if asked)
- Remove only copied runtime folders created for this temporary migration from NVMe:
  - `rm -rf /mnt/nvme/tenn/financial-engine_v2/data/{ops,cockpit,raw,db_recovery,asx,resource_library}`
  - `rm -rf /mnt/nvme/tenn/financial-engine_v2/reports`

  (Run these only with explicit approval; they are destructive.)
