---
job_id: extraction_third_canary_runtime_execution_v1_20260531
lane: Financial Truth
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_third_canary_runtime_execution_v1_20260531.md
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/README.md
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/status.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/validation.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/runtime_preflight.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/canary_execution_log.jsonl
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/scorecard_summary.json
  - docs/claude/STATE.md
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 97
---

# Extraction Third Canary Runtime Execution

## Status

Draft only. Do not claim or execute this task unless the operator explicitly
approves this exact task card and the approval phrase below.

Required approval phrase:

`APPROVE extraction_third_canary_runtime_execution_v1_20260531 WITH BACKEND WORKER GPU_WORKER RELOAD`

## Objective

Run the third extraction canary only after fresh runtime gates pass. The run is
bounded to the seven already-approved candidate documents from
`extraction_third_canary_approval_packet_refresh_v1_20260529`, one document at
a time, with scorecard evidence captured after each submission.

## Candidate Documents

1. AAU `508fc892-ae88-45ec-981f-cd9e124c8375`
2. ATM `96e9aabd-44dc-4c2c-be8c-74248a0a9025`
3. AM5 `aacc4c29-3089-48cf-8b82-8004134f9387`
4. AQX `0ed0104f-f29a-4068-8ff7-370f14fead98`
5. CRS `b43a16fb-7660-4bf7-96ab-0db641cd4032`
6. CLV `da9f9ea5-6596-464f-af14-5acf12f9b050`
7. CTM `035c6758-7aed-41a6-9e84-ad154125d431`

## Runtime Actions Authorized Only After Approval

- Start or reload only the local backend, worker, and gpu_worker required for
  canary execution.
- Re-prove post-reload backend health, queue health, direct GPU health, GPU
  guard status, loaded code identity, source path availability, and active
  registry ownership.
- Submit at most one document at a time through the backend route
  `POST /api/process/document/{document_id}`.
- Stop immediately after any failed gate, failed submission, queue anomaly,
  parser error, validation-gate truth blocker, or scorecard blocker.

## Required Gates Before First Submission

- This task card validates and is claimed.
- No unresolved overlapping active task owns extraction/runtime/candidate files.
- Backend `/api/health` is reachable and healthy.
- Backend `/api/queue/status` is reachable and queues are idle or explicitly
  understood.
- Direct `nvidia-smi` succeeds and shows no competing compute process on the
  extraction GPU.
- `scripts/gpu_process_guard.sh --check` exits `0`.
- Loaded backend, worker, and gpu_worker code is proven to match the intended
  branch/commit.
- All seven source PDF paths are present.
- The operator approval phrase above is present in the current conversation.

## Forbidden

- Running without the exact approval phrase.
- Broad backfill or multi-document batch submission.
- Direct SQL writes, Qdrant writes, source-PDF mutation, parser/prompt/schema
  changes, GitHub mutation, Cockpit UI mutation, or canonical write
  authorization outside the backend canary path.
- Treating a green canary as full extraction graduation without the broader
  scorecard and accuracy evidence required by the handoff.
