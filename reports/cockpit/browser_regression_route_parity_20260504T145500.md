# Cockpit Browser Regression Route Parity

Generated: 2026-05-04T05:01:14.154Z
Verification target: http://127.0.0.1:8081

| Page/Route | Control/Area | Expected | Observed | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| / | Server and chat shell | :8081 or configured base URL returns 200 and renders chat input | HTTP 200; title "Financial Cockpit"; chat input visible | PASS | http://127.0.0.1:8081 |
| / | Plain conversational message | Lightweight answer with no analyst shell, no error card, and no raw operator text | Plain mocked answer rendered without Sources/Trust shell labels or raw diagnostic text | PASS | SSE mocked; no live model call |
| / | Analyst shell message | Ticker, answer type, source count, evidence summary, key facts, and gap banner render | BHP partial-evidence shell rendered with source count 2, filings + news evidence, key facts, and market_context gap | PASS | Metadata and source list supplied through mocked SSE |
| / | Source list | Source list can close and reopen; rendered count matches metadata | Inline [2 sources] list closed, Review evidence reopened it, and two-source metadata remained visible | PASS | Drawer-equivalent inline source list exercised |
| / | Action proposal card | Confirmation state and confirm/cancel controls render without auto-execution | Action card rendered; backend action POST count stayed 0 until cancelled | PASS | Mutating backend action route mocked and counted |
| / | Thesis-note proposal | NOTE is not treated as ticker; referenced entity and memory/write confirmation are visible | Entity BHP rendered, Entity NOTE absent, Memory write and confirmation labels visible | PASS | create_thesis action preview mocked |
| / | Unsupported financial claim guard | Unsupported claim guard remains represented in UI when routing metadata requires it | Unsupported claim blocked trust label and Data missing answer type rendered | PASS | No financial truth, extraction, or prompt behavior changed |
| / | Diagnostic/flag card hygiene | Compact diagnostic card visible; raw Codex CLI and repair prompt hidden by default | Diagnostic controls rendered while raw CODEX PROMPT and codex exec strings remained hidden | PASS | Auto-flag payload mocked in SSE done event |
| / | Feedback flag flow | Flag dialog opens and safe mocked flag result renders without raw prompt dump | Flag saved through mocked route; feedback POST count 1; raw prompt/CLI hidden | PASS | No destructive backend action required |
| / | Chat | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /operations | Operations | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /verification | Verification | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /news | News | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /memory | Memory | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /watchlist | Watchlist | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /holdings | Holdings | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /marketplace | Marketplace | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /marketplace/matches | Marketplace matches | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /marketplace/alerts | Marketplace alerts | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /thesis-audit | Thesis audit | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /settings | Settings | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /history | History | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /intel-ops | Intel Pulse | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
| /updater | Updater | Route loads in browser without Next.js 404 or 500 page | HTTP 200 | PASS | Primary route smoke with mocked non-destructive API responses |
