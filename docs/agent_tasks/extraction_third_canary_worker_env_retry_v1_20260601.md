---
job_id: extraction_third_canary_worker_env_retry_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_third_canary_worker_env_retry_v1_20260601.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/README.md
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/status.json
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/validation.json
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/runtime_restart.json
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/preflight.json
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/queue_before.json
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/retry_results.json
  - reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601/queue_after.json
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_third_canary_worker_env_retry_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: runtime_canary_retry
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User approved full production runtime necessary to complete the extraction goal and specifically approved backend/worker/GPU worker reload for extraction_third_canary_runtime_execution_v1_20260531. Prior card 201d7701 hard-stopped after AAU failed because the dedicated worker lacked OLLAMA_URL; this retry is bounded to the same seven approved document IDs with worker env parity corrected."
---

# Extraction Third Canary Worker Env Retry V1

## Objective

Retry the bounded seven-document third canary after the prior runtime card
hard-stopped on AAU due to missing dedicated-worker `OLLAMA_URL` required by
model-routing config load. Restart only the dedicated `llm_gpu` worker with
`OLLAMA_URL=http://127.0.0.1:11434`, re-run gates, and submit approved
documents one at a time through the backend-owned route.

## Approved Scope

Approved route:

`POST /api/process/document/{document_id}`

Approved document IDs and order:

1. `508fc892-ae88-45ec-981f-cd9e124c8375` AAU
2. `96e9aabd-44dc-4c2c-be8c-74248a0a9025` ATM
3. `aacc4c29-3089-48cf-8b82-8004134f9387` AM5
4. `0ed0104f-f29a-4068-8ff7-370f14fead98` AQX
5. `b43a16fb-7660-4bf7-96ab-0db641cd4032` CRS
6. `da9f9ea5-6596-464f-af14-5acf12f9b050` CLV
7. `035c6758-7aed-41a6-9e84-ad154125d431` CTM

Approved runtime actions:

- Restart the dedicated canary `llm_gpu` worker with `OLLAMA_URL` set.
- Keep using the existing canary backend on `:8000` if health and loaded commit
  gates pass.
- Keep using the existing canary llama.cpp router on `:8001` if health, loaded
  model, and GPU guard gates pass.
- Use the router model-load API only if the extraction model is not loaded.

Not approved:

- broad backfill
- `/process/ticker`
- direct Celery enqueue
- direct SQL mutation
- direct cleanup/deletion of the prior failed AAU `extraction_runs` row
- Qdrant/news/memory/manual source-PDF mutation outside the backend-owned
  single-document route
- parser routing, prompt, schema, migration, or GitHub mutation

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION with approved bounded runtime retry side effects.

Intended files: this task card, runtime retry report bundle, and
`docs/claude/STATE.md`.

Contested surfaces touched: none by file edit. Runtime uses the existing
backend API and worker surfaces.

Collision risk: HIGH because this performs financial-truth runtime extraction
and canonical backend writes for exactly seven approved documents. Proceed only
if registry, queue, GPU, backend, worker, loaded-code, and route gates are clean.

Decision: proceed after validation, overlap check, registry claim, worker env
parity restart, and all runtime gates.

## Contract Check

Target system layers: Extraction and Storage through the backend-owned
single-document API; Evaluation/Provenance for report artifacts.

Relevant contract rules: backend is sole authority; pipeline order must not be
skipped; metric extraction may only use explicit source values; no inference,
substitution, gap filling, direct datastore mutation, alternate pipeline, or
broad backfill is allowed; GPU topology and spawn protocol must be followed.

What must not change: source PDFs, parser routing, extraction prompts, gold
labels, schemas/migrations, non-approved documents, Qdrant/news/memory stores
outside the route, Cockpit UI, GitHub state, and direct DB contents outside the
backend route.

Why safe: the retry is bounded to the same seven pre-approved document IDs,
uses the existing backend single-document route one document at a time, only
changes worker runtime environment parity, stops on the first hard failure, and
records fresh evidence before any broader extraction claim.

## Runtime Gates

Before the first document POST:

- Task card validates and is claimed.
- Shared registry has no overlapping extraction/backfill/runtime job.
- `scripts/gpu_process_guard.sh --check` exits `0`.
- `nvidia-smi` shows sufficient M40 free memory.
- Backend health at `/api/health` is reachable.
- Queue status at `/api/queue/status` is reachable.
- `llm_gpu` worker responds after restart.
- Worker env evidence proves `OLLAMA_URL=http://127.0.0.1:11434` is set.
- Live backend and worker code are `201d7701` or a documented descendant.
- Approved source paths still exist.
- Approved document rows still exist exactly once.
- No approved document is currently queued/running/orphaned.

Stop immediately if any hard gate fails.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_third_canary_worker_env_retry_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_third_canary_worker_env_retry_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_third_canary_worker_env_retry_v1_20260601.md --repo-root .`
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_third_canary_worker_env_retry_v1_20260601.md --repo-root .`
- Registry release and final list-active.
