# Mock Envelope Review

## Files

- `docs/strategy_lab/mock_payloads/mock_list_capabilities_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_market_snapshot_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_submit_backtest_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_get_job_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_regime_detect_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_policy_denied_trading_scope_v1.json`
- `docs/strategy_lab/mock_payloads/mock_sidecar_unavailable_v1.json`
- `docs/strategy_lab/mock_payloads/mock_schema_invalid_v1.json`
- `docs/strategy_lab/mock_payloads/mock_missing_benchmark_result_v1.json`
- `docs/strategy_lab/mock_payloads/mock_data_missing_result_v1.json`

## Coverage

The mock payloads cover:

- List capabilities request/result.
- Read market snapshot request/result.
- Submit backtest request/result.
- Job polling request/result.
- Regime detect request/result.
- Sidecar unavailable result.
- Schema-invalid result.
- Policy-denied trading-scope result.
- Missing benchmark result.
- `DATA_MISSING` result for held structured tuning / parameter sweep.

## Envelope Checks

Every mock payload includes:

- `mock_envelope_version`.
- `request`.
- `policy_decision`.
- `status`.
- `result`.
- `raw_payload_ref`.
- `artifact_mapping`.
- `quarantine`.
- `audit_log`.

Every request includes:

- `production_data_access=false`.
- `paper_live_scope=none`, except the denied trading fixture intentionally shows a forbidden requested `paper` scope.
- `mock_scope=phase3a_design_only`.

## Artifact Mapping

- `mock_get_job_result_v1.json` maps to `backtest_run` with explicit `DATA_MISSING` fields.
- `mock_regime_detect_result_v1.json` maps to `regime_breakdown` with explicit `DATA_MISSING` fields.
- `mock_submit_backtest_result_v1.json` does not emit an artifact at submission.
- `mock_market_snapshot_result_v1.json` does not emit an artifact by default.
- `mock_missing_benchmark_result_v1.json` documents when explicit benchmark `DATA_MISSING` permits pending-review mapping.
- `mock_schema_invalid_v1.json` emits no artifact and is quarantined.
- `mock_policy_denied_trading_scope_v1.json` emits no artifact and is quarantined.
- `mock_data_missing_result_v1.json` emits no artifact and holds `parameter_sweep`.

## Limitations

- Mock payloads are design fixtures only.
- Raw payload hashes are `DATA_MISSING`.
- No JSON Schema validator was added.
- No real adapter/client exists.
- No external service was called.
