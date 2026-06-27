# Decisions

## Redaction Instead Of Full Ticker Route Guard

`/api/context/ticker` remains available as a backend-owned context read. When
`settings.local_api_key` is configured and a caller omits or sends the wrong
key, the response keeps ordinary context fields but redacts operator diagnostic
surfaces.

Reason: issue #242 requires preserving backend authority while separating normal
context reads from diagnostic/evaluation evidence.

## Hard Guard Verification Reads

`/api/context/verification` and `/api/context/verification/runs` use
`require_api_key`.

Reason: these routes are explicitly diagnostic/evaluation surfaces and expose
cross-ticker queues or run history.

## Preserve Internal Helper Diagnostics

Direct Python helper calls keep diagnostics when local API-key config exists.

Reason: server-side callers such as audit providers are not HTTP clients and
should not silently lose diagnostic evidence because FastAPI header injection is
absent.
