# NVMe2 Binding Switch

## Verdict

BINDING_SWITCH_PARTIAL

## Branch / HEAD

- Branch: migration/clean-runtime-baseline-reconstruct-v1
- Starting HEAD: 52f1aba48fa429c189f65b1049ea3535654b5e92

## Copy gap final check

- Remaining missing files: 2
- Expected only safe excludes remain:
  - reports/router_metrics_snapshot.json
  - reports/tmpc6h17mhb.tmp

## Target visibility

- /mnt/tenn-nvme2/tenn/financial-engine_v2/data: 153G
- /mnt/tenn-nvme2/tenn/financial-engine_v2/reports: 786M
- docs sample present under /mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs

## Binding changes

- `scripts/start_config.env`: unchanged
- `financial-engine_v2/docker-compose.yml`: updated
  - backend/container `/data` -> `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`
  - backend/container `/reports` -> `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports`
  - temporary HDD doc/pdf binds replaced with nvme2 equivalents
  - old `/mnt/nvme/tenn/...` data/reports binds replaced with `/mnt/tenn-nvme2/...`

## Docker volume safety

- `fe_pgdata` and `fe_qdrant` preserved and unchanged in compose.
- Existing mountpoints remain on `/mnt/nvme/docker/volumes/...`.
- DB/Qdrant migration remains a follow-up task.

## Limited smoke / launch plan

- Limited smoke deferred in this run.
- See `limited_smoke_or_plan.json` for execution steps.

## Remaining HDD/current-NVMe dependencies

- No backend `/data` or `/reports` mounts remain to temporary HDD paths.

## Rollback

- Source HDD data untouched.
- Previous hybrid commit remains available in history.
- Revert commit after commit if rollback is required.

## Next safe step

Run limited backend smoke plan and, if health and path checks pass, proceed to final launch and mark `BINDING_SWITCH_COMMITTED`.

## Project Memory save recommendation

Record this partial switch completion: binding paths now point to NVMe2 with two accepted excludes, smoke pending.
