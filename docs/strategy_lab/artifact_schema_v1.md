# Strategy Lab Artifact Schema v1

Status: schema-only design.

Scope: QuantDinger and other external research sidecars may produce pending-review Strategy Lab artifacts. These artifacts are evidence/provenance objects only. They are not Tenn canonical financial truth, not memory, not holdings state, not watchlist priority, and not execution instructions.

## Boundary

- Tenn remains the research brain and evidence/provenance authority.
- QuantDinger is a replaceable external read/backtest sidecar/comparator.
- QuantDinger outputs become Strategy Lab artifacts, never canonical financial truth.
- Machine-generated sidecar artifacts default to `review_status=PENDING_REVIEW`.
- No artifact may affect memory, watchlist priority, company analysis, thesis state, holdings, or financial truth without later human review and a separately approved task card.
- Codex is a dev/audit agent only, not the runtime path.

## Envelope

Every artifact uses the same envelope. Type-specific data goes in `payload`; normalized cross-type summaries go in `normalized_result`; raw external outputs are referenced by `raw_payload_ref`.

Required envelope fields:

- `schema_version`: `strategy_lab_artifact_v1`.
- `artifact_id`: stable Strategy Lab artifact id, for example `stratlab_backtest_run_20260520_phase1_btc_usdt_sma_cross`.
- `artifact_type`: one allowed type from this document.
- `job_id`: Tenn task/job id that created the artifact or fixture.
- `created_at`: ISO-8601 UTC timestamp.
- `created_by`: `Codex`, `Tenn`, `human`, or a future approved service id.
- `tenant_scope`: `local_host` unless a later tenant model is approved.
- `source_of_idea`: Tenn-owned origin metadata.
- `external_engine`: sidecar/tool metadata; `name=QuantDinger` for Phase 1 mapped artifacts.
- `provenance`: source/report/run lineage.
- `parameters`: run or idea parameters.
- `assumptions`: explicit assumptions, including fees, slippage, signal timing, and provider inferences.
- `data_source`: provider, market, symbol, timeframe, and time range.
- `benchmark`: benchmark metadata or `DATA_MISSING` with explanation.
- `limitations`: non-empty list.
- `result_status`: normalized result status.
- `evidence_label`: primary evidence label.
- `evidence_labels`: all evidence labels.
- `review_status`: human-review state; defaults to `PENDING_REVIEW`.
- `data_missing`: explicit missing fields or evidence.
- `payload`: artifact-type-specific data.
- `raw_payload_ref`: pointer to saved raw external payload when an external engine is used.
- `normalized_result`: normalized summary derived from raw payload.
- `storage_policy`: approved storage/write policy.
- `validation`: parse and invariant-check metadata.
- `security_policy`: execution, token, credential, and hidden-field policy.

Mandatory top-level safety/truth flags on every machine-generated sidecar artifact:

```json
{
  "canonical_financial_truth": false,
  "production_data_access": false,
  "may_write_db": false,
  "may_write_qdrant": false,
  "may_write_memory": false,
  "may_write_financial_truth": false,
  "execution_allowed": false,
  "review_status": "PENDING_REVIEW"
}
```

The same write prohibitions are also mirrored in `storage_policy` so future validators can catch either envelope-level or policy-level drift.

## Artifact Types

Allowed `artifact_type` values:

- `strategy_idea`
- `backtest_run`
- `parameter_sweep`
- `factor_test`
- `regime_breakdown`
- `risk_report`
- `portfolio_experiment`
- `autonomous_opportunity_note`
- `human_review_decision`

Phase 1 evidence is strong enough to map `backtest_run` and `regime_breakdown`. `strategy_idea` is Tenn-owned and may exist without a sidecar run. `parameter_sweep`, `factor_test`, `risk_report`, and `portfolio_experiment` remain provisional unless later payload evidence fills the `DATA_MISSING` fields.

`human_review_decision` is Tenn-owned only. QuantDinger and other sidecars must not emit final review decisions.

## Evidence Labels

Allowed labels for Strategy Lab sidecar artifacts:

