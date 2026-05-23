# Strategy Lab Adapter Request/Response Envelopes v1

Status: design-only mock envelopes.

The JSON files under `docs/strategy_lab/mock_payloads/` are mock fixtures only. They are not real sidecar responses, not adapter implementation, not an artifact store, and not evidence of a running QuantDinger or MCP service.

## Common Request Shape

```json
{
  "request_id": "toolreq_phase3a_example",
  "job_id": "strategy_lab_mocked_adapter_design_phase3_v1_20260520",
  "requested_by": "Tenn",
  "operation": "read_market_snapshot",
  "mock_scope": "phase3a_design_only",
  "production_data_access": false,
  "execution_allowed": false,
  "paper_live_scope": "none",
  "input": {},
  "source_of_idea": {
    "origin": "human_or_tenn",
    "sidecar_may_decide_truth": false
  },
  "policy_context": {
    "policy_version": "strategy_lab_tool_policy_v1",
    "tenant_scope": "local_host",
    "forbidden_surfaces": ["credentials", "paper_orders", "live_orders", "tenn_store_writes"]
  },
  "audit_context": {
    "trace_id": "trace_phase3a_example",
    "task_card": "docs/agent_tasks/strategy_lab_mocked_adapter_design_phase3_v1_20260520.md"
  }
}
```

## Common Result Shape

```json
{
  "request_id": "toolreq_phase3a_example",
  "operation": "read_market_snapshot",
  "policy_decision": {
    "decision": "allow_mock_only",
    "reason_codes": ["PHASE3A_DESIGN_ONLY"]
  },
  "status": "succeeded",
  "raw_payload_ref": {
    "storage_state": "mock_ref_only",
    "path": "docs/strategy_lab/mock_payloads/example.json",
    "sha256": "DATA_MISSING",
    "redaction_status": "no_secrets_expected",
    "quarantine_status": "not_quarantined_mock"
  },
  "result": {},
  "artifact_mapping": {
    "artifact_emitted": false,
    "artifact_type": null
  },
  "quarantine": {
    "quarantined": false,
    "reason_codes": []
  },
  "audit_log": {}
}
```

## Mock Examples

| Example | Fixture |
| --- | --- |
| Mock list capabilities request/result | `mock_payloads/mock_list_capabilities_result_v1.json` |
| Mock read market snapshot request/result | `mock_payloads/mock_market_snapshot_result_v1.json` |
| Mock submit backtest request/result | `mock_payloads/mock_submit_backtest_result_v1.json` |
| Mock job polling request/result | `mock_payloads/mock_get_job_result_v1.json` |
| Mock regime detect request/result | `mock_payloads/mock_regime_detect_result_v1.json` |
| Mock sidecar unavailable result | `mock_payloads/mock_sidecar_unavailable_v1.json` |
| Mock schema-invalid result | `mock_payloads/mock_schema_invalid_v1.json` |
| Mock policy-denied trading-scope result | `mock_payloads/mock_policy_denied_trading_scope_v1.json` |
| Mock missing benchmark result | `mock_payloads/mock_missing_benchmark_result_v1.json` |
| Mock DATA_MISSING result | `mock_payloads/mock_data_missing_result_v1.json` |

## Envelope Rules

- Every request must include `production_data_access=false`.
- Every request must include `execution_allowed=false`.
- Every request must include `paper_live_scope=none`.
- Every result must include a `policy_decision`.
- Every external-result-like payload must include a `raw_payload_ref`.
- Missing raw refs, malformed outputs, credential/trading fields, and unexpected artifact types are quarantine triggers.
- `DATA_MISSING` is acceptable only when explicit and review-visible.
- A sidecar must not emit `human_review_decision`.
- A sidecar must not mark any result as `financial_truth` or generic `source-backed`.
