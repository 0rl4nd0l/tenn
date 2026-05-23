# Helper Mapping Coverage

## Reconciled Rule

The 2026-05-21 helper is accepted only as `pending_review_pre_envelope_only`.

- Helper schema: `strategy_lab_sidecar_artifact_v1`.
- Authoritative schema: `strategy_lab_artifact_v1`.
- Helper replacement of authoritative envelope: denied.
- Allowed outcomes: full-envelope mapping or quarantine/pre-envelope only.

## Mapped Evidence-Backed Cases

| Helper artifact type | Target artifact type | Target fixture | Result |
| --- | --- | --- | --- |
| `backtest_run` | `backtest_run` | `docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json` | Covered |
| `regime_breakdown` | `regime_breakdown` | `docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json` | Covered |

The tests assert that mapped targets contain the full authoritative envelope:

- `artifact_id`, `artifact_type`, `job_id`, `created_at`, `created_by`, `tenant_scope`
- `source_of_idea`, `external_engine`, `provenance`, `parameters`, `assumptions`
- `data_source`, `benchmark` or explicit `DATA_MISSING`, `limitations`, `result_status`
- `evidence_label`, `evidence_labels`, `review_status`, `data_missing`
- `payload`, `raw_payload_ref`, `normalized_result`, `storage_policy`, `validation`, `security_policy`

## Quarantined Helper Case

The vector `helper_compact_envelope_without_mapping_is_not_authoritative` proves that compact helper output with `observations` is quarantined if promoted without the full authoritative fields.

## Held Cases

The following helper-declared types remain held or `DATA_MISSING`:

- `parameter_sweep`
- `risk_report`
- `factor_test`
- `portfolio_experiment`
