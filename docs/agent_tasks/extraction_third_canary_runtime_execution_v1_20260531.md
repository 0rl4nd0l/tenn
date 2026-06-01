---
job_id: extraction_third_canary_runtime_execution_v1_20260531
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_third_canary_runtime_execution_v1_20260531.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/README.md
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/status.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/validation.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/preflight.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/source_paths.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/document_rows.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/runtime_startup.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/queue_before.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/canary_results.json
  - reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531/queue_after.json
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_third_canary_runtime_execution_v1_20260531
mutation_mode: safe_extension
requested_mutation_mode: runtime_canary_execution
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "APPROVE extraction_third_canary_runtime_execution_v1_20260531 WITH BACKEND WORKER GPU_WORKER RELOAD; user also approved full production runtime necessary to complete the extraction goal."
---

# Extraction Third Canary Runtime Execution V1

## Objective

Run the bounded seven-document third canary from
`extraction_third_canary_approval_packet_refresh_v1_20260529` after integrating
the current pre-persistence hardening stack, with backend/worker/GPU runtime
reloaded and proved immediately before submission.

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

- Start or reload backend on the canonical `:8000` API path.
- Start or reload the backend Celery worker consuming `llm_gpu`.
- Start or reload the canonical llama.cpp router on `:8001` only if health is
  down and GPU guard/VRAM checks pass.
- Use the router model-load API when the router is healthy but the extraction
  model is not loaded.

Not approved:

- broad backfill
- `/process/ticker`
- direct Celery enqueue
- direct SQL mutation
- Qdrant/news/memory/manual source-PDF mutation outside the backend-owned
  single-document route
- parser routing, prompt, schema, migration, or GitHub mutation

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION with approved runtime canary side effects.

Intended files: this task card, runtime report bundle, and
`docs/claude/STATE.md`.

Contested surfaces touched: none by file edit. Runtime uses the existing
backend API and worker surfaces.

Collision risk: HIGH because this performs financial-truth runtime extraction
and canonical backend writes for exactly seven approved documents. Proceed only
if registry, queue, GPU, backend, worker, loaded-code, source-path, and
document-row gates are clean.

Decision: proceed after validation, overlap check, registry claim, and all
runtime gates.

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

Why safe: the run is bounded to seven pre-approved document IDs, uses the
existing backend single-document route one document at a time, stops on the
first hard gate failure, and records preflight plus result evidence before any
broader extraction claim.

GPU process check required: yes. Backend/worker extraction depends on the
canonical llama.cpp router.

## Runtime Gates

Before the first document POST:

- Task card validates and is claimed.
- Shared registry has no overlapping extraction/backfill/runtime job.
- `scripts/gpu_process_guard.sh --check` exits `0`.
- `nvidia-smi` shows sufficient M40 free memory.
- Backend health at `/api/health` is reachable.
- Queue status at `/api/queue/status` is reachable.
- Worker responds to Celery inspection or queue processing can be otherwise
  observed.
- Live backend and worker code are `cf1bdcf4` or a documented descendant.
- Approved source paths exist.
- Approved document rows exist exactly once.
- No approved document is already queued/running/orphaned.

Stop immediately if any hard gate fails.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_third_canary_runtime_execution_v1_20260531.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_third_canary_runtime_execution_v1_20260531.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_third_canary_runtime_execution_v1_20260531.md --repo-root .`
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_third_canary_runtime_execution_v1_20260531.md --repo-root .`
- Registry release and final list-active.
