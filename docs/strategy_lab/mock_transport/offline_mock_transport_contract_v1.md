# Strategy Lab Offline Mock Transport Contract v1

Status: design and test layer only.

This contract defines a future transport boundary using only offline mock fixtures. It does not implement a production adapter, real client, API transport, MCP transport, QuantDinger runtime, Docker startup, token issuance, artifact store, Tenn store write, broker/exchange path, paper execution, or live execution.

## Authority Boundary

- Tenn is the research brain and evidence/provenance authority.
- QuantDinger is a replaceable external read/backtest sidecar/comparator only.
- QuantDinger output can become Strategy Lab context only after Tenn-owned policy, schema, quarantine, and review gates.
- `strategy_lab_artifact_v1` remains the authoritative artifact envelope.
- `strategy_lab_sidecar_artifact_v1` remains pending-review pre-envelope evidence only.
- Sidecar/helper output must map into the full authoritative envelope or stay quarantined/pre-envelope.
- Strategy Lab artifacts default to `review_status=PENDING_REVIEW`.
- Strategy Lab artifacts must never be canonical financial truth.

## Design-Only Classes

### StrategyLabMockTransport

Design role: offline fixture dispatcher used by tests to prove the policy and lifecycle boundary.

Responsibilities:

- Accept `StrategyLabTransportRequest` objects.
- Call `StrategyLabTransportPolicy` before any mock dispatch.
- Dispatch only to local JSON mock fixtures.
- Return `StrategyLabTransportResponse` objects with audit and lifecycle state.
- Never open a network socket, start a service, issue a token, install a dependency, call QuantDinger, call MCP, or write Tenn stores.

### StrategyLabTransportRequest

Required fields:

- `request_id`
- `job_id`
- `operation`
- `mock_scope=phase3c_offline_mock_transport_only`
- `production_data_access=false`
- `execution_allowed=false`
- `paper_live_scope=none`
- operation-specific `input`

Forbidden request fields include credentials, exchange keys, broker accounts, order payloads, quick-trade commands, bot activation, kill-switch commands, store-write intent, token/admin mutation, runtime routes, and service startup flags.

### StrategyLabTransportResponse

Required fields:

- `operation`
- `lifecycle_state`
- `policy_decision`
- `status`
- `raw_payload_ref` or explicit `DATA_MISSING`
- `result`
- `artifact_emission_decision`
- `quarantine_decision`
- `audit_record`

Responses are offline mock records only. They do not prove that a sidecar exists or that a service can be reached.

### StrategyLabTransportPolicy

The policy gate must produce a decision before mock dispatch:

- `allow_mock_only`: allowed local mock operation.
- `allow_local_mock_conversion_only`: local fixture-to-artifact-envelope conversion only; no persistence.
- `default_hold`: documented shape is unproven and must return `DATA_MISSING`.
- `deny`: forbidden scope, unrecognized operation, trading/order/store path, credential, token, runtime, service, parser/gold-label, or source-registry mutation.

### StrategyLabTransportAuditRecord

Audit records must include request id, operation, policy decision, lifecycle state, task card, mock fixture path, reason codes, artifact emission status, quarantine status, and explicit side-effect flags.

### StrategyLabTransportError

Errors are simulated only:

- `POLICY_DENIED`
- `TIMEOUT_SIMULATED`
- `SIDE_CAR_UNAVAILABLE_SIMULATED`
- `MALFORMED_MOCK_RESPONSE`
- `MISSING_REQUIRED_ENVELOPE_FIELD`
- `UNKNOWN_ARTIFACT_TYPE`

### StrategyLabTransportQuarantineDecision

Quarantine decisions must keep `artifact_emitted=false` unless a full `strategy_lab_artifact_v1` envelope has passed the mock policy and invariant checks. Quarantine preserves raw output context as a local mock reference only.

### StrategyLabArtifactEmissionDecision

Artifact emission is local mock conversion only. An emitted artifact must:

- use `schema_version=strategy_lab_artifact_v1`;
- preserve the full authoritative envelope;
- include `raw_payload_ref`;
- include provenance;
- include assumptions and limitations;
- include benchmark details or an explicit `DATA_MISSING` explanation;
- keep `review_status=PENDING_REVIEW`;
- keep `canonical_financial_truth=false`;
- keep `production_data_access=false`;
- keep `may_write_db=false`;
- keep `may_write_qdrant=false`;
- keep `may_write_memory=false`;
- keep `may_write_financial_truth=false`;
- keep `execution_allowed=false`.

## Allowed Mock Operations

| Operation | Decision | Artifact Emission |
| --- | --- | --- |
| `list_capabilities` | `allow_mock_only` | None |
| `read_market_snapshot` | `allow_mock_only` | None |
| `submit_backtest` | `allow_mock_only` | None at submission |
| `get_backtest_result` | `allow_mock_only` | `backtest_run` only after full envelope mapping |
| `get_job` | `allow_mock_only` | Known job result only, otherwise none/quarantine |
| `regime_detect` | `allow_mock_only` | `regime_breakdown` only after full envelope mapping |
| `parameter_sweep` | `default_hold` | None; `DATA_MISSING` |
| `structured_tune` | `default_hold` | None; `DATA_MISSING` |
| `export_artifact` | `allow_local_mock_conversion_only` | Local mock conversion report only, never persistence |

## Blocked Surfaces

The mock transport must hard deny broker credential setup, exchange key setup, paper order placement, live order placement, bot activation, admin token changes, strategy create/update/run against a live workspace, quick-trade orders, kill-switch interactions, direct Tenn DB writes, direct Qdrant writes, direct news writes, direct memory writes, direct financial-truth writes, parser/extraction/gold-label writes, and source-registry writes.

## Non-Goals

This contract deliberately does not define a production `StrategyLabSidecarClient`, MCP client, real transport adapter, runtime validator module, backend route, Cockpit UI/backend path, artifact store, scheduled job, autonomous loop, dependency, broker/exchange config, token flow, or paper/live execution path.
