---
job_id: extraction_low_confidence_context_surfacing_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_low_confidence_context_surfacing_v1_20260529.md
  - reports/agent_jobs/extraction_low_confidence_context_surfacing_v1_20260529/README.md
  - reports/agent_jobs/extraction_low_confidence_context_surfacing_v1_20260529/status.json
  - reports/agent_jobs/extraction_low_confidence_context_surfacing_v1_20260529/diff-check.json
  - docs/architecture/16_currency_and_fx_policy.md
  - docs/extraction/metric_extraction_contract.md
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_context_endpoints.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_low_confidence_context_surfacing_v1_20260529
mutation_mode: safe_extension
production_data_access: false
related_issue: 96
---

# Extraction Low Confidence Context Surfacing V1

## Objective

Close the remaining report-only `ok_low_confidence` truth-surface gap before any
full accurate extraction graduation claim.

The backend context APIs must expose extraction-run low-confidence status for
persisted financial rows, not only rows whose `confidence_metrics` value falls
below the numeric threshold. This preserves the native-currency/no-FX truth
marker created by metric extraction.

## Session Declaration

- Agent: Codex.
- Branch: `safe/extraction-low-confidence-context-surfacing-v1-20260529`.
- Worktree:
  `/home/l4nd0/tenn-extraction-low-confidence-context-surfacing-v1-20260529`.
- Lane: Financial Truth.
- Execution mode: SAFE EXTENSION.
- Intended files: this task card, backend context API, focused context tests,
  extraction/currency docs, and this job's report artifacts.
- Contested surfaces touched: none from the explicit contested-surface list.
- Collision risk: MEDIUM because this changes backend financial-truth context
  output, resolved only after registry validation, overlap check, and claim.
- Decision: proceed after validation and registry claim.

## Contract Check

- Target system layers: Storage read surface, Retrieval/context API, and
  Analysis-input provenance. This does not alter ingestion, extraction,
  canonical storage, embeddings, or client UI.
- Relevant contract rules: backend remains the sole authority; non-AUD values
  must remain native/no-FX and visible as lower-confidence facts; missing or
  ambiguous truth must not be silently promoted.
- What must not change: production extraction, DB writes, Qdrant/news/memory
  mutation, source PDFs, parser routing, prompts, gold labels, runtime/model/GPU
  config, service state, schemas, migrations, Cockpit UI, or GitHub issue state.
- Why safe: the change is read-only SQL projection over existing
  `asx_periodic_financials` and `extraction_runs` rows. It adds provenance
  fields and widens low-confidence verification visibility without changing
  persisted financial values.
- GPU process check required: no. This task does not spawn, restart, stop, or
  depend on `llama-server`.

## Required Behavior

- `GET /api/context/ticker` financial rows must include the latest persistable
  extraction run status for their `source_document_id` when available.
- `latest_financial_snapshot` must include the same status fields.
- `low_confidence_financials` must include rows when either:
  - `confidence_metrics < low_confidence_threshold`, or
  - latest persistable source extraction run status is `ok_low_confidence`.
- Low-confidence rows must include a reason field distinguishing
  `metric_confidence_below_threshold` from `extraction_run_ok_low_confidence`.
- `/api/context/verification` must use the same low-confidence semantics with
  and without a ticker filter.
- Do not add schema or datastore writes.

## Hard Stops

- Do not run a third canary batch.
- Do not run broad backfill or production extraction.
- Do not perform DB writes or direct SQL mutation.
- Do not mutate Qdrant, Redis, news, memory, source PDFs, parser routing,
  extraction prompts, gold labels, runtime/model/GPU config, services, schemas,
  migrations, Cockpit UI, or GitHub state.
- Do not touch the unrelated Query Orchestration task card in the baseline
  worktree.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_low_confidence_context_surfacing_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_low_confidence_context_surfacing_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_low_confidence_context_surfacing_v1_20260529.md --repo-root .`
- Focused pytest for context endpoint low-confidence behavior.
- Targeted Ruff and `py_compile` for touched Python files.
- JSON validation for report artifacts.
- `git diff --check`.
- Source PDF/new binary staging check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_low_confidence_context_surfacing_v1_20260529.md --repo-root .`
- Code-review pass.
- Registry release and final read-only active-job check.

## Final Report Requirements

Report branch, HEAD, worktree, files changed, validation commands/results,
exact context API behavior added, confirmation that no canary/backfill/datastore
mutation ran, remaining blockers before full extraction graduation, and final
git status.