- `external_tool_context`
- `backtest_result`
- `factor_test_result`
- `regime_context`
- `risk_context`
- `portfolio_simulation`
- `context_only`
- `local_personal_data`, only when holdings or personal portfolio state are involved

Forbidden labels for QuantDinger/Strategy Lab sidecar output:

- `financial_truth`
- `source-backed` as a generic claim-verification label unless a specific claim is verified by source evidence in a later approved schema.

`financial_truth` is never valid on machine-generated sidecar artifacts.

## Review Workflow

Allowed `review_status` values:

- `PENDING_REVIEW`: default for all sidecar artifacts.
- `APPROVED_FOR_RESEARCH_CONTEXT`: human approved for research context only.
- `REJECTED`: human rejected or invalidated.
- `NEEDS_MORE_EVIDENCE`: schema is coherent but evidence is insufficient.
- `FAILED_SCHEMA_VALIDATION`: offline validator rejected the artifact.
- `QUARANTINED_RAW_OUTPUT`: raw payload is retained but not trusted for normal Strategy Lab display.
- `PROMOTED_TO_TASK_CARD`: human chose to create a new Tenn task card.

Promotion to memory, financial truth, holdings, watchlist priority, company analysis, thesis state, execution, paper trading, or live trading is not represented in this workflow. Any such action requires a later task card and a different schema.

## Phase 1 Payload Mapping

### Backtest Run

Observed raw payload reference:

- Source report bundle: `/home/l4nd0/tenn-strategy-lab-quantdinger-phase1-sandbox-v1-20260520/reports/agent_jobs/strategy_lab_quantdinger_phase1_sandbox_v1_20260520`
- Raw payload: `raw_payloads/backtest_raw.json`
- Normalized summary: `raw_payloads/backtest_normalized_summary.json`

Required `backtest_run` payload fields:

- `strategy_id`
- `backtest_id`
- `external_job_id`
- `engine_run_id`
- `strategy_code_ref`
- `strategy_code_hash`
- `instrument_universe`
- `time_range`
- `frequency`
- `capital_base`
- `position_sizing`
- `fees_slippage`
- `metrics`
- `trade_summary`
- `equity_curve`
- `execution_assumptions`
- `benchmark_comparison`
- `robustness_flags`
- `result_error`

Observed QuantDinger fields mapped:

- `job_id`: `7f41134d04464e73bcadee86ff58ab6f`
- `kind`: `backtest`
- `status`: `succeeded`
- request `market`: `Crypto`
- request `symbol`: `BTC/USDT`
- request `timeframe`: `1D`
- request `start_date`: `2026-05-10`
- request `end_date`: `2026-05-20`
- request `initial_capital`: `1000`
- request `commission`: `0.001`
- request `slippage`: `0`
- request `leverage`: `1`
- request `trade_direction`: `long`
- metrics: `annualReturn`, `maxDrawdown`, `profitFactor`, `sharpeRatio`, `totalCommission`, `totalProfit`, `totalReturn`, `totalTrades`, `winRate`
- equity curve: `result.equityCurve`, 11 points with `time` and `value`
- trades: `result.trades`, 2 rows with `time`, `type`, `price`, `amount`, `profit`, and `balance`
- execution assumptions: `mtfActive`, `mtfRequested`, `signalTiming`, `engineVersion`, `simulationMode`, `signalTimingRaw`, `defaultFillPrice`, `strategyTimeframe`, `executionTimeframe`

Backtest `DATA_MISSING`:

- Benchmark object and benchmark returns.
- Explicit upstream market-data provider field; `CryptoKline` was inferred from backend logs, not emitted by the payload.
- Strategy code hash.
- Volatility, Sortino, turnover, exposure, drawdown series, and benchmark comparison.
- Raw payload hash in this schema-only job.

### Regime Breakdown

Observed raw payload reference:

- Source report bundle: `/home/l4nd0/tenn-strategy-lab-quantdinger-phase1-sandbox-v1-20260520/reports/agent_jobs/strategy_lab_quantdinger_phase1_sandbox_v1_20260520`
- Raw payload: `raw_payloads/regime_detect_raw.json`
- Normalized summary: `raw_payloads/regime_detect_normalized_summary.json`

