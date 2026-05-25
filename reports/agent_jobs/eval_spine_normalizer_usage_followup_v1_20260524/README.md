# Eval Spine Normalizer Usage Follow-Up

Status: `complete_safe_extension`.

This child made the Gold Metric Coverage normalizer more usable and visible without runtime integration or framework expansion.

## Confirmed

- The normalizer is `scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py`.
- The current Gold Metric Coverage audit artifact is `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/metric_inventory.json`.
- That artifact uses a `summary` plus per-metric `classification` shape, not only the older direct `canonical_core`/`expanded_required` shape.
- The generated sample now preserves the real profile boundaries:
  - `canonical_core`: 10 documents, 24 metric checks, 3 eligible metrics.
  - `expanded_required`: 15 documents, 39 metric checks, 3 eligible metrics.
  - `confirmed_metric_coverage`: 146 total expectations, 73 eligible/scored expectations, 70 candidate rows, 3 ambiguous rows, 0 unsupported rows.

## Implementation

- Added `scripts/reporting/README.md` with the documented normalizer invocation and interpretation guardrails.
- Extended the normalizer to accept the current audit inventory shape while preserving the older direct input shape.
- Added tests proving current audit inventory rows normalize without turning inventory categories into accuracy claims.
- Generated report-local sample artifacts:
  - `normalized_manifest.json`
  - `scorecards.csv`
  - `metric_expectations.csv`

## DATA_MISSING

- `confirmed_metric_coverage_current_accuracy` remains missing by design because no extracted-payload scoring artifact was supplied.
- The sample is report-local/offline; it is not a Cockpit runtime display integration.

## Validation

- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest scripts/reporting/test_gold_metric_coverage_eval_spine_normalizer.py scripts/reporting/test_eval_spine_manifest.py -q`
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py scripts/reporting/test_gold_metric_coverage_eval_spine_normalizer.py`
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m scripts.reporting.gold_metric_coverage_eval_spine_normalizer --metric-inventory reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/metric_inventory.json --out-dir reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524 --task-card docs/agent_tasks/eval_spine_normalizer_usage_followup_v1_20260524.md --job-id eval_spine_normalizer_usage_followup_v1_20260524 --repo-root "$PWD"`

## No-Write Boundary

No production DB, parser, extraction, gold-label, Qdrant, news, memory, or canonical financial truth writes were performed.
