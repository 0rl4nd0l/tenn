# Chat Browser Regression Harness

## Scope

- Extracted `/full-chat` browser regression route mocks, SSE fixtures, chat send helpers, and route parity writing into `cockpit-ui/tests/chat-browser-harness.ts`.
- Kept `cockpit-ui/tests/chat-browser-regression.spec.ts` behavior-focused and pointed chat assertions at the current `/full-chat` route.
- Added `cockpit-ui/lib/chat-browser-harness.test.ts` for pure harness coverage.
- Hardened route parity to fail on browser `pageerror` events, not only HTTP 404/500 responses.
- Added shaped, non-destructive UI fixture payloads for Home, Strategy Lab, Settings model groups, and Intel Pulse route smoke. These mocks do not represent live financial truth, memory truth, runtime truth, DB state, or Strategy Lab readiness.

## Validation

- PASS `pnpm --dir cockpit-ui exec vitest run lib/chat-browser-harness.test.ts`
- PASS `pnpm --dir cockpit-ui exec eslint lib/chat-browser-harness.test.ts tests/chat-browser-harness.ts tests/chat-browser-regression.spec.ts`
- PASS `pnpm --dir cockpit-ui exec tsc --noEmit --pretty false --incremental false`
- PASS `COCKPIT_E2E_BASE_URL=http://127.0.0.1:3000 COCKPIT_ROUTE_PARITY_REPORT_PATH=/tmp/chat-browser-regression-route-parity-20260604.md pnpm --dir cockpit-ui exec playwright test tests/chat-browser-regression.spec.ts --project=chromium`
- PASS `git diff --check`

## Notes

- Browser plugin was not available in this session; Playwright was used as the frontend validation fallback.
- The temporary Next dev server was stopped after validation.
- The route parity report path was redirected to `/tmp` during validation to avoid writing unallowlisted report artifacts.
