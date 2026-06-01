---
job_id: extraction_post_truth_hardening_canary_rerun_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_post_truth_hardening_canary_rerun_v1_20260601.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/README.md
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/status.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/validation.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/runtime_startup.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/preflight.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/queue_before.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/results.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/queue_after.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/runtime_shutdown.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/canary_actual_payloads.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/canary_actual_payloads_summary.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/canary_actuals_real_gold_keyed.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/source_document_rekey_summary.json
  - reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601/canary_real_gold_scorecard.json
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_post_truth_hardening_canary_rerun_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: post_truth_hardening_runtime_canary_score
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User approved full production runtime necessary to complete the extraction goal and previously approved backend/worker/GPU worker reload for the third canary. This fresh card is bounded to rerunning the same seven approved canary document IDs after commit fcbbc31e hardened AAU/AQX/ATM truth defects."
---

# Extraction Post Truth Hardening Canary Rerun V1

## Objective

Rerun the bounded seven-document canary at current backend commit `fcbbc31e`
after AAU/AQX/ATM backend truth hardening landed, then export the accepted
runtime payloads, rekey them to source-reviewed real-gold fixtures, and score
the actual payloads.

This is not broad extraction graduation. It is the next bounded runtime proof
step toward that goal.

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

- Start or reload backend on `:8000` with `DATABASE_URL=sqlite:////data/fe_local.db`.
- Start or reload the Celery worker consuming only `llm_gpu`.
- Start or reload the llama.cpp router on `:8001` if health is down and
  GPU/VRAM gates pass.
- Use the router model-load API if the extraction model is not loaded.
- Submit exactly the approved documents one at a time through the backend route.
- Stop dedicated runtime units after the run and record shutdown evidence.

Approved report-only follow-up:

- Export the selected accepted `extraction_runs.structured_json` rows.
- Rekey actual payloads by `source_document_id` to the source-reviewed fixture IDs.
- Run the real-gold scorecard over the seven canary fixtures.

Not approved:

- broad backfill
- `/process/ticker`
- direct Celery enqueue
- direct SQL mutation
- direct cleanup/deletion of prior extraction rows
- Qdrant/news/memory/manual source-PDF mutation outside the backend route
- parser routing, prompt, schema, migration, Cockpit UI, or GitHub mutation

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION with approved bounded runtime side effects.

Intended files: this task card, runtime/scorecard report bundle, and
`docs/claude/STATE.md`.

Contested surfaces touched: none by file edit. Runtime uses the existing
backend API and worker surfaces.

Collision risk: HIGH because this performs financial-truth runtime extraction
and canonical backend writes for exactly seven approved documents. The overlap
risk is controlled only if registry, queue, GPU, backend, worker, loaded-code,
source-path, document-row, and one-at-a-time submission gates are clean.

Decision: proceed after validation, overlap check, registry claim, runtime
startup, and all runtime gates.

## Contract Check

Target system layers: Extraction and Storage through the backend-owned
single-document API; Evaluation/Provenance for report artifacts.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.1 backend source of truth,
§2 mandatory flow, §3.3 explicit-only metric extraction, §3.5 normalization,
§9.4 GPU process topology, and §9.5 agent spawn protocol.

What must not change: source PDFs, parser routing, extraction prompts, gold
labels, schemas/migrations, non-approved documents, Qdrant/news/memory stores
outside the route, Cockpit UI, GitHub state, and direct DB contents outside the
backend route.

Why safe: the rerun is bounded to seven pre-approved document IDs, uses only
the backend single-document route, submits one document at a time, stops on the
first hard runtime failure, and records source-review scorecard evidence before
any broader extraction claim.

GPU process check required: yes, because this starts llama.cpp runtime and
worker extraction work.

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
- Live backend and worker code are `fcbbc31e` or a documented descendant.
- Approved source paths still exist.
- Approved document rows still exist exactly once.
- No approved document is currently queued/running/orphaned.

Stop immediately if any hard gate fails.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_post_truth_hardening_canary_rerun_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_post_truth_hardening_canary_rerun_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_post_truth_hardening_canary_rerun_v1_20260601.md --repo-root .`
- Runtime startup and preflight gates.
- One-at-a-time backend route submissions.
- Actual-payload export for accepted run IDs.
- Source-document rekey summary.
- Seven-fixture real-gold scorecard.
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_post_truth_hardening_canary_rerun_v1_20260601.md --repo-root .`
- Registry release and final active-job read-only check.
