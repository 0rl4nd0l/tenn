# Extraction Third Canary Runtime Readiness Refresh V2

## Verdict

Status: BLOCKED BEFORE CANARY.

The prior approval phrase was recorded by the blocked preflight:

`APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529`

That phrase does not authorize a backend/worker/gpu_worker reload, and the
current runtime state still fails the safe-execution gates. No document was
submitted. No `POST /api/process/document/{document_id}` was made. No service
was restarted or reloaded. No canary, broad backfill, direct SQL, Qdrant
mutation, news/memory write, source-PDF mutation, parser/prompt/schema change,
runtime/model/GPU config change, Cockpit UI change, or GitHub issue mutation was
performed.

## Current Evidence

- Branch: `audit/extraction-runtime-readiness-refresh-v2-20260529`.
- Worktree: `/home/l4nd0/tenn-extraction-runtime-readiness-refresh-v2-20260529`.
- Baseline branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Baseline HEAD: `7ee06fbdad5f954056981769eef3ba25bee86480`
  (`milestone(extraction): block third canary on runtime preflight`).
- `/api/health` returned `{"status":"ok"}`.
- `/api/queue/status` returned Redis connected with all queues at `0`.
- `scripts/gpu_process_guard.sh --check` exited `0` but emitted repeated
  `nvidia-smi` query warnings.
- Direct `nvidia-smi` failed with
  `Unable to determine the device handle for GPU0000:25:00.0: Unknown Error`.
- Runtime containers are still long-running:
  - `fe_backend`, started `2026-05-27T10:45:40.592004537Z`
  - `fe_worker`, started `2026-05-27T10:45:42.410745023Z`
  - `fe_gpu_worker`, started `2026-05-27T10:45:42.444213793Z`

## Blocking Gates

1. GPU health is not cleanly verifiable. The guard did not return a hard
   nonzero code, but it could not query `nvidia-smi`, and a direct `nvidia-smi`
   probe failed with the GPU handle error.
2. Loaded worker code is still not proven current. The containers predate the
   integrated extraction hardening on the baseline, and long-running Python
   process imports cannot be proven fresh without a reload.
3. The received third-canary approval phrase authorizes the seven-document
   canary packet only. It does not authorize the service reload required to
   prove loaded code.
4. A prior AAU-only reload packet is stale for current execution: it targeted an
   older baseline descendant requirement, scoped only AAU, and did not promote a
   direct `nvidia-smi` handle failure to a hard readiness blocker.

## DATA_MISSING

- Clean direct GPU/VRAM proof.
- Proof that live backend, worker, and gpu_worker processes have loaded current
  extraction code.
- Explicit approval for a bounded runtime reload after GPU health is clean.
- A clean approval-required runtime execution task card for any later canary.
- Future actual payloads and #97 scorecard results.
- Full graduation evidence for broad accurate extraction.

## Next Safe Step

Do not run the seven-document third canary from the current runtime state. The
next safe operator-visible state change must first restore clean GPU health so
`nvidia-smi` works. After that, create a new approval-required runtime execution
task that explicitly authorizes restarting only `backend`, `worker`, and
`gpu_worker`, proves post-reload loaded code, rechecks queues/source paths/GPU
health, and submits at most one document at a time through the backend route.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`: one stale
  unrelated Query Orchestration job, no file overlap.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md --repo-root .`
- `curl -m 5 -sS http://127.0.0.1:8000/api/health`
- `curl -m 5 -sS http://127.0.0.1:8000/api/queue/status`
- `scripts/gpu_process_guard.sh --check`: exit `0` with `nvidia-smi` query
  warnings; not accepted as clean GPU readiness.
- `nvidia-smi`: exit `255`, GPU handle error; accepted only as blocking
  evidence.
- Docker container start-time inspection for `fe_backend`, `fe_worker`, and
  `fe_gpu_worker`.
- JSON validation for `runtime_readiness_packet.json` and `status.json`.
- `git diff --check` and `git diff --cached --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_third_canary_runtime_readiness_refresh_v2_20260529.md --repo-root .`
- Code-reviewer pass over the report-only diff: no critical, warning, or
  suggestion findings.
