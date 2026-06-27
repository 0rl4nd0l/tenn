# Decisions

- `SUPERSEDE`: PR #439 is preserved as prior reviewed work but replaced by a
  fresh current-base branch because it is dirty/conflicting.
- `ADOPT`: Replayed the PR #439 backend route guard and tests.
- `CONTINUE`: Kept the newer current-canonical context diagnostics,
  TradingView, Intel Pulse, and extraction-review API surface notes while adding
  the memory read-route policy.
- `NO_EXTRA_CLIENT_PATCH`: The P2 review fix for company-dump API-key
  forwarding is already present on canonical, so no redundant client edit was
  needed.
- `UPDATE_DIAGNOSTICS_EXPECTATION`: `/api/context/ticker` keeps unauthenticated
  diagnostic redaction, but `/api/context/company_dump` is memory-inclusive and
  now returns `401` without `X-API-Key` when a local key is configured.
- `PARTIAL_RUNTIME_PROOF`: Local tests prove route/client behavior at unit level,
  but no live backend/browser smoke was run.
