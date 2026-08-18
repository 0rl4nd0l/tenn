# Reporting Scripts

## Gold Metric Coverage to Eval Spine

Use `gold_metric_coverage_eval_spine_normalizer.py` to convert a Gold Metric Coverage `metric_inventory.json` into report-local Eval Spine artifacts:

```bash
/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m scripts.reporting.gold_metric_coverage_eval_spine_normalizer \
  --metric-inventory reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/metric_inventory.json \
  --out-dir reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524 \
  --task-card docs/agent_tasks/eval_spine_normalizer_usage_followup_v1_20260524.md \
  --job-id eval_spine_normalizer_usage_followup_v1_20260524 \
  --repo-root "$PWD"
```

Outputs:

- `normalized_manifest.json`
- `scorecards.csv`
- `metric_expectations.csv`

Interpretation rules:

- `canonical_core` is the narrow no-regression scorecard profile, not a broad accuracy claim.
- `expanded_required` is the required-metric profile where available.
- `confirmed_metric_coverage` is breadth inventory only.
- `confirmed_unscored`, `schema_supported_but_not_labelled`, `extractor_output_but_not_gold`, `ambiguous_or_derived`, and `unsupported` rows are not accuracy claims.

The normalizer is offline/report-local. It does not write production databases, gold labels, parser outputs, Qdrant, news, memory, or canonical financial truth.
