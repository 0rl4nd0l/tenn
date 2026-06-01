---
job_id: extraction_remaining_canary_after_clv_prose_fix_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_remaining_canary_after_clv_prose_fix_v1_20260601.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/README.md
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/status.json
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/validation.json
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/runtime_startup.json
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/preflight.json
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/queue_before.json
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/results.json
  - reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601/queue_after.json
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_remaining_canary_after_clv_prose_fix_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: runtime_canary_retry
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User approved full production runtime necessary to complete the extraction goal. This retry is bounded to the remaining approved third-canary documents after AAU, ATM, AM5, AQX, and CRS were accepted and CLV prose-highlight support landed in 4b0acebe."
---

# Extraction Remaining Canary After CLV Prose Fix V1

## Objective

Run the remaining approved third-canary documents after the CLV prose-highlight
code fix landed in `4b0acebe`.

Approved route:

`POST /api/process/document/{document_id}`

Approved remaining document IDs and order:

1. `da9f9ea5-6596-464f-af14-5acf12f9b050` CLV
2. `035c6758-7aed-41a6-9e84-ad154125d431` CTM

Prior accepted documents not rerun in this card:

- AAU `14616c70-ba40-4398-bd63-23fa1508a190` `ok_low_confidence`
- ATM `74442c2b-3ce4-45b9-8eed-1581d1fa319e` `ok_low_confidence`
- AM5 `c1c5fd5e-39f9-4efe-8534-e4d839558445` `ok`
- AQX `9aa658d6-c8db-4376-9698-cb33f05172f4` `ok`
- CRS `44a86108-eab0-4b41-911e-545a4d7682c5` `ok_low_confidence`

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION with approved bounded runtime side effects.

Intended files: this task card, runtime report bundle, and `docs/claude/STATE.md`.

Contested surfaces touched: none by file edit. Runtime uses the existing
backend API and worker surfaces.

Collision risk: HIGH because this performs financial-truth runtime extraction
and canonical backend writes for two approved documents. Proceed only if
registry, queue, GPU, backend, worker, loaded-code, and route gates are clean.

Decision: proceed after validation, overlap check, registry claim, runtime
startup, and all runtime gates.

## Contract Check

Target system layers: Extraction and Storage through the backend-owned
single-document API; Evaluation/Provenance for report artifacts.

Relevant contract rules: backend is sole authority; pipeline order must not be
skipped; metric extraction may only use explicit source values; no inference,
substitution, gap filling, direct datastore mutation, alternate pipeline, or
broad backfill is allowed.

What must not change: source PDFs, parser routing, extraction prompts, gold
labels, schemas/migrations, non-approved documents, Qdrant/news/memory stores
outside the route, Cockpit UI, GitHub state, and direct DB contents outside the
backend route.

Why safe: the retry is bounded to two remaining pre-approved document IDs, uses
the backend single-document route one document at a time, stops on first hard
failure, and records fresh evidence.

GPU process check required: yes, because this starts llama.cpp runtime.

## Runtime Gates

Before the first document POST:

- Task card validates and is claimed.
- Shared registry has no overlapping extraction/backfill/runtime job.
- `scripts/gpu_process_guard.sh --check` exits `0`.
- `nvidia-smi` shows sufficient M40 free memory.
- Backend health at `/api/health` is reachable after startup.
- Queue status at `/api/queue/status` is reachable.
- `llm_gpu` worker responds after startup.
- Worker env evidence proves `OLLAMA_URL=http://127.0.0.1:11434` is set.
- Live backend and worker code are `4b0acebe` or a documented descendant.
- Approved source paths still exist.
- Approved document rows still exist exactly once.
- No approved document is currently queued/running/orphaned.

Stop immediately if any hard gate fails.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_remaining_canary_after_clv_prose_fix_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_remaining_canary_after_clv_prose_fix_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_remaining_canary_after_clv_prose_fix_v1_20260601.md --repo-root .`
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_remaining_canary_after_clv_prose_fix_v1_20260601.md --repo-root .`
- Registry release and final list-active.
