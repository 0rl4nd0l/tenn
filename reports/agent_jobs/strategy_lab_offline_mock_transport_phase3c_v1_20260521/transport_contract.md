# Transport Contract

## Files

- `docs/strategy_lab/mock_transport/offline_mock_transport_contract_v1.md`
- `docs/strategy_lab/mock_transport/offline_mock_transport_lifecycle_v1.md`
- `docs/strategy_lab/mock_transport_fixtures/*.json`

## Design Boundary

The Phase 3C transport layer is an offline mock boundary only. It defines test-local shapes for:

- `StrategyLabMockTransport`
- `StrategyLabTransportRequest`
- `StrategyLabTransportResponse`
- `StrategyLabTransportPolicy`
- `StrategyLabTransportAuditRecord`
- `StrategyLabTransportError`
- `StrategyLabTransportQuarantineDecision`
- `StrategyLabArtifactEmissionDecision`

No production adapter/client, real transport, MCP client, QuantDinger service, Docker startup, token issuance, dependency install, runtime/backend/Cockpit integration, artifact store, Tenn store write, or trading execution is implemented.

## Lifecycle

Covered lifecycle states:

- `CREATED`
- `POLICY_CHECKED`
- `DISPATCHED_TO_MOCK`
- `MOCK_RESULT_READY`
- `NORMALIZED_TO_PENDING_ARTIFACT`
- `QUARANTINED`
- `DATA_MISSING`
- `POLICY_DENIED`
- `TIMEOUT_SIMULATED`
- `SIDE_CAR_UNAVAILABLE_SIMULATED`

## Allowed Mock Operations

- `list_capabilities`
- `read_market_snapshot`
- `submit_backtest`
- `get_backtest_result`
- `get_job`
- `regime_detect`
- `parameter_sweep` and `structured_tune` only as default-hold / `DATA_MISSING`
- `export_artifact` only as Tenn-owned local mock conversion, never persistence

## Artifact Emission

Only the backtest and regime fixtures emit local pending artifacts, and only by reference to copied full `strategy_lab_artifact_v1` fixtures:

- `docs/strategy_lab/artifact_fixtures/valid_backtest_run_v1.json`
- `docs/strategy_lab/artifact_fixtures/valid_regime_breakdown_v1.json`

Both keep `review_status=PENDING_REVIEW`, `canonical_financial_truth=false`, `production_data_access=false`, all Tenn store write flags false, and `execution_allowed=false`.
