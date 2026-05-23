# Strategy Lab Adapter Quarantine Policy v1

Status: design-only quarantine policy.

Invalid output must be quarantined, not normalized into a valid Strategy Lab artifact.

## Error Handling

| Condition | Policy result | Artifact result | Required handling |
| --- | --- | --- | --- |
| Sidecar unavailable | `sidecar_unavailable` | No artifact | Return unavailable result, log endpoint/service status as mock/future evidence, do not retry indefinitely |
| Timeout | `timeout` | No artifact | Return failed result, include timeout budget, no partial artifact unless raw payload is complete and valid |
| Malformed output | `schema_invalid` | No artifact | Quarantine raw payload, preserve parse error, require human review |
| Schema validation failure | `schema_invalid` | No artifact | Quarantine raw payload, mark `FAILED_SCHEMA_VALIDATION` |
| Policy denial | `policy_denied` | No artifact | Do not call sidecar, log denied operation and reason |
| Forbidden scope requested | `policy_denied` | No artifact | Reject before sidecar call; includes W/C/T/N, broker, exchange, quick-trade, bot, token-admin, Tenn-store, parser/gold-label, source-registry |
| Result lacks benchmark | `needs_more_evidence` or `quarantined` | Only allowed if benchmark is explicitly represented as `DATA_MISSING` | Add review-visible `DATA_MISSING`; quarantine if omitted or hidden |
| Result lacks data source | `needs_more_evidence` or `quarantined` | Only allowed if provider/source is explicit `DATA_MISSING` or `INFERRED` | Add review-visible provider status; quarantine if omitted |
| Result lacks assumptions/limitations | `schema_invalid` | No artifact | Quarantine; assumptions and non-empty limitations are required |
| Raw payload missing | `schema_invalid` | No artifact | Quarantine; no raw ref means no normalized artifact |
| Credential/trading/order fields appear | `policy_denied` plus `quarantined` | No artifact | Quarantine and require security review |
| Unexpected artifact_type | `schema_invalid` | No artifact | Quarantine; no best-effort remap |
| Suspected live/paper execution surface | `policy_denied` plus `quarantined` | No artifact | Stop; no artifact, no retry, no execution |

## Quarantine Reasons

Standard reason codes:

- `SIDECAR_UNAVAILABLE`
- `TIMEOUT`
- `MALFORMED_OUTPUT`
- `SCHEMA_VALIDATION_FAILED`
- `POLICY_DENIED`
- `FORBIDDEN_SCOPE_REQUESTED`
- `MISSING_BENCHMARK`
- `MISSING_DATA_SOURCE`
- `MISSING_ASSUMPTIONS`
- `MISSING_LIMITATIONS`
- `MISSING_RAW_PAYLOAD_REF`
- `CREDENTIAL_FIELD_PRESENT`
- `TRADING_FIELD_PRESENT`
- `ORDER_FIELD_PRESENT`
- `UNEXPECTED_ARTIFACT_TYPE`
- `SUSPECTED_LIVE_OR_PAPER_EXECUTION`
- `FINANCIAL_TRUTH_LABEL_PRESENT`
- `STORE_WRITE_FIELD_PRESENT`

## Raw Output Rules

- Raw output is quarantined before normalization when it fails policy or schema checks.
- Quarantined output can be referenced by report-local path only.
- Quarantined output must not be displayed as a valid Strategy Lab artifact.
- Quarantined output must not update Tenn DB, Qdrant, news, memory, financial truth, source registry, parser/extraction, gold labels, Cockpit, or runtime state.
- Redaction is mandatory if token, credential, account, broker, exchange, order, or secret-looking fields appear.

## DATA_MISSING Rules

`DATA_MISSING` is allowed only when explicit and review-visible. It is not a waiver for hidden missing evidence.

Allowed `DATA_MISSING` examples from Phase 2:

- Benchmark object and benchmark returns.
- Explicit upstream provider field.
- Strategy code hash.
- Raw payload SHA-256 in schema-only/design-only tasks.
- Regime segment start/end times.
- Sample size by regime.
- Exact candle count used by detector.
- Structured tuning result shape.

If a required field is missing and no `DATA_MISSING` entry is present, the result is invalid and must be quarantined.
