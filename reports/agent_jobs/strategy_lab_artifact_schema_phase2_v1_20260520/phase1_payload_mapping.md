# Phase 1 Payload Mapping

## Inputs Inspected

Phase 1 bundle:

- `/home/l4nd0/tenn-strategy-lab-quantdinger-phase1-sandbox-v1-20260520/reports/agent_jobs/strategy_lab_quantdinger_phase1_sandbox_v1_20260520/README.md`
- `preflight.md`
- `runtime_footprint.md`
- `permission_token_proof.md`
- `mcp_api_observed.md`
- `backtest_payload_observed.md`
- `schema_fit_phase1.md`
- `security_risks_phase1.md`
- `go_no_go_phase2.md`
- `raw_payloads/backtest_raw.json`
- `raw_payloads/backtest_normalized_summary.json`
- `raw_payloads/regime_detect_raw.json`
- `raw_payloads/regime_detect_normalized_summary.json`
- `raw_payloads/capability_probe_raw.json`
- `raw_payloads/startup_probe_raw.json`

Prior framework/schema:

- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/artifact_schema_v1.md`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/README.md`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/task_card_outlines.md`

Phase 0 fit report:

- `/home/l4nd0/tenn-strategy-lab-quantdinger-fit-audit-v1-20260520/reports/agent_jobs/strategy_lab_quantdinger_fit_audit_v1_20260520/README.md`
- `schema_fit.md`
- `go_no_go.md`
- `permission_model.md`

## Phase 1 Confirmed Safety Inputs

- R+B-only token was issued with `paper_only=true`.
- W and T probes were denied.
- T-scope issuance was denied in hosted mode.
- No broker or exchange credentials were configured.
- No paper or live execution happened; `qd_agent_paper_orders` stayed `0`.
- No Tenn runtime, Cockpit, DB, Qdrant, news, memory, or financial-truth store was touched.
- QuantDinger containers, volumes, network, backend image, and `/tmp` sandbox were removed.
- Phase 1 final registry list-active returned `active_jobs: []`.

## Backtest Mapping

Raw payload:

- `raw_payloads/backtest_raw.json`

Normalized summary:

- `raw_payloads/backtest_normalized_summary.json`

QuantDinger request fields mapped:

| QuantDinger field | Strategy Lab field |
| --- | --- |
| `request.market` | `data_source.market`, `payload.instrument_universe[].market` |
| `request.symbol` | `data_source.symbols[]`, `payload.instrument_universe[].symbol` |
| `request.timeframe` | `data_source.timeframe`, `payload.frequency` |
| `request.start_date` | `data_source.time_range.start`, `payload.time_range.start` |
| `request.end_date` | `data_source.time_range.end`, `payload.time_range.end` |
| `request.initial_capital` | `payload.capital_base.initial_capital` |
| `request.commission` | `payload.fees_slippage.commission` |
| `request.slippage` | `payload.fees_slippage.slippage` |
| `request.leverage` | `payload.position_sizing.leverage` |
| `request.trade_direction` | `payload.position_sizing.trade_direction` |
| `request.code` | `payload.strategy_code_ref` plus `DATA_MISSING` code hash |

QuantDinger job/envelope fields mapped:

| QuantDinger field | Strategy Lab field |
| --- | --- |
| `submit.data.job_id` | `payload.external_job_id`, `provenance.run_id` |
| `final.data.kind` | `normalized_result.kind` |
| `final.data.status` | `result_status=SUCCEEDED`, `normalized_result.status` |
| `final.data.created_at` | provenance/report context |
| `final.data.started_at` | provenance/report context |
| `final.data.finished_at` | provenance/report context |
| `final.data.error` | `payload.result_error` |

Result metrics mapped:

| QuantDinger result field | Strategy Lab normalized metric |
| --- | --- |
| `totalReturn` | `total_return_pct` |
| `annualReturn` | `annualized_return_pct` |
| `maxDrawdown` | `max_drawdown_pct` |
| `sharpeRatio` | `sharpe_ratio` |
| `profitFactor` | `profit_factor` |
| `totalProfit` | `total_profit` |
| `totalTrades` | `total_trades` |
| `winRate` | `win_rate_pct` |
| `totalCommission` | `fees_slippage.total_commission` |

Equity curve representation:

- Observed path: `result.equityCurve`.
- Observed shape: array of `{time, value}` objects.
- Observed points: `11`.
- Fixture representation: inline points for this small Phase 1 payload.
- Future large runs should use `equity_curve_ref` or report-local artifact refs instead of large inline arrays.

Trades/trade summary representation:

- Observed path: `result.trades`.
- Observed rows: `2`.
- Observed row keys: `time`, `type`, `price`, `amount`, `profit`, `balance`.
- Fixture representation: count, completed trade count inferred from open/close pair, and one sample row.

Execution assumptions:

- `mtfActive=false`
- `mtfRequested=false`
- `signalTiming=next_bar_open`
- `engineVersion=strategy-backtest-v1`
- `simulationMode=standard`
- `signalTimingRaw=next_bar_open`
- `defaultFillPrice=open`
- `strategyTimeframe=1D`
- `executionTimeframe=null`

Backtest `DATA_MISSING`:

- Benchmark object and benchmark returns.
- Explicit provider field in payload.
- Strategy code hash.
- Volatility.
- Sortino.
- Turnover.
- Exposure.
- Drawdown series.
- Raw payload SHA-256 in this schema-only task.

## Regime Mapping

Raw payload:

- `raw_payloads/regime_detect_raw.json`

Normalized summary:

- `raw_payloads/regime_detect_normalized_summary.json`

Request mapping:

| QuantDinger field | Strategy Lab field |
| --- | --- |
| corrected `request.market` | `data_source.market`, `payload.instrument_universe[].market` |
| corrected `request.symbol` | `data_source.symbols[]`, `payload.instrument_universe[].symbol` |
| corrected `request.timeframe` | `data_source.timeframe`, `payload.frequency` |
| corrected `request.startDate` | `data_source.time_range.start`, `payload.time_range.start` |
| corrected `request.endDate` | `data_source.time_range.end`, `payload.time_range.end` |

Result mapping:

| QuantDinger result field | Strategy Lab field |
| --- | --- |
| `version` | `payload.regime_model`, `external_engine.version` |
| `regime` | `payload.regime`, `normalized_result.regime` |
| `label` | `payload.label`, `normalized_result.label` |
| `confidence` | `payload.confidence`, `normalized_result.confidence` |
| `features.priceChangePct` | `payload.features.price_change_pct` |
| `features.emaGapPct` | `payload.features.ema_gap_pct` |
| `features.realizedVolPct` | `payload.features.realized_vol_pct` |
| `features.atrPct` | `payload.features.atr_pct` |
| `features.directionalEfficiency` | `payload.features.directional_efficiency` |
| `features.volumeRatio` | `payload.features.volume_ratio` |
| `strategyFamilies` | `payload.strategy_families` |
| `segments[]` | `payload.segments[]` |

Regime `DATA_MISSING`:

- Explicit provider field.
- Non-null segment `startTime` / `endTime`.
- Sample size by regime.
- Exact candle count used by detector.
- Raw payload SHA-256 in this schema-only task.

## Provisional Artifact Types

- `parameter_sweep`: `DATA_MISSING`; structured tuning was not run.
- `factor_test`: `DATA_MISSING`; no factor-test endpoint or result was observed.
- `risk_report`: partial only; risk-relevant metrics exist but no dedicated risk result schema was observed.
- `portfolio_experiment`: `DATA_MISSING`; portfolio experiment routes were not exercised.
- `autonomous_opportunity_note`: Tenn-owned only; no QuantDinger authority.
- `human_review_decision`: Tenn-owned only; no sidecar authority.
