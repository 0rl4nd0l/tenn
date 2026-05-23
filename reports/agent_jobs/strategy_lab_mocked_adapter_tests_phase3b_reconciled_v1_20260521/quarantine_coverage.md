# Quarantine Coverage

## Covered Quarantine / Invalid Cases

- helper output missing full envelope fields when promoted beyond pre-envelope normalization
- sidecar unavailable
- timeout
- malformed output
- schema validation failure
- policy denial
- forbidden scope requested
- missing benchmark without `DATA_MISSING`
- missing data source
- missing assumptions or limitations
- missing raw payload ref
- broker or exchange credential fields
- paper/live/order fields
- unexpected artifact type
- suspected live or paper execution surface

## DATA_MISSING Propagation

The tests require explicit `DATA_MISSING` for:

- benchmark unavailable
- incomplete data source
- missing equity curve or trade fields
- unproven regime or tuning shape
- unavailable raw payload
- unconfirmed sidecar capability
- helper output that cannot prove a full Strategy Lab artifact field

## Boundary

Quarantine coverage is encoded only as local JSON mock vectors and stdlib tests. It does not implement a runtime validator, artifact store, adapter, client, service, or transport.
