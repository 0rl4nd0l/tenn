# 07 - Production Hardening Execution Worksheet

Execution order:
1. Host stability (`01_nvml_host_stabilization_runbook.md`)
2. Ollama runtime validation (`02_ollama_m40_validation_and_mitigation.md`)
3. Model/routing policy (`03_model_tiering_m40_24gb.md`)
4. Pipeline/queue and durability checks
5. Final rollout gate decision

## A. GPU / NVML

### A1 - NVML stable across 3 reboots
- Objective: Prove NVML and GPU enumeration are stable across three consecutive boots.
- Evidence to capture: `nvidia-smi` outputs, boot IDs, kernel excerpts for each boot.
- Command skeletons:
```bash
date -u
uname -a
journalctl --list-boots | head -n 6
nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv
journalctl -b -k | rg -i "nvrm|xid|nvidia|nvml"
```
- Pass criteria: Three consecutive boot checks show successful `nvidia-smi` and no recurring NVML failure pattern.
- Fail action: Follow branch workflow in `docs/ops/01_nvml_host_stabilization_runbook.md`.

### A2 - Persistence and device nodes stable
- Objective: Verify persistence daemon and `/dev/nvidia*` node stability.
- Evidence to capture: service status, node listing, permissions snapshot.
- Command skeletons:
```bash
systemctl status nvidia-persistenced --no-pager
systemctl is-active nvidia-persistenced
ls -l /dev/nvidia*
cat /proc/driver/nvidia/version
```
- Pass criteria: Persistence service is active and expected `/dev/nvidia*` nodes exist without flapping.
- Fail action: Apply device-node/persistence remediation path in `docs/ops/01_nvml_host_stabilization_runbook.md`.

### A3 - No repeated NVRM/Xid errors
- Objective: Confirm no repeating GPU kernel fault patterns in observation window.
- Evidence to capture: filtered kernel log excerpt for the window.
- Command skeletons:
```bash
journalctl -k --since "24 hours ago" | rg -i "nvrm|xid|gpu has fallen off the bus"
journalctl -k --since "24 hours ago" | tail -n 200
```
- Pass criteria: No repeated NVRM/Xid sequence indicating instability.
- Fail action: Stop scale-up and triage per `docs/ops/01_nvml_host_stabilization_runbook.md`.

## B. Ollama

### B1 - GPU-confirmed inference run
- Objective: Verify Ollama inference drives GPU memory/compute on M40.
- Evidence to capture: inference output, Ollama logs, `nvidia-smi` telemetry during run.
- Command skeletons:
```bash
ollama ps
journalctl -u ollama --since "15 minutes ago" --no-pager | tail -n 200
nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv
curl -sS http://127.0.0.1:11434/api/generate -d '{"model":"phi3:mini","prompt":"return ok","stream":false,"options":{"num_predict":8}}'
nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv
```
- Pass criteria: Inference succeeds and M40 shows activity consistent with GPU-assisted run.
- Fail action: Apply `docs/ops/02_ollama_m40_validation_and_mitigation.md`.

### B2 - No `no kernel image` / CUDA arch mismatch pattern
- Objective: Prove absence of CUDA arch mismatch/runtime errors.
- Evidence to capture: Ollama logs filtered for CUDA/kernel-image errors.
- Command skeletons:
```bash
journalctl -u ollama --since "24 hours ago" --no-pager | rg -i "no kernel image|cuda error|sm_52|fallback"
journalctl -u ollama --since "24 hours ago" --no-pager | tail -n 300
```
- Pass criteria: No architecture mismatch signatures during representative runs.
- Fail action: Execute fix/rollback strategy in `docs/ops/02_ollama_m40_validation_and_mitigation.md`.

### B3 - Degraded-mode policy verified
- Objective: Validate controlled degraded behavior (reduced tier/context) when GPU path is unavailable.
- Evidence to capture: command, runtime logs, route/tier used, latency note.
- Command skeletons:
```bash
python3 scripts/local_coding_router.py --route fallback --num-ctx 4096 --num-predict 64 "Summarize this log block"
python3 scripts/local_coding_router.py --route simple --num-ctx 8192 --num-predict 64 "Summarize this log block"
```
- Pass criteria: Fallback route executes with expected reduced capability and documented SLA downgrade.
- Fail action: Tighten degraded routing per `docs/ops/03_model_tiering_m40_24gb.md`.

## C. Queues and Workers

### C1 - Queue health and no deadlocks
- Objective: Verify queues progress and workers are not stuck.
- Evidence to capture: worker inspect output, queue backlog snapshot, worker logs.
- Command skeletons:
```bash
cd financial-engine_v2
docker compose ps
docker compose exec -T worker celery -A worker_app.celery_app:celery inspect ping
docker compose exec -T worker celery -A worker_app.celery_app:celery inspect active
docker compose exec -T worker celery -A worker_app.celery_app:celery inspect reserved
docker compose exec -T redis redis-cli LLEN celery
docker compose logs --tail=200 worker
```
- Pass criteria: Workers respond, tasks move, and no queue remains stuck with active workers.
- Fail action: Inspect broker/worker routing and concurrency settings before rerun.

### C2 - GPU queue concurrency is enforced
- Objective: Confirm only one GPU-bound generation job runs at a time.
- Evidence to capture: active-task snapshots proving single GPU task concurrency.
- Command skeletons:
```bash
# If using dedicated GPU queue in this environment:
<gpu_worker_inspect_active_command>
<gpu_worker_inspect_active_queues_command>
# Current single-worker baseline:
cd financial-engine_v2
docker compose exec -T worker celery -A worker_app.celery_app:celery inspect active
```
- Pass criteria: At most one GPU-bound task is active at any snapshot.
- Fail action: Reduce worker concurrency / isolate GPU queue as defined in `docs/ops/04_batch_pipeline_architecture_fastapi_celery.md`.

