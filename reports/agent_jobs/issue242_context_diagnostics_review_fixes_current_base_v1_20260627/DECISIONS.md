# Decisions

## D1: Replace Stale PR Worktree From Current Base

Decision: create a fresh current-base worktree instead of editing PR #438's
stale local worktree.

Evidence:

- Root checkout was stale.
- PR #438 worktree was `STALE_PATH`.
- The replacement branch starts at canonical `eb4a4291`.

## D2: Preserve Public Ticker Reads With Redaction

Decision: keep `/api/context/ticker` available as a backend-owned context read,
but redact diagnostic/path fields when `settings.local_api_key` is configured
and the caller does not provide a matching key.

Reason: this matches issue #242 acceptance criteria without replacing backend
context authority or requiring all ordinary context reads to authenticate.

## D3: Company Dump Inherits Caller Auth

Decision: `company_dump` passes the request `X-API-Key` into ticker context
assembly.

Reason: unauthenticated configured-key company dump responses should not expose
diagnostic internals, but authenticated Cockpit/tool calls must preserve
diagnostic counts and source-path evidence.

## D4: Do Not Expand Shared Frontend Runtime Key Handling

Decision: keep the frontend changes to the existing `withApiKey()` pattern for
this issue.

Reason: broader localStorage/runtime-key propagation affects several other open
route-guard PRs and should be handled in those issue-specific lanes instead of
expanding #242 beyond its reviewed blockers.
