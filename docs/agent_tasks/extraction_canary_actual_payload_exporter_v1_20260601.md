---
job_id: extraction_canary_actual_payload_exporter_v1_20260601
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_canary_actual_payload_exporter_v1_20260601.md
  - docs/claude/STATE.md
  - docs/extraction/metric_extraction_contract.md
  - scripts/export_extraction_run_actual_payloads.py
  - scripts/test_export_extraction_run_actual_payloads.py
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/README.md
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/status.json
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/validation.json
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/function_quality_findings.json
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/canary_actual_payloads.json
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/canary_actual_payloads_summary.json
  - reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/canary_payload_scorecard_probe.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: read_only_evaluation_helper
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User asked to continue the extraction hardening handoff. This slice is non-runtime and read-only over explicit local SQLite inputs; no runtime or canonical data-store mutation is authorized."
---

# Extraction Canary Actual Payload Exporter V1

## Objective

Add a bounded, read-only helper that exports selected `extraction_runs`
`structured_json` payloads into the actual-payload map format accepted by
`scripts/extraction_gold_eval_scorecard.py --profile confirmed_metric_payload`.

This closes the evidence gap between accepted runtime canary runs and the
existing pre-persistence scorecard gate without creating gold labels, running
extraction, or mutating canonical truth.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Evaluation

Execution mode: SAFE EXTENSION.

Intended files: this task card, one script, focused script tests, metric
contract docs, report bundle, and `docs/claude/STATE.md`.

Contested surfaces touched: none.

Collision risk: LOW. The slice is read-only Evaluation tooling and does not
touch runtime services, canonical storage writes, prompts, schemas, Qdrant,
memory, Cockpit UI, or GitHub state.

Decision: proceed after task-card validation, registry overlap check, and
claim.

## Contract Check

Target system layers: Evaluation/Reporting over backend-owned extraction
artifacts.

Relevant contract rules: backend remains the source of truth; metric extraction
must not infer, substitute, or fabricate values; canonical data stores must not
be mutated by report helpers.

What must not change: extraction runtime behavior, parser routing, prompts,
schemas/migrations, source PDFs, canonical financial rows, Qdrant/news/memory
stores, Cockpit UI, and GitHub state.

Why safe: the helper reads explicitly selected extraction run rows and writes
JSON artifacts only. It does not run extraction, does not compute new metrics,
does not treat runtime outputs as gold labels, and does not authorize canonical
writes or broad backfills.

GPU process check required: no; this task does not start or depend on
llama.cpp, backend, Celery, or model runtime.

## Implementation Requirements

- Require explicit `--run-id` and/or `--document-id` selectors.
- Read SQLite only; no insert/update/delete statements.
- Fail closed when a selected run is missing, has failed status unless
  explicitly allowed, has invalid JSON, or lacks a metrics object.
- Export payloads keyed by document id by default so they can be passed directly
  as `--actuals-json`.
- Preserve provenance metadata separately from `metrics`.
- Include metric evidence maps derived only from payload evidence/provenance,
  metric evidence, row references, or source snippets already present in
  `structured_json`.
- Emit a summary artifact that records selected run ids, skipped/failed rows,
  and explicit non-authority boundaries.
- Keep outputs report-local and label them as actual payload evidence, not gold
  truth.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_canary_actual_payload_exporter_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_canary_actual_payload_exporter_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_canary_actual_payload_exporter_v1_20260601.md --repo-root .`
- Focused unit tests for the exporter.
- Export the seven accepted canary run ids from `/data/fe_local.db` to the
  report bundle.
- JSON validation for generated report artifacts.
- Probe the existing confirmed-metric payload scorecard with exported payloads
  to verify the output format is accepted and unmatched payloads block rather
  than silently pass.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_canary_actual_payload_exporter_v1_20260601.md --repo-root .`
- Registry release and final list-active.