### C3 - Overnight sustained run sanity
- Objective: Validate one overnight batch cycle without deadlock/GPU dropout.
- Evidence to capture: run start/end timestamps, job outcomes, failure summary.
- Command skeletons:
```bash
cd financial-engine_v2
curl -sS -X POST "http://localhost:8000/api/backfill/ticker/BHP?years=1"
docker compose logs --since=10h worker > /tmp/overnight_worker.log
docker compose logs --since=10h backend > /tmp/overnight_backend.log
```
- Pass criteria: Cycle completes with no critical runtime faults or deadlocked queue.
- Fail action: Pause schedule and remediate failing subsystem before another burn-in run.

## D. Postgres and Qdrant Durability

### D1 - Postgres backup/restore dry-run
- Objective: Verify backup integrity and restore viability.
- Evidence to capture: backup artifact path, restore output, row-count sanity query.
- Command skeletons:
```bash
cd financial-engine_v2
BACKUP="/tmp/fe_$(date +%F_%H%M%S).sql"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-fe}" -d "${POSTGRES_DB:-fe}" > "$BACKUP"
docker compose exec -T postgres createdb -U "${POSTGRES_USER:-fe}" fe_restore_test
cat "$BACKUP" | docker compose exec -T postgres psql -U "${POSTGRES_USER:-fe}" -d fe_restore_test
docker compose exec -T postgres psql -U "${POSTGRES_USER:-fe}" -d fe_restore_test -c "select count(*) from documents;"
```
- Pass criteria: Backup is created, restore succeeds, and integrity/row-count sanity checks pass.
- Fail action: Fix backup process before production scale-up.

### D2 - Qdrant snapshot/restore dry-run
- Objective: Validate Qdrant snapshot creation and restore path.
- Evidence to capture: snapshot metadata, restore command output, sample retrieval.
- Command skeletons:
```bash
curl -sS -X POST "http://localhost:6333/collections/asx_docs/snapshots"
curl -sS "http://localhost:6333/collections/asx_docs/snapshots"
# Restore dry-run target/flow may differ by environment:
<qdrant_snapshot_restore_command>
<qdrant_sample_query_command>
```
- Pass criteria: Snapshot and restore flow complete and sample retrieval is valid.
- Fail action: Remediate snapshot policy before rollout.

### D3 - Artifact storage growth controls
- Objective: Ensure storage growth remains within expected envelope.
- Evidence to capture: disk usage before/after run and retention behavior.
- Command skeletons:
```bash
df -h .
du -sh financial-engine_v2/data financial-engine_v2/reports
find financial-engine_v2/reports -type f | wc -l
```
- Pass criteria: No runaway growth outside expected overnight envelope.
- Fail action: Apply retention/archival controls and rerun overnight sanity.

## E. Application and Provenance Integrity

### E1 - Provenance completeness on generated artifacts
- Objective: Confirm required lineage fields exist for sampled outputs.
- Evidence to capture: sample rows/artifacts containing model/prompt/extractor/time linkage.
- Command skeletons:
```bash
cd financial-engine_v2
docker compose exec -T postgres psql -U "${POSTGRES_USER:-fe}" -d "${POSTGRES_DB:-fe}" \
  -c "select run_id, document_id, model_name, prompt_hash, extractor_version, status, created_at from extraction_runs order by created_at desc limit 20;"
<artifact_provenance_validation_command>
```
- Pass criteria: Required provenance fields are present for sampled outputs.
- Fail action: Block release until provenance writes are fixed.

### E2 - Reproducibility sanity
- Objective: Re-run same deterministic job and compare class/lineage outputs.
- Evidence to capture: both run IDs, output hashes, lineage metadata diff.
- Command skeletons:
```bash
<run_deterministic_job_command>
<rerun_same_job_command>
sha256sum <first_output_artifact> <second_output_artifact>
diff -u <first_lineage_metadata.json> <second_lineage_metadata.json>
```
- Pass criteria: Equivalent output class and expected lineage consistency with unchanged inputs/versions.
- Fail action: Investigate nondeterminism/version drift before rollout.

### E3 - Alert pipeline traceability
- Objective: Verify alert/event outputs map back to scoring runs and source docs.
- Evidence to capture: lineage chain from alert -> score -> source doc IDs.
- Command skeletons:
```bash
<fetch_recent_alerts_command>
<trace_alert_to_score_command>
<trace_score_to_source_documents_command>
```
- Pass criteria: Full lineage is reconstructable for sampled alerts/events.
- Fail action: Disable autonomous alert actions until lineage gaps are closed.

## Final Rollout Gate

Rollout is allowed only when all are true:
1. A1-A3 pass
2. B1-B3 pass
3. C1-C3 pass
4. D1-D3 pass
5. E1-E3 pass

If any check fails, remain in stabilization mode, remediate, and rerun this worksheet.

## Run Metadata

Capture and attach this metadata with the worksheet evidence bundle.

- Timestamp (UTC)
- Operator
- Hostname
- Active branch and commit hash
- Dirty worktree status
- Ollama version
- NVIDIA driver version
- Notes

Command skeletons:
```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
whoami
hostname
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD
git status --short
ollama --version
nvidia-smi --query-gpu=driver_version --format=csv,noheader
```
