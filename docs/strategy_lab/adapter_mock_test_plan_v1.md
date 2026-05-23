# Strategy Lab Mocked Adapter Test Plan v1

Status: design-only plan for future Phase 3B mocked tests. No runtime tests are implemented by Phase 3A.

## Phase 3B Test Scope

Future Phase 3B may implement mock-only tests if separately authorized by task card. Tests must not start QuantDinger, start MCP, issue tokens, access production data, write Tenn stores, install dependencies, or execute paper/live trading.

## Test Groups

### Policy Allowlist Tests

- `list_capabilities` returns `allow_mock_only`.
- `read_market_snapshot` returns `allow_mock_only` only with `production_data_access=false` and `execution_allowed=false`.
- `submit_backtest` returns `allow_mock_only` only for bounded historical simulation fields.
- `get_backtest_result` returns `allow_mock_only` only for expected `backtest` jobs.
- `regime_detect` returns `allow_mock_only` only for read/context inputs.
- `parameter_sweep` / `structured_tune` returns `default_hold`.
- `export_artifact` from sidecar returns `deny`.

### Blocked-Surface Tests

- Broker credential setup is denied.
- Exchange key setup is denied.
- Paper order placement is denied.
- Live order placement is denied.
- Bot activation is denied.
- Admin token changes are denied.
- Strategy create/update/run against live workspace is denied.
- Quick-trade orders are denied.
- Kill-switch interactions are denied.
- Tenn DB/Qdrant/news/memory/financial-truth writes are denied.
- Parser/extraction/gold-label writes are denied.
- Source-registry writes are denied.

### Schema Mapping Tests

- Mock successful job maps to `backtest_run` with mandatory false flags.
- Mock regime result maps to `regime_breakdown` with mandatory false flags.
- Mock structured tune remains `DATA_MISSING` / default hold.
- Mock risk report is provisional/context only and cannot claim financial truth.
- Mock strategy idea requires Tenn/human source of idea.
- Sidecar cannot emit `human_review_decision`.

### Raw Payload Quarantine Tests

- Missing raw payload ref quarantines result.
- Malformed JSON quarantines result.
- Credential-looking fields quarantine result.
- Paper/live/order fields quarantine result.
- Unexpected artifact type quarantines result.
- Financial truth label quarantines result.

### DATA_MISSING Propagation Tests

- Missing benchmark becomes explicit `DATA_MISSING` or quarantine.
- Missing provider becomes explicit `DATA_MISSING` / `INFERRED` or quarantine.
- Missing sample size becomes explicit `DATA_MISSING`.
- Missing raw hash remains `DATA_MISSING` in design-only tests.
- Missing assumptions or limitations quarantines result.

### Sidecar Unavailable Tests

- Unavailable sidecar returns `sidecar_unavailable`.
- Timeout returns failure with no artifact.
- Retry policy is bounded and does not start services.

### Artifact Flag Invariant Tests

Every normalized sidecar artifact must assert:

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

Tests must fail if any flag is true or missing.

### No-Store-Write Tests

Mocks must prove no adapter path calls Tenn DB, Qdrant, news, memory, financial-truth, parser/extraction, gold-label, source-registry, Cockpit, Docker, systemd, env, secrets, or runtime code.

### No-Token/No-Service/No-Network Tests

Mocks must prove:

- No QuantDinger startup.
- No MCP startup.
- No Docker startup.
- No token issuance.
- No network call.
- No dependency installation.
- No package lock change.

### Forbidden Broker/Trading Regression Tests

Regression fixtures should include fields such as:

- `broker_api_key`
- `exchange_secret`
- `paper_order_id`
- `live_order_id`
- `quick_trade_order`
- `kill_switch`
- `bot_activation`
- `execution_allowed=true`
- `canonical_financial_truth=true`

Each must be denied or quarantined with no artifact emitted.

## Phase 3B Entry Gate

Phase 3B is appropriate only if Phase 3A provides:

- Coherent mocked adapter contract.
- Strict mock tool allowlist.
- Mock request/response envelopes.
- Quarantine/error policy.
- Mock-only test plan.
- Explicit Phase 3B go/no-go.
