# Input Inventory

## Phase 3C Primary Inputs

Root:
`/home/l4nd0/tenn-strategy-lab-offline-mock-transport-phase3c-v1-20260521`

Available and inspected:

- `docs/strategy_lab/mock_transport/offline_mock_transport_contract_v1.md`
- `docs/strategy_lab/mock_transport/offline_mock_transport_lifecycle_v1.md`
- 12 JSON fixtures under `docs/strategy_lab/mock_transport_fixtures/`
- `tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py`
- `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/README.md`
- `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/mock_transport_test_results.md`
- `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/policy_coverage_matrix.md`
- `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/quarantine_coverage.md`
- `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/transport_contract.md`
- `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/go_no_go_phase3d.md`
- `reports/agent_jobs/strategy_lab_offline_mock_transport_phase3c_v1_20260521/status.json`

No Phase 3C primary input path required for this review was missing.

## Phase 3C Fixture Summary

| Fixture | Operation | Decision | Status | Lifecycle | Emits Artifact | Quarantined | Raw Payload Ref | Artifact Type |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `invalid_missing_raw_payload_ref_transport_response_v1.json` | `get_backtest_result` | `allow_mock_only` | `quarantined` | `QUARANTINED` | false | true | false |  |
| `invalid_order_field_transport_response_v1.json` | `submit_backtest` | `deny` | `policy_denied` | `POLICY_DENIED` | false | false | false |  |
| `invalid_policy_denied_transport_response_v1.json` | `broker_credential_setup` | `deny` | `policy_denied` | `POLICY_DENIED` | false | false | false |  |
| `invalid_sidecar_unavailable_transport_response_v1.json` | `list_capabilities` | `allow_mock_only` | `sidecar_unavailable_simulated` | `SIDE_CAR_UNAVAILABLE_SIMULATED` | false | true | true |  |
| `invalid_store_write_transport_response_v1.json` | `export_artifact` | `deny` | `policy_denied` | `POLICY_DENIED` | false | false | false |  |
| `invalid_timeout_transport_response_v1.json` | `get_job` | `allow_mock_only` | `timeout_simulated` | `TIMEOUT_SIMULATED` | false | true | true |  |
| `invalid_trading_scope_transport_response_v1.json` | `submit_backtest` | `deny` | `policy_denied` | `POLICY_DENIED` | false | false | false |  |
| `valid_capabilities_transport_response_v1.json` | `list_capabilities` | `allow_mock_only` | `succeeded` | `MOCK_RESULT_READY` | false | false | true |  |
| `valid_get_backtest_result_transport_response_v1.json` | `get_backtest_result` | `allow_mock_only` | `succeeded` | `NORMALIZED_TO_PENDING_ARTIFACT` | true | false | true | `backtest_run` |
| `valid_market_snapshot_transport_response_v1.json` | `read_market_snapshot` | `allow_mock_only` | `succeeded` | `MOCK_RESULT_READY` | false | false | true |  |
| `valid_regime_detect_transport_response_v1.json` | `regime_detect` | `allow_mock_only` | `succeeded` | `NORMALIZED_TO_PENDING_ARTIFACT` | true | false | true | `regime_breakdown` |
| `valid_submit_backtest_transport_response_v1.json` | `submit_backtest` | `allow_mock_only` | `accepted` | `MOCK_RESULT_READY` | false | false | true |  |

## Supporting Inputs

Phase 3B reconciled bundle was available and inspected where needed:

- Root:
  `/home/l4nd0/tenn-strategy-lab-mocked-adapter-tests-phase3b-reconciled-v1-20260521`
- Report recommendation:
  `GO_PHASE3C_OFFLINE_MOCK_TRANSPORT_ADAPTER_ONLY`
- Reported test result:
  12 stdlib unittest tests passed with `python3`.

Phase 2 authoritative schema bundle was available and inspected where needed:

- Root:
  `/home/l4nd0/tenn-strategy-lab-artifact-schema-phase2-v1-20260520`
- Schema id:
  `https://tenn.local/schemas/strategy_lab_artifact_v1.schema.json`
- Required envelope includes `raw_payload_ref`, provenance, storage policy,
  validation, security policy, truth flags, production-data flag, and
  execution flag.
- Valid copied fixtures inspected:
  `valid_backtest_run_v1.json`, `valid_regime_breakdown_v1.json`,
  `valid_strategy_idea_v1.json`.

## Merge And Readiness Warning

Worktree status checks found consolidation work is still needed:

- Phase 2 worktree has untracked task-card, schema, and fixture files.
- Phase 3A worktree has staged additions under `docs/agent_tasks/`,
  `docs/strategy_lab/`, and `reports/agent_jobs/`.
- Phase 3B worktree has untracked task-card, `docs/strategy_lab/`, and test
  additions; reports are ignored.
- Phase 3C worktree has untracked task-card, `docs/strategy_lab/`, and test
  additions; reports are ignored.

This does not block a Phase 3E implementation-plan-only recommendation, but it
does block treating the Phase 2/3A/3B/3C files as consolidated implementation
inputs without an explicit save/merge decision.

## DATA_MISSING

- No primary Phase 3C input for this review was missing.
- Real sidecar capability and real transport evidence remain `DATA_MISSING` by
  design.
- Consolidated saved state of the Phase 2/3A/3B/3C worktrees remains
  `DATA_MISSING` until those worktrees are explicitly preserved or merged.
