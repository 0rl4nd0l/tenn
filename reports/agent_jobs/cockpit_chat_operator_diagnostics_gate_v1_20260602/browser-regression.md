# Cockpit Chat Operator Diagnostics Browser Regression

Generated: 2026-06-02T09:46:51Z

Verification target: `http://127.0.0.1:3026`

Runtime:

- Worktree: `/home/l4nd0/tenn-cockpit-chat-operator-diagnostics-gate-v1-20260602`
- Branch: `safe/cockpit-chat-operator-diagnostics-gate-v1-20260602`
- Frontend command: `NEXT_PUBLIC_COCKPIT_OPERATOR_DIAGNOSTICS=0 corepack pnpm --dir cockpit-ui exec next dev --hostname 127.0.0.1 --port 3026`
- Browser command: `COCKPIT_E2E_BASE_URL=http://127.0.0.1:3026 COCKPIT_ROUTE_PARITY_REPORT_PATH=/tmp/cockpit_chat_operator_diagnostics_browser_regression_20260602.md corepack pnpm --dir cockpit-ui exec playwright test tests/chat-browser-regression.spec.ts --project=chromium --retries=0`

Result: PASS, 4 browser tests passed.

## Relevant #108 Evidence

| Route | Area | Expected | Observed | Status |
| --- | --- | --- | --- | --- |
| `/full-chat` | Diagnostic/flag card hygiene | Normal users see `DATA_MISSING` recovery text without operator report paths, diagnostic links, repair prompts, or `Deploy Codex` controls. | Mocked `auto_flag` rendered normal recovery text; report id, diagnostic link, repair prompt, investigation packet, `Deploy Codex`, raw prompt, and CLI text were absent. | PASS |
| `/full-chat` | Feedback flag flow | Manual flag flow saves feedback without exposing operator report ids, paths, diagnostic links, repair prompts, or `Deploy Codex` controls. | Flag saved through mocked route; feedback POST count was 1; normal recovery text remained visible and operator controls were hidden. | PASS |

## Full Chromium Route Parity Summary

All rows below passed with mocked non-destructive API responses:

- `/full-chat` chat shell: HTTP 200 and chat input visible.
- `/full-chat` plain answer: no analyst shell, error card, or raw operator text.
- `/full-chat` analyst shell: ticker, source count, evidence summary, key facts, and gap banner render.
- `/full-chat` source list: source list closes and reopens.
- `/full-chat` action proposal: confirmation state and cancel controls render without auto-execution.
- `/full-chat` thesis-note proposal: BHP entity and memory-write confirmation render; NOTE is not treated as ticker.
- `/full-chat` unsupported financial claim guard: `Unsupported / not verified` and `Data missing` render.
- `/full-chat` diagnostic auto-flag and manual flag flows: normal recovery text visible, operator controls hidden.
- Primary route smoke: `/`, `/operations`, `/verification`, `/news`, `/memory`, `/watchlist`, `/holdings`, `/marketplace`, `/marketplace/matches`, `/marketplace/alerts`, `/thesis-audit`, `/settings`, `/history`, `/intel-ops`, and `/updater` loaded without browser 404 or 500 pages.

## Boundary

The browser proof uses deterministic Playwright route mocks for the SSE `auto_flag` and feedback capture payloads. It proves `/full-chat` rendering behavior for normal users without mutating backend diagnostics, financial truth, retrieval, memory, runtime, or service config.
