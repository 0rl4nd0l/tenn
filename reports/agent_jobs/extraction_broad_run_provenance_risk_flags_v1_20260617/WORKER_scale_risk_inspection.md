# WORKER_RESULT: Scale Risk Inspection

- Parent task: `extraction_broad_run_provenance_risk_flags_v1_20260617`
- Lane: `Evaluation`
- Worktree: `/home/l4nd0/tenn-broad-run-provenance-risk-flags-v1-20260617`
- Branch: `safe/extraction-broad-run-provenance-risk-flags-v1-20260617`
- Task status: `DONE_WITH_RISK`
- Ledger status: `DATA_MISSING`

## Files Inspected

- `docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md`
- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/provenance.py`
- `financial-engine_v2/backend/app/services/extraction_eval.py`
- `financial-engine_v2/backend/app/models/asx_financials.py`

## Recommended Schema

Use report-only broad-run fields:

```json
{
  "accepted_output_scale_magnitude_risk": {
    "accepted_output": true,
    "risk_level": "none|info|review",
    "flag_count": 0,
    "flag_codes": [],
    "flags": []
  }
}
```

Companion summary fields:

- `risk_flag_distribution`
- `risk_flagged_documents`
- `provenance_coverage.metrics_with_provenance`
- `provenance_coverage.metrics_missing_provenance`

## Recommended Rules

- `metric_exceeds_native_sanity_cap`
- `all_checked_metrics_below_minimum`
- `scale_unknown_with_metrics`
- `mixed_metric_source_scales`
- `payload_scale_differs_from_metric_source_scale`
- `metric_source_scale_missing`
- `metric_revenue_ratio_high`

These are visibility-only flags and must not feed canonical acceptance.

## Risks

- `HCW` was not found as a direct fixture in inspected harnesses; generic magnitude and scale-source rules should cover the pattern instead of hardcoding the ticker.
- Parent validation should use the repo venv because `/usr/bin/python3` lacks pytest.
