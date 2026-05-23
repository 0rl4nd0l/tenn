# Tool Policy Matrix

## Summary

Phase 3A defines only mock/design-level tool policy. No real tools were called.

| Operation | Decision | Artifact | Reason |
| --- | --- | --- | --- |
| `list_capabilities` | `allow_mock_only` | None | Safe capability listing as a mock fixture |
| `read_market_snapshot` | `allow_mock_only` | None by default | Read-only market context; provider gaps explicit |
| `submit_backtest` | `allow_mock_only` | None at submission | Bounded historical simulation submission only |
| `get_backtest_result` / `get_job` | `allow_mock_only` | `backtest_run` | Phase 1 result shape mapped to Phase 2 schema |
| `regime_detect` | `allow_mock_only` | `regime_breakdown` | Phase 1 result shape mapped to Phase 2 schema |
| `parameter_sweep` / `structured_tune` | `default_hold` | None in Phase 3A | Result shape and compute caps are `DATA_MISSING` |
| `export_artifact` | `blocked` for sidecar | None | Export/persistence must be Tenn-owned only |

## Blocked Surfaces

- Broker credential setup.
- Exchange key setup.
- Paper order placement.
- Live order placement.
- Bot activation.
- Admin token changes.
- Strategy create/update/run against live workspace.
- Quick-trade orders.
- Kill-switch interactions.
- Direct Tenn DB/Qdrant/news/memory/financial-truth writes.
- Parser/extraction/gold-label writes.
- Source-registry writes.

## Policy Requirements

- `production_data_access=false`.
- `execution_allowed=false`.
- `paper_live_scope=none`.
- `canonical_financial_truth=false`.
- No W/C/T/N scope in Strategy Lab sidecar artifacts.
- No token issuance in Phase 3A.
- No service startup in Phase 3A.
- No network calls in Phase 3A.
- Human review is required for any saved artifact.

## Rate Limits

Phase 3A is mock-only, so no real rate limit was exercised.

Future design expectations:

- Capability and read calls: max 10/min unless stricter.
- Submit backtest: max 2/min.
- Polling: bounded backoff with max 10/min.
- Regime detect: max 5/min.
- Default-hold and blocked operations: no calls.
