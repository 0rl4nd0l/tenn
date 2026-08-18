# Extraction Third Canary Runtime Preflight

## Verdict

Status: BLOCKED BEFORE CANARY.

The exact operator approval phrase for the refreshed #96 third-canary packet was
received:

`APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529`

No document was submitted. No `POST /api/process/document/{document_id}` was
made. No canary, broad backfill, direct SQL, Qdrant mutation, news/memory write,
source-PDF mutation, parser/prompt/schema change, service restart, runtime/model
change, Cockpit UI change, or GitHub issue mutation was performed.

## Blocking Gates

The live runtime preflight is not safe enough to execute the packet:

1. GPU health is not cleanly verifiable. `scripts/gpu_process_guard.sh --check`
   exited without a hard failure, but emitted `nvidia-smi` query warnings, and a
   direct `nvidia-smi` probe returned `Unable to determine the device handle for
   GPU0000:25:00.0: Unknown Error`.
2. Loaded worker code cannot be proven current. `fe_backend`, `fe_worker`, and
   `fe_gpu_worker` have been running since `2026-05-27T10:45Z`, while the
   current baseline HEAD is `e2029835efbd2eb6425f089d703841eb20625bf7` and the
   AAU-integrated `multipass_extraction.py` file changed on
   `2026-05-29T18:52:10+10:00`. Bind-mounted source hashes match the current
   checkout, but the long-running Python processes may still have imported old
   code.
3. The approval packet treats any required service restart as an abort
   condition. Since proving current loaded code would require a backend/worker
   reload, this approval does not authorize continuing.
4. The task-card overlap/claim gate is not clean in this shared checkout
   because an unrelated stale Query Orchestration task card is already dirty:
   `docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_v1_20260529.md`.

## Gates That Did Pass

- Repo/runtime symlink path resolved to
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch `migration/clean-runtime-baseline-reconstruct-v1` is at
  `e2029835efbd2eb6425f089d703841eb20625bf7`.
- `/api/health` returned `{"status":"ok"}`.
- The seven approved source PDFs still exist at their packet paths.
- No adjacent `.pdf.pymupdf.json` or `.docling.json` sidecars were found beside
  the seven approved source PDFs.
- Container bind-mounted extraction file hashes match the current checkout for
  `multipass_extraction.py`, `docling_extract.py`, `pipeline.py`, and
  `worker_tasks.py`.

## DATA_MISSING

- Clean GPU process/VRAM proof.
- Proof that the live backend and workers have loaded current HEAD code.
- Queue/orphan proof for approved document IDs beyond `/api/ops/jobs/active`;
  that endpoint still lists stale non-canary jobs from prior dates.
- Explicit approval to reload backend/worker/gpu_worker and then run the
  approved seven-document canary.
- Clean task-card overlap/claim state in the shared runtime checkout.

## Files Changed

- `docs/agent_tasks/extraction_third_canary_runtime_preflight_v1_20260529.md`
- `reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/README.md`
- `reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/preflight.json`
- `reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/status.json`
- `reports/agent_jobs/extraction_third_canary_runtime_preflight_v1_20260529/diff-check.json`
- `docs/claude/STATE.md`

## Next Safe Step

Do not run the third canary from the current live runtime state. The next safe
step is an explicit runtime-reload approval that covers backend, worker, and
gpu_worker reload, followed by a fresh GPU health check and the same
one-document-at-a-time seven-ID canary packet from a clean claimed runtime task.
