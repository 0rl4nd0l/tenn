# Quarantine Coverage

## Covered Cases

- malformed mock response, via Phase 3B `malformed_output` vector
- missing `raw_payload_ref`
- missing assumptions or limitations, via Phase 3B vector
- missing benchmark without `DATA_MISSING`, via Phase 3B vector
- missing data source, via Phase 3B vector
- unknown artifact type, via Phase 3B `unexpected_artifact_type` vector
- broker/exchange credential fields
- order fields
- paper/live execution scope
- store-write intent
- unrecognized operation
- sidecar unavailable simulated response
- timeout simulated response

## DATA_MISSING Coverage

The Phase 3C tests require explicit `DATA_MISSING` for:

- unavailable benchmark/provider/hash
- incomplete data source
- missing equity curve or trade fields
- unproven `parameter_sweep`
- unproven `risk_report`
- unproven `factor_test`
- unproven `portfolio_experiment`
- sidecar capability cannot be confirmed
- helper output cannot prove full authoritative artifact fields

## Boundary

Quarantine is represented only by local JSON fixtures and stdlib tests. No runtime validator, artifact store, adapter, client, service, transport, or store-write path was implemented.
