# Strategy Lab Mocked Adapter Tool Policy v1

Status: design-only mock policy.

All operations in this document are mock/design-level entries. Phase 3A does not call any real tool, issue tokens, start services, or write stores.

## Operation Matrix

| Operation | Phase 3A status | Required mock scope | Required input fields | Expected output shape | Artifact emitted | Raw payload ref rule | Quarantine rule | DATA_MISSING behavior | Audit log fields | Rate-limit expectation | Human review |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `list_capabilities` | `allowed_mock_only` | `phase3a_design_only` | `request_id`, `job_id`, `operation`, `mock_scope`, `production_data_access=false`, `execution_allowed=false` | Capability list with each operation classified and forbidden surfaces listed | None | Mock fixture ref optional; no external raw payload | Quarantine if output contains credential, token-admin, trading, store-write, or unknown operation authority | Missing tool schemas become `DATA_MISSING` | request id, policy version, operation, decision, forbidden surfaces, task card | Local mock only; future sidecar max 10/min unless lower | Required before any future use |
| `read_market_snapshot` | `allowed_mock_only` | `phase3a_design_only`, public/synthetic only | `market`, `symbol`, `timeframe`, `lookback`, `requested_fields` | Read-only OHLCV/price context with provider status and limitations | None by default; may be referenced as `external_tool_context` | Required if a future external result is used; mock path in Phase 3A | Quarantine if provider/source missing and no `DATA_MISSING`, if production data appears, or if result has order/credential fields | Provider or source gaps must be explicit | market, symbol, timeframe, provider status, data policy, result count | Local mock only; future sidecar max 10/min | Required for any saved context |
| `submit_backtest` | `allowed_mock_only` | `phase3a_design_only`, bounded historical simulation only | `strategy_ref`, `market`, `symbol`, `timeframe`, `start`, `end`, `initial_capital`, `fees_slippage`, `position_sizing`, `benchmark_policy` | Accepted job envelope with `external_job_id`, status, and polling policy | Not at submission; eventual `backtest_run` on successful result | Required for future raw submit response | Quarantine/deny if strategy creates or mutates live workspace, requests paper/live order path, or includes credential fields | Missing benchmark policy defaults to `DATA_MISSING` hold | strategy ref, date range, requested benchmark, denied scopes, idempotency key | Local mock only; future sidecar submit max 2/min | Required before artifact display |
| `get_backtest_result` / `get_job` | `allowed_mock_only` | `phase3a_design_only` | `external_job_id`, `expected_kind=backtest`, `request_id`, `job_id` | Job status plus raw result metrics, equity curve ref/shape, trades summary, assumptions, limitations | `backtest_run` only after schema/policy gates | Required; missing raw ref is quarantine | Quarantine if malformed, missing raw payload, unexpected artifact type, benchmark/provider/source/limitations absent without `DATA_MISSING`, or trading fields appear | Benchmark/provider/hash/robustness gaps are carried as explicit `DATA_MISSING` | job id, poll count, status, result keys, missing fields, mapping decision | Local mock only; future polling backoff and max 10/min | Required; default `PENDING_REVIEW` |
| `regime_detect` | `allowed_mock_only` | `phase3a_design_only`, public/synthetic only | `market`, `symbol`, `timeframe`, `start`, `end`, `regime_model` | Regime label, confidence, features, segments, strategy families, limitations | `regime_breakdown` after schema/policy gates | Required; missing raw ref is quarantine | Quarantine if malformed, provider/sample/segment/source/limitations absent without `DATA_MISSING`, or strategy family output is framed as execution advice | Provider, segment times, sample size, and candle count gaps become explicit `DATA_MISSING` | symbol, date range, model, confidence, missing fields, mapping decision | Local mock only; future max 5/min | Required; default `PENDING_REVIEW` |
| `parameter_sweep` / `structured_tune` | `default_hold` | Not authorized beyond design fixture | `DATA_MISSING`; safe compute caps and result shape not proven | `DATA_MISSING` placeholder only | None in Phase 3A; possible future `parameter_sweep` | No future raw ref until Phase 3B/3C proves shape | Hold/quarantine any real result until schema, caps, and payload examples exist | Always report `DATA_MISSING` for structured tuning result shape | hold reason, missing evidence, requested params if any | No calls allowed | Required before any future approval |
| `export_artifact` | `blocked` in sidecar; Tenn-owned only | Not applicable | None accepted from sidecar | Policy denial | None from sidecar | No sidecar raw export accepted | Deny/quarantine if sidecar claims to export approved Tenn artifact or write store | `DATA_MISSING` only for future Tenn-owned artifact-store design | denied operation, reason, attempted target | No calls allowed | Human review and later task card required |

## Blocked Surfaces

The policy must explicitly reject:

- Broker credential setup.
- Exchange key setup.
- Paper order placement.
- Live order placement.
- Bot activation.
- Admin token changes.
- Strategy create/update/run against a live workspace.
- Quick-trade orders.
- Kill-switch interactions.
- Direct Tenn DB writes.
- Direct Qdrant writes.
- Direct news store writes.
- Direct memory writes.
- Direct financial-truth writes.
- Parser, extraction, or gold-label writes.
- Source-registry writes.
- Docker, systemd, env, or secrets changes.
- QuantDinger install/runtime directory writes.
- MCP adapter/client implementation.
- Real API client code.
- Dependency installation or package lock changes.

## Scope Rules

Allowed Phase 3A decisions:

- `allow_mock_only`: operation may be represented by a mock JSON envelope and report text only.
- `default_hold`: operation may be named and documented, but no execution or artifact mapping is authorized.
- `deny`: operation is forbidden and must produce a policy-denied result.

Forbidden Phase 3A decisions:

- No real `allow`.
- No token issuance.
- No service startup.
- No network call.
- No production data access.
- No store write.
- No paper/live execution.

## Artifact Flag Invariants

Any future sidecar-derived artifact must preserve:

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

Policy must deny any request or result that attempts to override these fields.
