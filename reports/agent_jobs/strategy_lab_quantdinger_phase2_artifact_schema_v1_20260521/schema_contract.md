# Schema Contract

## Implemented

- Offline schema version: `strategy_lab_sidecar_artifact_v1`
- Source system accepted by this adapter: `QuantDinger`
- Source role: `external_sidecar_comparator`
- Review state: `PENDING_REVIEW`
- Runtime authority: none
- Store write authority: none
- Execution authority: none

## Required Guardrails

The validator rejects artifacts unless these top-level fields are literal `false`:

- `canonical_financial_truth`
- `production_data_access`
- `may_write_db`
- `may_write_qdrant`
- `may_write_memory`
- `may_write_financial_truth`
- `execution_allowed`

The validator also rejects provenance blocks unless these fields are literal `false`:

- `production_data_access`
- `credential_use`
- `broker_exchange_setup`
- `paper_or_live_execution`
- `tenn_store_write`

## Observed Phase 1 Payload Mapping

`backtest_run` maps:

- metrics: `metrics`
- equity curve shape: `equity_curve_shape`
- trade summary shape: `trade_summary_shape`
- benchmark fields: `benchmark_fields`
- fees/slippage fields: `fees_slippage_fields`
- data source fields: `data_source_fields`
- execution assumptions: `execution_assumption_fields`
- job polling: `poll_count`, `poll_statuses`

`regime_breakdown` maps:

- regime label: `regime`, `label`
- confidence: `confidence`
- feature values: `features`
- feature names: `feature_keys`
- segment shape: `segment_shape`
- strategy families: `strategy_families`
- bounded endpoint behavior: `attempt_count`, `first_attempt_error`, `http_status`

## DATA_MISSING

No Phase 1 payload was captured for:

- `parameter_sweep`
- `risk_report`
- `factor_test`
- `portfolio_experiment`

Those types are declared only as schema surface. They must not be populated from assumptions.
