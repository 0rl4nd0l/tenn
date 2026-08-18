# Issue 241 Extraction Review Route Guard V3

## Summary

Replayed the validated PR #451 issue #241 fix onto current canonical base
`968a613b24783e1929a893ff1f098d8ff63a8ef5` because PR #451 became
`DIRTY` / `CONFLICTING` after later auth merges.

This v3 branch:

- guards extraction-review read routes and snippet image serving with
  `require_api_key`;
- sends `X-API-Key` from Cockpit extraction-review JSON reads;
- fetches guarded snippet PNGs through an API-key-aware blob helper;
- preserves the stable review-session refresh callback that avoids repeated
  snippet refetches;
- sends API-key headers from the Python/Textual `BackendApiClient` review
  reads;
- preserves already-merged Intel Pulse and TradingView API-key coverage while
  resolving current-base test/doc conflicts.

## Status

`PARTIAL`: code and focused tests are validated locally, but no live backend or
browser smoke was run and frontend Vitest is unavailable in this checkout.

## Supersedes

- PR #451 conflicting head `c7e88d0f928ce18b6db335760beb1ec6f559a1a3`
- PR #436 stale/conflicting earlier replacement
- branch `safe/issue241-extraction-review-route-guard-review-fixes-current-base-v2-20260627`
