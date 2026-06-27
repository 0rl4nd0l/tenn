# Issue 235 Memory Read Route Guard V2

## Summary

Replayed stale PR #439 onto current canonical head
`38e74ca717197e82102d0554aa031ab09233378f` as a replacement branch for issue
#235. The backend memory read routes now require `X-API-Key` when
`settings.local_api_key` is configured:

- `GET /api/context/memory`
- `GET /api/context/memory/index`
- `GET /api/context/thesis`
- `GET /api/context/company_dump`

The P2 review finding from PR #439 was checked against current canonical:
`BackendApiClient.get_company_dump()` already forwards `_api_key_headers()` and
the existing focused client test asserts the `X-API-Key` header.

## Status

`implementation_validated`

This is code/test validation only. No live backend/browser runtime was exercised
and no durable memory store was mutated.
