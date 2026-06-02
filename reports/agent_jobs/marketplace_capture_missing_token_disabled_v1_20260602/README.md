# Marketplace Capture Missing Token Disabled State

## Summary

Issue #52 was fixed in an isolated Reporting-lane worktree. The Marketplace
capture helper no longer renders a dead `href="#"` capture action when opened
without a capture token.

## User-Visible Behavior

- `/marketplace-capture` without `token` shows a missing-token warning.
- The capture control is disabled in the missing-token state.
- The missing-token state exposes a `Return to Cockpit` link.
- `/marketplace-capture?token=token-123&url=<listing>` still renders a
  `javascript:` bookmarklet for `Capture Marketplace Listing`.

## Validation Evidence

- Focused ESLint passed for `app/marketplace-capture/page.tsx` and
  `tests/marketplace-capture-helper.spec.ts`.
- Focused Chromium Playwright regression passed: `2 passed`.
- TypeScript `tsc --noEmit --pretty false` passed.
- Rendered evidence with Cockpit BFF calls mocked:
  - missing-token URL title was `Financial Cockpit`
  - missing-token warning visible
  - capture button disabled
  - dead `a[href="#"]` capture links: `0`
  - return link href: `/full-chat`
  - valid-token capture href prefix: `javascript:`
  - valid-token open-listing href preserved
  - console warnings/errors: `0`

Screenshots were captured outside the repo:

- `/tmp/tenn-marketplace-capture-missing-token-disabled-v1-20260602/missing-token-mocked.png`
- `/tmp/tenn-marketplace-capture-missing-token-disabled-v1-20260602/valid-token-mocked.png`

## Boundary Notes

- No backend route was edited.
- No token issuance or storage code was edited.
- No DB, Qdrant, news, memory, financial truth, parser routing, extraction
  prompt, gold label, model config, GPU config, or service config was changed.
- The local Next dev server on `127.0.0.1:3102` was stopped after validation.

## Closeout Status

Leave issue #52 open until the covering PR merges and the reviewer accepts the
close gate.
