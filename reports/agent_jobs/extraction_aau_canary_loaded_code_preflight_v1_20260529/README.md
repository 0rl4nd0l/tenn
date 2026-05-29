# Extraction AAU Canary Loaded-Code Preflight V1

## Summary

- Related issue: #96
- Branch: `audit/extraction-aau-canary-loaded-code-preflight-v1-20260529`
- Worktree: `/home/l4nd0/tenn-aau-canary-loaded-code-preflight-v1-20260529`
- Target baseline HEAD: `e2029835efbd2eb6425f089d703841eb20625bf7`
- Candidate checked: AAU `508fc892-ae88-45ec-981f-cd9e124c8375`
- Mode: AUDIT ONLY
- AAU submitted: no
- Broad backfill run: no
- DB/Qdrant/news/memory/source-PDF mutation: no
- Runtime/backend/worker/llama restart: no

## Verdict

AAU must not be submitted under the current approval packet yet.

The current branch is ready and pushed, the AAU source PDF exists, the API is
healthy, queues are empty, and `scripts/gpu_process_guard.sh --check` exited
`0`. However, the approval packet requires proof that the live backend and
worker are serving the integrated commit or a descendant.

That proof is not available:

- `fe_backend`, `fe_worker`, and `fe_gpu_worker` all started on
  `2026-05-27T10:45:40Z` to `2026-05-27T10:45:42Z`.
- The AAU integration commits were created on `2026-05-29`:
  - `c45f8f57` - `milestone(extraction): integrate AAU period fix and fixture`
  - `e2029835` - `milestone(extraction): record AAU integration claim release`
- The route is in `celery` task mode, so AAU would execute in `fe_gpu_worker`.
- `app.worker_tasks` imports `app.services.pipeline` at worker startup, and
  `pipeline.py` imports `run_multipass_extraction` at module import time.
- A fresh Python import inside the container sees the updated mounted files, but
  that does not prove the already-running worker process reloaded those modules.

The refreshed approval packet also lists this abort condition:

`service restart, parser routing change, prompt change, or schema change is required`

Because a reload/restart is the available path to prove loaded code, this audit
stopped before any `POST /api/process/document/...` call.

## Runtime Evidence

- `/api/health`: `{"status":"ok"}`
- `/api/cockpit/health`: overall `healthy`; GPU service status `unknown`
  because `nvidia-smi` is not installed.
- `/api/queue/status`: all queues zero.
- `scripts/gpu_process_guard.sh --check`: exit `0`, with `nvidia-smi` query
  warnings.
- AAU source PDF:
  `/data/asx/docs/AAU/financial_performance/2026-03-31_annual-report-and-full-year-statutory-accounts_508fc892-ae88-45ec-981f-cd9e124c8375.pdf`
  exists, `1804699` bytes.

## Validation

- Task-card validate: passed.
- Registry overlap check in isolated worktree: passed.
- Registry claim: passed.
- Runtime/container/process checks: completed.
- JSON validation: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed.
- Registry release: passed.

## Next Safe Step

Get explicit approval for a runtime reload/restart, or provide another
authoritative loaded-code proof path for the live backend and Celery workers.
After that, create a new approval-required runtime task card and submit AAU
alone through `POST /api/process/document/508fc892-ae88-45ec-981f-cd9e124c8375`.
Do not continue ATM/AM5/AQX/CRS/CLV/CTM until AAU passes.
