---
job_id: gold_metric_coverage_eval_spine_normalizer_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/gold_metric_coverage_eval_spine_normalizer_v1_20260524.md
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/README.md
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/status.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/validation.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/normalized_manifest.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/scorecards.csv
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/metric_expectations.csv
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/diff-check.json
  - scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py
  - scripts/reporting/test_gold_metric_coverage_eval_spine_normalizer.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Gold Metric Coverage Eval Spine Normalizer

## Objective

Add a narrow offline `scripts/reporting` normalizer that converts Gold Metric Coverage audit artifacts into Eval Spine-compatible report-local JSON/CSV artifacts without changing parser, extraction, gold labels, canonical truth, or production stores.

## Required Semantics

- `canonical_core` is the 10-document / 24-check strict no-regression profile only.
- `expanded_required` is the 15-document / 39-check proof where available.
- `confirmed_metric_coverage` is read-only breadth inventory, not current accuracy proof.
- `confirmed_unscored` and `schema_supported_but_not_labelled` are not accuracy claims.

## Forbidden

- No extraction logic edits, parser routing, prompt edits, gold-label rewrites, canonical writes, production DB writes, or claims that breadth inventory is current accuracy.

## Validation

- Validate this task card.
- Run focused normalizer tests.
- Run the normalizer on a report-local/prior artifact input and validate output JSON/CSV.
- Run `git diff --check`.
