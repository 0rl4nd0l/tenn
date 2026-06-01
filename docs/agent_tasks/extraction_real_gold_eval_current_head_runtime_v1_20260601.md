---
job_id: extraction_real_gold_eval_current_head_runtime_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_real_gold_eval_current_head_runtime_v1_20260601.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/README.md
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/status.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/validation.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/preflight.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/runtime_startup.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/runtime_shutdown.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/queue_before.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/queue_after.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/source_path_probe.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/review_session_inventory_before.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/review_session_inventory_after.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_stdout.txt
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_summary.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_canonical_scorecard.json
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_documents.csv
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_metrics.csv
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_results_trust_triggers.csv
  - reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601/real_gold_eval_summary.md
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_real_gold_eval_current_head_runtime_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: real_gold_eval_current_head_runtime
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User approved full production runtime necessary to complete the extraction goal; this card is bounded to backend real-gold eval on current HEAD after the source-path resolver fix."
---

# Extraction Real-Gold Eval Current-Head Runtime V1

## Objective

Run the backend-owned real-gold extraction eval on current HEAD `8728158d34b0`
after the source-path resolver fix, using the canonical real-gold fixture corpus
and default canonical eval settings.

This is a broad evaluation proof step toward extraction graduation. It is not a
broad ticker-universe backfill and does not by itself prove full extraction
graduation across all tickers.

## Approved Scope

Approved route:

`POST /api/extraction-eval/real-gold?background=true`

Approved eval settings:

- Dataset: `financial-engine_v2/data/extraction_gold_real`
- Parser method: `docling`
- Strict method: `true`
- Limit: `0` (all canonical real-gold fixtures)
- Tolerance: `0.01`
- Backend URL: `http://127.0.0.1:8000`

Approved runtime actions:

- Start or reload the backend on `:8000` with `DATABASE_URL=sqlite:////data/fe_local.db`.
- Start or reload the llama.cpp router on `:8001` only if health is down and
  GPU/VRAM gates pass.
- Register GPU-exclusive activity for the full eval runtime.
- Use the router model-load API for `model:qwen2.5-14b-instruct` if needed.
- Run `scripts/run_real_extraction_eval.py` against the backend background eval endpoint.
- Record source-path readiness, queue status, runtime startup/shutdown,
  eval artifacts, and review-session inventory before/after.
- Stop dedicated runtime units after the run and record shutdown evidence.

Approved external runtime side effects:

- Backend-owned extraction-review artifacts under `/data/reports/extraction_review`
  if the real-gold eval creates review sessions for failed or parser-error
  documents. These artifacts must be inventoried before and after the run; do
  not delete or rewrite unrelated prior review artifacts.

Not approved:

- `POST /api/process/document/{document_id}`.
- Broad backfill or `/process/ticker`.
- Direct SQL mutation or direct Celery enqueue.
- Source PDF copy, mutation, deletion, or symlink changes.
- Parser routing, extraction prompts, schemas/migrations, fixture labels,
  canonical financial rows, Qdrant/news/memory writes, Cockpit UI, or GitHub
  mutation.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION with approved bounded runtime side effects.

Intended files: this task card, runtime/eval report bundle, and
`docs/claude/STATE.md`.

Contested surfaces touched: none by file edit. Runtime uses existing backend
real-gold eval and llama.cpp router surfaces.

Collision risk: HIGH because this performs financial-truth runtime extraction
evaluation through the backend. Proceed only if registry, queue, GPU, backend,
model, and source-path gates are clean.

Decision: proceed after validation, overlap check, registry claim, runtime
startup, and all runtime gates.

## Contract Check

Target system layers: Extraction through the backend-owned real-gold eval
route; Evaluation/Provenance for report artifacts and review-session evidence.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.1 backend source of truth,
§2 mandatory flow, §3.3 explicit-only metric extraction, §3.5 normalization,
§4 data preservation, §9.4 GPU process topology, §9.5 agent spawn protocol,
and §9.6 shared-router mutual exclusion.

What must not change: extraction logic, source PDFs, parser routing, prompts,
fixture labels, schemas/migrations, canonical stored financial rows,
Qdrant/news/memory stores, Cockpit UI, GitHub state, and any document outside
the canonical real-gold eval corpus.

Why safe: the run uses the backend-owned eval endpoint, canonical fixture
settings, an allowlisted source resolver, explicit GPU-exclusive registration,
and report-only artifacts. Any review-session artifacts are backend-owned
diagnostic output and are inventoried rather than treated as canonical truth.

GPU process check required: yes, because this starts or uses llama.cpp runtime.

## Runtime Gates

Before scheduling the eval:

- Task card validates and is claimed.
- Shared registry has no overlapping Financial Truth extraction/backfill/runtime job.
- `scripts/gpu_process_guard.sh --check` exits `0`.
- `nvidia-smi` shows sufficient M40 free memory.
- Ports `8000` and `8001` are either controlled by this task or cleanly down.
- Backend health at `/api/health` is reachable after startup.
- Queue status at `/api/queue/status` is reachable.
- Router health and `/v1/models` are reachable after startup.
- `model:qwen2.5-14b-instruct` is loaded through the router API.
- All canonical real-gold fixture source files resolve to existing files.
- Review-session inventory is captured before the run.

Stop immediately if any hard gate fails.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_eval_current_head_runtime_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_eval_current_head_runtime_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_eval_current_head_runtime_v1_20260601.md --repo-root .`
- Runtime startup and preflight gates.
- `scripts/run_real_extraction_eval.py` with canonical settings.
- Review-session inventory before/after.
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_real_gold_eval_current_head_runtime_v1_20260601.md --repo-root .`
- Registry release and final active-job read-only check.
