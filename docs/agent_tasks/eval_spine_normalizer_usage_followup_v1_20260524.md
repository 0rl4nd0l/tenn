---
job_id: eval_spine_normalizer_usage_followup_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/eval_spine_normalizer_usage_followup_v1_20260524.md
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/README.md
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/status.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/normalized_manifest.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/scorecards.csv
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/metric_expectations.csv
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/validation.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/diff-check.json
  - scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py
  - scripts/reporting/test_gold_metric_coverage_eval_spine_normalizer.py
  - scripts/reporting/README.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Eval Spine Normalizer Usage Follow-up

## Objective

Make the canonical Gold Metric Coverage normalizer under `scripts/reporting/` usable and visible without broad framework creep.

## Required Audit

- Locate the normalizer script, tests, output schema, Eval Spine scaffold, and docs.
- Determine whether the smallest safe extension is README command coverage, report-local sample output, wrapper, tests, status/manifest wiring, Cockpit display plan, or task-card template.

## Required Semantics

- `canonical_core` remains the narrow 10-document / 24-check no-regression proof.
- `expanded_required` remains the 15-document / 39-check proof where available.
- `confirmed_metric_coverage` is read-only breadth inventory, not current accuracy proof.
- `confirmed_unscored` and `schema_supported_but_not_labelled` are not accuracy claims.

## Forbidden

- No production DB writes, parser/extraction edits, gold-label rewrites, canonical truth writes, broad Eval Spine framework rewrite, or claim that inventory equals accuracy.

## Validation

- Focused normalizer tests.
- Report-local sample artifact generation.
- JSON/CSV validation.
- `git diff --check`.
- Task-card `check-diff`.
