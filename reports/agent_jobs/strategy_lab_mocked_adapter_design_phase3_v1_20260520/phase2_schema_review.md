# Phase 2 Schema Review

## Inputs Inspected

Phase 2:

- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/docs/strategy_lab/artifact_schema_v1.md`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/docs/strategy_lab/artifact_schema_v1.schema.json`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/docs/strategy_lab/artifact_fixtures/`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/README.md`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/phase1_payload_mapping.md`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/schema_invariants.md`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/validation_notes.md`
- `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520/reports/agent_jobs/strategy_lab_artifact_schema_phase2_v1_20260520/go_no_go_phase3.md`

Phase 1:

- `/home/l4nd0/tenn-strategy-lab-quantdinger-phase1-sandbox-v1-20260520/reports/agent_jobs/strategy_lab_quantdinger_phase1_sandbox_v1_20260520/README.md`
- `permission_token_proof.md`
- `mcp_api_observed.md`
- `backtest_payload_observed.md`
- `schema_fit_phase1.md`
- `security_risks_phase1.md`
- `raw_payloads/*`

Phase 0:

- `/home/l4nd0/tenn-strategy-lab-quantdinger-fit-audit-v1-20260520/reports/agent_jobs/strategy_lab_quantdinger_fit_audit_v1_20260520/go_no_go.md`

## Confirmed Phase 2 Facts

- Phase 2 recommended `GO_PHASE3_MOCKED_ADAPTER_DESIGN_ONLY`.
- The artifact schema is a schema-only design, not runtime validation code.
- Allowed artifact types include `backtest_run`, `parameter_sweep`, `factor_test`, `regime_breakdown`, `risk_report`, `portfolio_experiment`, `strategy_idea`, `autonomous_opportunity_note`, and `human_review_decision`.
- Phase 1 evidence was strong enough for `backtest_run` and `regime_breakdown`.
- `parameter_sweep`, `factor_test`, `portfolio_experiment`, and broader risk output remained provisional or `DATA_MISSING`.
- `human_review_decision` is Tenn-owned only.
- Sidecar artifacts default to `PENDING_REVIEW`.

## Required Invariants Carried Forward

All sidecar-derived artifacts must preserve:

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

Phase 3A design preserves these invariants in the adapter contract, tool policy, mock envelopes, and test plan.

## Evidence-Mapped Outputs

`backtest_run`:

- Supported by Phase 1 backtest job with metrics, equity curve, trades, and execution assumptions.
- Requires explicit `DATA_MISSING` for benchmark, provider, strategy code hash, raw hash, and robustness gaps.

`regime_breakdown`:

- Supported by Phase 1 regime detect result with model version, label, confidence, features, segment shape, and strategy families.
- Requires explicit `DATA_MISSING` for provider, segment start/end times, sample size, candle count, and raw hash.

`parameter_sweep`:

- Held as `DATA_MISSING`; structured tuning route existed but was not run.

`risk_report`:

- Provisional/context only; backtest metrics include risk-adjacent fields but no dedicated risk schema was observed.

`strategy_idea`:

- Tenn/human-origin only. Sidecar may provide context but must not decide truth.

`human_review_decision`:

- Tenn-owned only. Sidecar must never emit it.

## DATA_MISSING

- Live MCP transport schemas.
- Structured tuning result shape.
- Experiment pipeline result shape.
- AI optimization shape.
- Benchmark fields for backtests.
- Explicit data provider field in backtest/regime results.
- Exact QuantDinger audit retention policy.
- Exact controls to disable all nonessential background workers.
- Exact GHCR image-to-source commit provenance.
- Raw payload hashes for schema-only/design-only outputs.