Required `regime_breakdown` payload fields:

- `regime_model`
- `classification_source`
- `instrument_universe`
- `time_range`
- `frequency`
- `regime`
- `label`
- `confidence`
- `features`
- `segments`
- `strategy_families`
- `sample_size_by_regime`
- `regime_transition_notes`
- `result_error`

Observed QuantDinger fields mapped:

- request `market`: `Crypto`
- request `symbol`: `BTC/USDT`
- request `timeframe`: `1D`
- corrected request `startDate`: `2026-04-05`
- corrected request `endDate`: `2026-05-20`
- failed first attempt: snake_case `start_date`/`end_date`, error `time data 'None' does not match format '%Y-%m-%d'`
- result `version`: `market-regime-v1`
- result `regime`: `high_volatility`
- result `label`: `High Volatility`
- result `confidence`: `0.99`
- features: `priceChangePct`, `emaGapPct`, `realizedVolPct`, `atrPct`, `directionalEfficiency`, `volumeRatio`
- segments: one segment with `regime`, `label`, `confidence`, `startTime=null`, `endTime=null`
- strategy families: `volatility_breakout`, `reduced_risk_trend`, `event_drive`

Regime `DATA_MISSING`:

- Explicit provider field.
- Non-null segment start/end times.
- Sample-size by regime.
- Exact candle count used by regime detector.
- Raw payload hash in this schema-only job.

## Schema Invariants

The schema and any future offline validator must reject or flag:

- `canonical_financial_truth=true`
- `production_data_access=true`
- `may_write_db=true`
- `may_write_qdrant=true`
- `may_write_memory=true`
- `may_write_financial_truth=true`
- `execution_allowed=true`
- `review_status` missing
- `provenance` missing
- `source_of_idea` missing
- `data_source` missing for `backtest_run` or `regime_breakdown`
- `benchmark` missing without a `DATA_MISSING` explanation
- `limitations` missing or empty
- `raw_payload_ref` missing when `external_engine.name=QuantDinger`
- `financial_truth` evidence label on sidecar output
- `source-backed` generic evidence label
- paper or live execution artifacts
- broker or exchange credential fields
- hidden order, trade execution, broker account, or exchange account fields
- QuantDinger `T`, `C`, `W`, or `N` scopes on sidecar artifacts

## Validator Contract

This Phase 2 job does not implement runtime validation code. A future offline validator should:

1. Parse JSON and validate against `docs/strategy_lab/artifact_schema_v1.schema.json`.
2. Enforce the schema invariants above even when a field is nested inside `payload`, `parameters`, or `normalized_result`.
3. Require `DATA_MISSING` entries for missing benchmark/provider/sample-size/source fields.
4. Require `raw_payload_ref.path` and `raw_payload_ref.source_report_path` for QuantDinger artifacts.
5. Reject `financial_truth` and generic `source-backed` labels.
6. Reject hidden credential or execution fields by recursive key scan.
7. Verify every machine-generated sidecar artifact remains `PENDING_REVIEW` unless a Tenn-owned `human_review_decision` artifact changes review state.
8. Emit validation output as a report artifact only; do not write Tenn DB, Qdrant, memory, financial-truth, parser, extraction, gold-label, Cockpit, or runtime state.

## Fixtures

Valid fixtures:

- `artifact_fixtures/valid_backtest_run_v1.json`
- `artifact_fixtures/valid_regime_breakdown_v1.json`
- `artifact_fixtures/valid_strategy_idea_v1.json`

Invalid fixtures:

- `artifact_fixtures/invalid_canonical_truth_v1.json`
- `artifact_fixtures/invalid_execution_allowed_v1.json`
- `artifact_fixtures/invalid_missing_provenance_v1.json`
- `artifact_fixtures/invalid_financial_truth_label_v1.json`
- `artifact_fixtures/invalid_credentials_field_v1.json`
- `artifact_fixtures/invalid_memory_or_financial_truth_write_v1.json`
