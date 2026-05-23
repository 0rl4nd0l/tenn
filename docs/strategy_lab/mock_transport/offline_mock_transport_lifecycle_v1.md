# Strategy Lab Offline Mock Transport Lifecycle v1

Status: offline mock lifecycle only.

The lifecycle below is test-only. It models the states a future Tenn-owned transport boundary must pass through without starting services, opening network transport, importing runtime code, writing stores, or executing trades.

## States

| State | Meaning |
| --- | --- |
| `CREATED` | A local `StrategyLabTransportRequest` object exists. |
| `POLICY_CHECKED` | `StrategyLabTransportPolicy` evaluated the request. |
| `DISPATCHED_TO_MOCK` | The request was routed to a local JSON fixture only. |
| `MOCK_RESULT_READY` | The local mock response was read and shaped. |
| `NORMALIZED_TO_PENDING_ARTIFACT` | A local mock result mapped to a full `strategy_lab_artifact_v1` envelope with `PENDING_REVIEW`. |
| `QUARANTINED` | The mock result was retained as unsafe/incomplete local evidence and emitted no artifact. |
| `DATA_MISSING` | The operation or field remains unproven and is held without artifact emission. |
| `POLICY_DENIED` | Policy denied the request before mock dispatch. |
| `TIMEOUT_SIMULATED` | A local fixture simulates timeout; no real timeout or service call occurred. |
| `SIDE_CAR_UNAVAILABLE_SIMULATED` | A local fixture simulates sidecar unavailability; no sidecar was started or contacted. |

## Required Transitions

- Every request starts at `CREATED`.
- Every request must pass through `POLICY_CHECKED` before `DISPATCHED_TO_MOCK`.
- `POLICY_DENIED` requests stop before mock dispatch and cannot emit artifacts.
- `default_hold` requests stop as `DATA_MISSING` and cannot emit artifacts.
- `DISPATCHED_TO_MOCK` can lead to `MOCK_RESULT_READY`, `QUARANTINED`, `TIMEOUT_SIMULATED`, or `SIDE_CAR_UNAVAILABLE_SIMULATED`.
- Only `MOCK_RESULT_READY` for an evidence-backed artifact type can lead to `NORMALIZED_TO_PENDING_ARTIFACT`.
- `NORMALIZED_TO_PENDING_ARTIFACT` is not an approval, store write, runtime route, or canonical truth promotion.

## Fixture Set

| Fixture | Purpose |
| --- | --- |
| `valid_capabilities_transport_response_v1.json` | Capability discovery. |
| `valid_market_snapshot_transport_response_v1.json` | Read-only market snapshot context. |
| `valid_submit_backtest_transport_response_v1.json` | Offline mock job submission. |
| `valid_get_backtest_result_transport_response_v1.json` | Offline mock backtest result conversion. |
| `valid_regime_detect_transport_response_v1.json` | Offline mock regime detection conversion. |
| `invalid_policy_denied_transport_response_v1.json` | Policy denial before dispatch. |
| `invalid_trading_scope_transport_response_v1.json` | Paper/live scope denial. |
| `invalid_missing_raw_payload_ref_transport_response_v1.json` | Quarantine for missing raw payload ref. |
| `invalid_sidecar_unavailable_transport_response_v1.json` | Simulated sidecar unavailable. |
| `invalid_timeout_transport_response_v1.json` | Simulated timeout. |
| `invalid_order_field_transport_response_v1.json` | Denial/quarantine for order fields. |
| `invalid_store_write_transport_response_v1.json` | Denial/quarantine for store-write intent. |

## DATA_MISSING Rules

`DATA_MISSING` must be explicit for unavailable benchmark/provider/hash, incomplete data source, missing equity curve or trade fields, unproven `parameter_sweep`, unproven `risk_report`, unproven `factor_test`, unproven `portfolio_experiment`, unconfirmed sidecar capability, and helper output that cannot prove full authoritative artifact fields.

## Side-Effect Rules

No lifecycle state authorizes production data access, service startup, network transport, dependency installation, token issuance, store writes, paper execution, live execution, order/bot/kill-switch interaction, source-registry writes, parser/gold-label writes, or holdings/watchlist/thesis mutation.
