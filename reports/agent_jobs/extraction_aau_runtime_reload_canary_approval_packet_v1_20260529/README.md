# Extraction AAU Runtime Reload Canary Approval Packet V1

## Verdict

READY_FOR_OPERATOR_APPROVAL.

This task did not restart, reload, stop, start, or rebuild any service. It did
not submit AAU, and it did not submit ATM, AM5, AQX, CRS, CLV, or CTM.

The prior AAU-only retry is blocked because the running backend and Celery
containers started on 2026-05-27, before the integrated AAU period-semantics
fix was present on the current baseline. Fresh `docker exec` imports are not
enough to prove the long-running uvicorn or Celery worker processes loaded the
new module graph.

## Required Approval Phrase

```text
APPROVE #96 RUNTIME RELOAD AND AAU CANARY extraction_aau_runtime_reload_canary_approval_packet_v1_20260529
```

That phrase authorizes only a later bounded runtime task to:

1. Restart `backend`, `worker`, and `gpu_worker`.
2. Prove the restarted backend and workers are serving `e2029835` or a
   descendant that includes it.
3. Submit AAU alone through the backend single-document route.
4. Stop before ATM, AM5, AQX, CRS, CLV, or CTM unless AAU passes and a separate
   approval/task reopens the remaining canary sequence.

## Current Evidence

- Target baseline head:
  `e2029835efbd2eb6425f089d703841eb20625bf7`
  (`milestone(extraction): record AAU integration claim release`).
- `origin/migration/clean-runtime-baseline-reconstruct-v1` currently resolves to
  that same commit.
- Current API health returned `{"status":"ok"}`.
- Current queue status returned Redis connected and all queues at `0`.
- Compose services seen: `redis`, `postgres`, `qdrant`, `worker`, `backend`,
  `fe_beat`, `gpu_worker`.
- Running containers seen:
  - `fe_backend`, started `2026-05-27T10:45:40.592004537Z`
  - `fe_worker`, started `2026-05-27T10:45:42.410745023Z`
  - `fe_gpu_worker`, started `2026-05-27T10:45:42.444213793Z`
- AAU source PDF exists at
  `/data/asx/docs/AAU/financial_performance/2026-03-31_annual-report-and-full-year-statutory-accounts_508fc892-ae88-45ec-981f-cd9e124c8375.pdf`
  with size `1804699` bytes.
- `scripts/gpu_process_guard.sh --check` exited `0`, with `nvidia-smi` warnings.
- The baseline worktree still has unrelated Query Orchestration task-card dirt:
  `docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_v1_20260529.md`.

## Future Runtime Scope

Candidate command for the later approved runtime task:

```bash
docker compose -f financial-engine_v2/docker-compose.yml restart backend worker gpu_worker
```

Allowed services:

- `backend`
- `worker`
- `gpu_worker`

Forbidden in this packet and in the immediate approved scope:

- restarting `postgres`, `qdrant`, `redis`, `fe_beat`, llama/model services, or
  frontend
- rebuilds, image pulls, config/env changes, migrations, direct SQL, Qdrant
  writes, Redis purges, source-PDF writes, parser routing changes, prompt
  changes, schema changes, Cockpit UI changes, or GitHub mutation

`cockpit restart backend` is not the proposed command for this packet because
the documented launcher path is broader than the minimum reload needed here.
The packet intentionally scopes the future reload to the three compose services
that need fresh Python process imports for the route and worker path.

## Future AAU Scope

Submit one document only:

```bash
curl -sS -X POST \
  "http://127.0.0.1:8000/api/process/document/508fc892-ae88-45ec-981f-cd9e124c8375" \
  -H "Content-Type: application/json" \
  -d '{"method":"auto","strict_method":false}'
```

AAU must be polled and reported before any remaining #96 candidate is touched.
ATM, AM5, AQX, CRS, CLV, and CTM remain blocked until AAU passes.

## Later Task Gates

- Validate and claim a new approval-required runtime task card.
- Check registry overlap before any reload.
- Confirm queue status is zero before reload and before AAU submission.
- Run `scripts/gpu_process_guard.sh --check` before reload and before AAU
  submission.
- Restart only `backend`, `worker`, and `gpu_worker`.
- Confirm post-reload health and queue status.
- Prove worker readiness after the restart.
- Confirm AAU source PDF still exists and has size `1804699`.
- Submit AAU alone.
- Capture route response, task/run identifiers, status, logs, and result.
- Stop on first hard gate failure or unexpected side effect.

## Validation Run For This Packet

- Task card validation: passed.
- Registry overlap check: passed.
- Registry claim: active for this packet.
- Compose service read: passed.
- API health read: passed.
- Queue status read: passed.
- GPU process guard read-only check: exit `0` with `nvidia-smi` warnings.
- AAU source PDF stat: passed.
