---
job_id: extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/README.md
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/status.json
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/validation.json
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/runtime_startup.json
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/preflight.json
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/queue_before.json
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/results.json
  - reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601/queue_after.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: runtime_canary_retry
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User approved full production runtime necessary to complete the extraction goal and then instructed Codex to proceed. This card is bounded to CTM after the Docling spaced-year period-end detector fix landed in 63a992ae."
---

# Extraction CTM Canary Rerun After Spaced-Year Fix V1

## Objective

Rerun only CTM document `035c6758-7aed-41a6-9e84-ad154125d431` after the
Docling spaced-year period-end detector fix landed in `63a992ae`.

Approved route:

`POST /api/process/document/{document_id}`

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION with approved bounded runtime side effects.

Intended files: this task card, runtime report bundle, and
`docs/claude/STATE.md`.

Contested surfaces touched: none by file edit. Runtime uses existing backend API
and worker surfaces.

Collision risk: HIGH because this performs financial-truth runtime extraction
and canonical backend writes for one approved document. Proceed only if registry,
queue, GPU, backend, worker, loaded-code, and route gates are clean.

Decision: proceed after validation, overlap check, registry claim, runtime
startup, and all runtime gates.

## Contract Check

Target system layers: Extraction and Storage through the backend-owned
single-document API; Evaluation/Provenance for report artifacts.

Relevant contract rules: backend is sole authority; pipeline order must not be
skipped; metric extraction may use only explicit source values; no inference,
substitution, gap filling, direct datastore mutation, alternate pipeline, or
broad backfill is allowed.

What must not change: source PDFs, parser routing, extraction prompts, gold
labels, schemas/migrations, non-CTM documents, Qdrant/news/memory stores outside
the route, Cockpit UI, GitHub state, and direct DB contents outside the backend
route.

Why safe: the retry is bounded to one pre-approved CTM document ID, uses the
backend single-document route, records fresh evidence, and stops/cleans up
dedicated canary runtime units after completion.

GPU process check required: yes, because this starts llama.cpp runtime.

## Runtime Gates

Before the CTM document POST:

- Task card validates and is claimed.
- Shared registry has no overlapping extraction/backfill/runtime job.
- `scripts/gpu_process_guard.sh --check` exits `0`.
- `nvidia-smi` shows sufficient M40 free memory.
- Backend health at `/api/health` is reachable after startup.
- Queue status at `/api/queue/status` is reachable.
- `llm_gpu` worker responds after startup.
- Worker env evidence proves `OLLAMA_URL=http://127.0.0.1:11434` is set.
- Live backend and worker code are `63a992ae` or a documented descendant.
- CTM source path still exists.
- CTM document row still exists exactly once.
- CTM is not currently queued/running/orphaned.

Stop immediately if any hard gate fails.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601.md --repo-root .`
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_ctm_canary_rerun_after_spaced_year_fix_v1_20260601.md --repo-root .`
- Registry release and final list-active.
