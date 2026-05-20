# Strategy Lab Artifact Schema v1

Status: design proposal only
Canonical financial truth: no
Production data access: false by default

## 1. Common Envelope

All Strategy Lab artifacts use this envelope. Type-specific payloads live in `payload`.

```json
{
  "schema_version": "strategy_lab_artifact_v1",
  "artifact_id": "stratlab_<type>_<date>_<stable_hash>",
  "artifact_type": "strategy_idea | backtest_run | parameter_sweep | factor_test | regime_breakdown | risk_report | portfolio_experiment | autonomous_opportunity_note | human_review_decision",
  "job_id": "strategy_lab_quantdinger_framework_v1_20260520",
  "created_at": "ISO-8601 UTC",
  "created_by": "tenn_orchestrator | human | external_sidecar",
  "tenant_scope": "local_host",
  "production_data_access": false,
  "canonical_financial_truth": false,
  "source_of_idea": {
    "origin": "human_prompt | watchlist_scan | thesis | company_memory | market_memory | external_tool | report",
    "source_ref": "string or DATA_MISSING",
    "prompt_or_summary": "string",
    "source_evidence_ids": []
  },
  "external_engine": {
    "name": "QuantDinger | DATA_MISSING",
    "version": "string or DATA_MISSING",
    "transport": "none | rest | mcp_stdio | mcp_http | DATA_MISSING",
    "base_url_ref": "redacted local ref or DATA_MISSING",
    "tool_name": "string or DATA_MISSING",
    "tool_scope": ["R", "B"],
    "token_scope": ["R", "B"],
    "live_trading_enabled": false,
    "paper_execution_enabled": false
  },
  "provenance": {
    "input_artifact_ids": [],
    "source_documents": [],
    "source_urls": [],
    "data_source_refs": [],
    "run_id": "string or DATA_MISSING",
    "raw_result_ref": "path or DATA_MISSING",
    "code_hash": "string or DATA_MISSING",
    "config_hash": "string or DATA_MISSING",
    "generated_by_tool": "string or DATA_MISSING"
  },
  "parameters": {},
  "assumptions": [],
  "data_source": {
    "provider": "string",
    "market": "string",
    "symbols": [],
    "time_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
    "frequency": "string",
    "adjustments": [],
    "survivorship_bias_handled": "yes | no | DATA_MISSING",
    "fees_slippage_model": "string or DATA_MISSING"
  },
  "benchmark": {
    "name": "string or DATA_MISSING",
    "symbol": "string or DATA_MISSING",
    "method": "string or DATA_MISSING"
  },
  "limitations": [],
  "result_status": "NOT_RUN | RUNNING | COMPLETE | FAILED | DATA_MISSING | BLOCKED",
  "evidence_label": "external_tool_context",
  "evidence_labels": ["external_tool_context"],
  "review_status": "PENDING_REVIEW",
  "data_missing": [],
  "payload": {},
  "storage_policy": {
    "write_target": "reports/strategy_lab or approved report bundle",
    "may_write_db": false,
    "may_write_qdrant": false,
    "may_write_memory": false,
    "may_write_financial_truth": false
  }
}
```

## 2. Strategy Idea Payload

Required payload fields:

- `idea_id`
- `hypothesis`
- `universe`
- `entry_logic`
- `exit_logic`
- `risk_controls`
- `expected_holding_period`
- `research_question`
- `why_now`
- `known_counterarguments`
- `minimum_evidence_needed`

Default result status: `NOT_RUN`.

## 3. Backtest Run Payload

Required payload fields:

- `strategy_id`
- `backtest_id`
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
- `equity_curve_ref`
- `drawdown_ref`
- `benchmark_comparison`
- `robustness_flags`

Required metrics:

- `total_return`
- `annualized_return`
- `volatility`
- `max_drawdown`
- `sharpe`
- `sortino`
- `win_rate`
- `turnover`
- `trade_count`
- `exposure`

Default evidence labels: `external_tool_context`, `backtest_result`.

## 4. Parameter Sweep Payload

Required payload fields:

- `strategy_id`
- `sweep_id`
- `search_method`
- `parameter_grid`
- `objective_metric`
- `constraints`
- `run_count`
- `top_results`
- `full_results_ref`
- `overfit_risk`
- `sensitivity_summary`

Default evidence labels: `external_tool_context`, `parameter_sweep_result`.

## 5. Factor Test Payload

Required payload fields:

- `factor_id`
- `factor_definition`
- `universe`
- `rebalance_frequency`
- `sort_method`
- `quantile_count`
- `forward_return_windows`
- `information_coefficient`
- `quantile_spreads`
- `turnover`
- `capacity_notes`
- `correlation_to_existing_factors`

Default evidence labels: `external_tool_context`, `factor_test_result`.

## 6. Regime Breakdown Payload

Required payload fields:

- `regime_model`
- `regime_definitions`
- `classification_source`
- `time_range`
- `strategy_or_factor_ref`
- `performance_by_regime`
- `sample_size_by_regime`
- `regime_transition_notes`
- `limitations`

Default evidence labels: `external_tool_context`, `regime_context`.

## 7. Risk Report Payload

Required payload fields:

- `subject_ref`
- `risk_model`
- `drawdown_analysis`
- `volatility_analysis`
- `tail_events`
- `liquidity_constraints`
- `concentration`
- `correlation`
- `scenario_tests`
- `risk_limits`
- `breach_flags`
- `mitigations`

Default evidence labels: `external_tool_context`, `risk_context`.

## 8. Portfolio Experiment Payload

Required payload fields:

- `portfolio_experiment_id`
- `base_portfolio_ref`
- `proposed_changes`
- `rebalance_method`
- `constraints`
- `input_holdings_source`
- `simulation_method`
- `expected_return_assumptions`
- `risk_assumptions`
- `outputs`
- `comparison_to_current`
- `operator_notes`

Default evidence labels: `external_tool_context`, `portfolio_simulation`, `local_personal_data` when user holdings are involved.

## 9. Autonomous Opportunity Note Payload

Required payload fields:

- `opportunity_id`
- `trigger`
- `watchlist_scope`
- `thesis_or_signal`
- `supporting_evidence_refs`
- `contrary_evidence_refs`
- `suggested_next_test`
- `forbidden_actions_checked`
- `confidence`
- `review_priority`

Default evidence labels: `external_tool_context`, `context_only`.

## 10. Human Review Decision Payload

Required payload fields:

- `review_id`
- `reviewer`
- `reviewed_artifact_ids`
- `decision`
- `decision_reason`
- `required_followup`
- `allowed_next_phase`
- `blocked_surfaces`
- `memory_write_allowed`
- `financial_truth_write_allowed`
- `execution_allowed`

Allowed `decision` values:

- `APPROVED_FOR_RESEARCH`
- `REJECTED`
- `NEEDS_MORE_EVIDENCE`
- `PROMOTED_TO_TASK_CARD`
- `BLOCKED_BOUNDARY_RISK`

The only allowed truth flags for this schema are:

- `memory_write_allowed=false`
- `financial_truth_write_allowed=false`
- `execution_allowed=false`

Any true value requires a separate future task card and schema revision.
