# Launch Smoke Plan (Optional)

## 0) Preconditions
- Verify no conflicting services are already running.
- Confirm target mounts exist and are writable where expected:
  - `ls -ld /mnt/nvme/tenn/financial-engine_v2/data /mnt/nvme/tenn/financial-engine_v2/reports`
  - `test -d /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/asx/docs`

## 1) Backend launch command
```bash
cd /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1
source scripts/start_config.env
scripts/cockpit start
```

## 2) Frontend launch command
```bash
cd /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1
scripts/cockpit ui-start
```

## 3) Health checks
- Backend: `curl -fsS http://127.0.0.1:8000/api/health`
- Cockpit config: `curl -fsS http://127.0.0.1:8000/api/cockpit/config`

## 4) Data-population checks
- Verify copied runtime folders exist in NVMe data tree:
  - `ls -la /mnt/nvme/tenn/financial-engine_v2/data/{ops,cockpit,raw,db_recovery,asx,resource_library}`
  - `find /mnt/nvme/tenn/financial-engine_v2/data -maxdepth 3 -type f | head -80`

## 5) Docs path checks
- Confirm HDD doc bindings are present and readable:
  - `ls -la /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/asx/docs`
  - `ls -la /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/extraction_gold_real/pdfs`
  - `ls -la /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/benchmark/pdfs`
  - `ls -la /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/marketindex/pdfs`

## 6) Rollback and stop
- Stop services: `scripts/cockpit stop`
- Revert runbook by restoring git-tracked config via:
  - `git checkout -- scripts/start_config.env financial-engine_v2/docker-compose.yml`
- Keep copied data untouched unless explicit cleanup is requested.
