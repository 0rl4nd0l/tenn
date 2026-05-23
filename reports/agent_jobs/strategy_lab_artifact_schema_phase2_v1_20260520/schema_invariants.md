# Schema Invariants

## Required Defaults

All machine-generated Strategy Lab sidecar artifacts must carry:

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

These are top-level fields and must be mirrored by `storage_policy` where relevant.

## Reject

A future offline validator must reject:

- `canonical_financial_truth=true`
- `production_data_access=true`
- `may_write_db=true`
- `may_write_qdrant=true`
- `may_write_memory=true`
- `may_write_financial_truth=true`
- `execution_allowed=true`
- Missing `review_status`
- Missing `provenance`
- Missing `source_of_idea`
- Missing `data_source` for `backtest_run` or `regime_breakdown`
- Missing `benchmark` without a `DATA_MISSING` explanation
- Missing or empty `limitations`
- Missing `raw_payload_ref` when `external_engine.name=QuantDinger`
- `financial_truth` evidence label on sidecar output
- Generic `source-backed` evidence label on sidecar output
- Paper or live execution artifacts
- Broker or exchange credential fields
- Hidden order/execution fields
- QuantDinger `T`, `C`, `W`, or `N` scopes on sidecar artifacts
- `token_issued_by_this_artifact=true`

## Flag

A future offline validator should flag for human review:

- `benchmark.status=DATA_MISSING`
- `data_source.provider_status=INFERRED` or `DATA_MISSING`
- `strategy_code_hash=DATA_MISSING`
- `raw_payload_ref.sha256=DATA_MISSING`
- Regime segment `start_time` or `end_time` is null.
- Backtest metrics are present without robustness flags.
- Large inline equity curves or trade lists that should be stored as report-local refs.
- Any `local_personal_data` label without a clear holdings/personal-portfolio source explanation.

## Allowed Labels

Allowed evidence labels:

- `external_tool_context`
- `backtest_result`
- `factor_test_result`
- `regime_context`
- `risk_context`
- `portfolio_simulation`
- `context_only`
- `local_personal_data`, only when holdings/personal portfolio state are involved

Forbidden labels:

- `financial_truth`
- `source-backed` as a generic label

## Review Status

Allowed review statuses:

- `PENDING_REVIEW`
- `APPROVED_FOR_RESEARCH_CONTEXT`
- `REJECTED`
- `NEEDS_MORE_EVIDENCE`
- `FAILED_SCHEMA_VALIDATION`
- `QUARANTINED_RAW_OUTPUT`
- `PROMOTED_TO_TASK_CARD`

`human_review_decision` is Tenn-owned only. No sidecar may set or emit a final human review decision.

## Invalid Fixture Cases

- `invalid_canonical_truth_v1.json`: rejects `canonical_financial_truth=true`.
- `invalid_execution_allowed_v1.json`: rejects `execution_allowed=true` and execution flags.
- `invalid_missing_provenance_v1.json`: rejects missing `provenance`.
- `invalid_financial_truth_label_v1.json`: rejects `financial_truth` label.
- `invalid_credentials_field_v1.json`: rejects broker/exchange credential fields.
- `invalid_memory_or_financial_truth_write_v1.json`: rejects memory and financial-truth write permissions.
