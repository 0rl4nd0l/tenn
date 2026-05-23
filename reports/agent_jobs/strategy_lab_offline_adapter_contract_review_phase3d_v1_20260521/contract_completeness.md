# Contract Completeness Review

Result: `SUFFICIENT_FOR_PHASE3E_PLAN_ONLY`

The Phase 3C offline mock transport contract is complete enough for a future
implementation-plan-only phase. It is not complete enough to authorize runtime,
client, store, token, transport, or trading implementation.

## Requirement Matrix

| Requirement | Evidence | Result |
| --- | --- | --- |
| Request envelope | Contract defines `StrategyLabTransportRequest` with `request_id`, `job_id`, `operation`, `mock_scope`, `production_data_access=false`, `execution_allowed=false`, `paper_live_scope=none`, and operation-specific input. | Covered |
| Response envelope | Contract defines `StrategyLabTransportResponse` with operation, lifecycle state, policy decision, status, `raw_payload_ref` or explicit `DATA_MISSING`, result, artifact emission decision, quarantine decision, and audit record. | Covered |
| Policy decision shape | Contract defines `allow_mock_only`, `allow_local_mock_conversion_only`, `default_hold`, and `deny`. Tests assert allowed, default-held, and denied behavior. | Covered |
| Audit record shape | Contract requires request id, operation, policy decision, lifecycle state, task card, fixture path, reason codes, emission status, quarantine status, and side-effect flags. Fixtures include `audit_record`. | Covered |
| Lifecycle states | Lifecycle doc defines `CREATED`, `POLICY_CHECKED`, `DISPATCHED_TO_MOCK`, `MOCK_RESULT_READY`, `NORMALIZED_TO_PENDING_ARTIFACT`, `QUARANTINED`, `DATA_MISSING`, `POLICY_DENIED`, `TIMEOUT_SIMULATED`, and `SIDE_CAR_UNAVAILABLE_SIMULATED`. | Covered |
| Allowed operation list | Contract allows `list_capabilities`, `read_market_snapshot`, `submit_backtest`, `get_backtest_result`, `get_job`, `regime_detect`, and local mock conversion through `export_artifact`. | Covered |
| Blocked operation list | Contract blocks broker credentials, exchange keys, paper/live orders, bot activation, admin token changes, live workspace runs, quick trades, kill-switch interactions, Tenn store writes, parser/gold-label writes, and source-registry writes. | Covered |
| Artifact emission decision | Contract allows only local mock conversion to full `strategy_lab_artifact_v1` envelopes, with hard false truth/store/execution flags and `review_status=PENDING_REVIEW`. | Covered |
| Raw payload reference rule | Contract and tests require `raw_payload_ref` for emitted artifacts; missing raw payload ref is quarantined. | Covered |
| Quarantine decision | Contract defines quarantine as local evidence retention with `artifact_emitted=false`; report covers malformed, missing evidence, credential/order, store-write, sidecar unavailable, and timeout cases. | Covered |
| `DATA_MISSING` propagation | Lifecycle and quarantine coverage require explicit `DATA_MISSING` for benchmark/provider/hash gaps, incomplete data, missing curve/trade fields, unproven artifact types, sidecar capability, and helper output gaps. | Covered |
| Sidecar unavailable / timeout behavior | Lifecycle includes `SIDE_CAR_UNAVAILABLE_SIMULATED` and `TIMEOUT_SIMULATED`; fixtures cover both with no artifact emission. | Covered |

## Specificity Assessment

The contract gives enough specificity to plan a future Tenn-owned adapter
boundary:

- It names the objects and decisions the boundary must preserve.
- It fixes policy-before-dispatch as a required invariant.
- It separates allowed offline mock reads/backtests from blocked runtime,
  credential, store, and execution surfaces.
- It proves the artifact boundary for `backtest_run` and `regime_breakdown`.
- It holds unproven operations as `DATA_MISSING`.

The contract intentionally does not define production module ownership,
runtime dependency injection, network retry semantics, token handling, MCP/API
transport, artifact persistence, or Cockpit/backend routes. Those omissions are
required by the Phase 3D boundary and should be handled only as plan topics in
Phase 3E.

## Contract Change Need

No Phase 3C docs or tests need to be edited inside Phase 3D. The gaps found are
planning risks, not blockers that require Phase 3C contract changes before a
Phase 3E implementation-plan-only task.
