# Issue 242 Context Diagnostics Guard V2

## Summary

Replayed PR #448 onto current canonical base
`c84ad58911ee7d68143396d9545913fa7eb54b98` because #448 is stale after later
canonical auth merges.

This v2 branch preserves the reviewed #448 behavior:

- `/api/context/ticker` remains a backend-owned context read.
- Configured-key unauthenticated ticker/company context responses redact
  operator diagnostics, source paths/hashes, announcement excerpts/source paths,
  low-confidence rows, extraction failures, and internal errors.
- `/api/context/verification` and `/api/context/verification/runs` require
  `X-API-Key` when `settings.local_api_key` is configured.
- Cockpit and Python/Textual clients forward configured API-key headers for the
  guarded/redacted context diagnostic routes.
- Current-base API-client tests preserve #240 and #241 auth coverage.

## Status

`PARTIAL`: code and focused tests are validated locally, but no live backend or
browser smoke was run and local frontend Vitest is unavailable.

## Supersedes

- PR #448 head `59eed0582831cf5de229772c1b8a273c7e2715cb`
- branch `safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627`
