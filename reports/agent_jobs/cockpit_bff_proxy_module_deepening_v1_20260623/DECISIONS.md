# Decisions

## Decision 1: Start With Watchlist Routes

The watchlist BFF route cluster was selected as the first Cockpit proxy slice
because it already had focused Vitest coverage and exercises GET, POST, and
DELETE forwarding without touching product UI components or backend code.

## Decision 2: Keep The Helper Web-Platform Native

`cockpit-ui/lib/proxy.ts` is also imported by non-route library code, so the new
helper returns a standard `Response` instead of importing `NextResponse` from
`next/server`. This avoids making the shared proxy module server-framework
specific.

## Decision 3: Rebuild In A Clean Worktree

Unrelated edits to Tenn guard/skill-surface files appeared in the source
worktree after implementation started. The Cockpit patch was moved into a clean
sibling worktree based on current canonical instead of touching or staging the
unrelated files.

## Ledger Update

Live ledger mutation was skipped because the task card did not explicitly
authorize live ledger append/release mutation. The report bundle records guard,
ledger, validation, and closeout state instead.
