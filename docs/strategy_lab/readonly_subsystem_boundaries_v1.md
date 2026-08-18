# Strategy Lab Read-Only Subsystem Boundaries v1

Status: enforced boundary for Strategy Lab reporting and review surfaces.

## Confirmed Safe Surface

- Repository artifacts under `docs/strategy_lab/**`.
- Report artifacts under `reports/agent_jobs/**`.
- Cockpit UI read-only status/review cards.
- Focused tests for Strategy Lab contracts and regressions.
- JSON/markdown review packets.

## Forbidden Surface

- Broker credentials.
- Live orders.
- Paper orders.
- Execution surfaces.
- `current_sidecar_available=true`.
- `execution_allowed=true`.
- `canonical_financial_truth=true`.
- Backend runtime orchestration.
- Persistent sidecar runtime.
- MCP or live transport implementation.
- Token manager or scheduler.
- Queue worker.
- Tenn DB, Qdrant, news, memory, source-registry, parser, runtime, model, or GPU
  configuration writes.
- Production data access.
- Misleading current-availability labels.

## Retry, Timeout, And Unavailable Semantics

These are documentation, status, fixture, and packet semantics only:

- retry behavior remains `DATA_MISSING` unless a later approved adapter task
  implements and validates it;
- timeout behavior remains fixture/status semantics only;
- runtime unavailable behavior is represented as degraded-state evidence, not as
  a live endpoint result;
- cleanup/revoke invariants are required for every runtime proof;
- failed or incomplete outputs must remain quarantined or `DATA_MISSING`.

## Future Adapter Seam Definition

A future adapter seam can only be considered after a separate task card proves:

- no execution/order/broker/token-admin surface;
- no Tenn store write;
- explicit timeout and retry budget;
- explicit degraded/unavailable state;
- local cleanup and revoke proofs;
- human review and promotion gates;
- source/provenance labels that cannot imply canonical financial truth.

This document does not approve that future work.
