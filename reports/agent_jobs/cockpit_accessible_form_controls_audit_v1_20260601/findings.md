# Findings

## Method

Playwright Chromium rendered the current Cockpit UI on local Next dev server
`http://127.0.0.1:3013`. API requests were fulfilled with empty
`DATA_MISSING`-shaped responses so the audit did not read production data and
could still inspect visible empty/error-state controls.

The DOM inventory marked failures when:

- visible `input`, `textarea`, or native `select` controls had no `label`,
  `aria-label`, `aria-labelledby`, or title;
- visible `role="combobox"`, `role="switch"`, or `role="checkbox"` controls had
  no programmatic name;
- visible icon-only buttons had no programmatic or visible name.

## Route Summary

| Route | Controls | Failures |
| --- | ---: | ---: |
| `/full-chat` | 11 | 1 |
| `/holdings` | 32 | 14 |
| `/news` | 11 | 3 |
| `/verification` | 29 | 9 |
| `/marketplace` | 28 | 9 |
| `/marketplace/alerts` | 9 | 1 |
| `/marketplace/matches` | 12 | 3 |
| `/memory` | 30 | 3 |
| `/thesis-audit` | 13 | 3 |
| `/updater` | 11 | 2 |
| `/intel-ops` | 2 | 0 |
| `/history` | 9 | 0 |
| `/operations` | 16 | 4 |
| `/settings` | 2 | 0 |
| `/watchlist` | 8 | 0 |

Total: 223 visible controls, 52 failures.

## Source Anchors

- `/full-chat`: command input uses only placeholder text at
  `cockpit-ui/components/cockpit/chat/terminal-input.tsx:164`.
- `/holdings`: portfolio filter `SelectTrigger` has no programmatic name at
  `cockpit-ui/components/cockpit/holdings/holdings-screen.tsx:556`; create
  holding inputs are placeholder-only at lines 760, 767, 774, 781, 790, 797,
  804, 811, 818, and 827; filters are placeholder/select-only at lines 845,
  850, and 861.
- `/news`: search and ticker inputs use placeholders at
  `cockpit-ui/components/cockpit/news/news-screen.tsx:293` and line 309; the
  lookback `SelectTrigger` has no programmatic name at line 319.
- `/verification`: header ticker input, method select, and strict switch are
  unlabeled in the rendered DOM at
  `cockpit-ui/components/cockpit/verification/verification-header.tsx:73`,
  line 83, and line 100. Review controls include unlabeled docs limit, extra
  document IDs, recent runs, refresh icon button, saved review sessions, and
  refresh icon button around
  `cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx:176`,
  line 180, line 222, line 249, line 266, and line 283.
- `/marketplace`: assistant prompt textarea is placeholder-only at
  `cockpit-ui/components/cockpit/marketplace/marketplace-assistant.tsx:398`.
  The mission creation form uses visual `label` text without `htmlFor`/wrapping
  associations around
  `cockpit-ui/components/cockpit/marketplace/mission-screen.tsx:1600`,
  lines 1608, 1637, 1649, 1659, 1667, 1677, and 1685.
- `/marketplace/alerts`: status filter select has no programmatic name at
  `cockpit-ui/components/cockpit/marketplace/alerts-screen.tsx:105`.
- `/marketplace/matches`: status, band, and sort select triggers have no
  programmatic names at
  `cockpit-ui/components/cockpit/marketplace/matches-screen.tsx:525`,
  line 541, and line 555.
- `/memory`: ticker and search filters are placeholder-only at
  `cockpit-ui/components/cockpit/memory/memory-screen.tsx:1279` and line 1293;
  memory statement textarea is placeholder-only at line 1388.
- `/thesis-audit`: ticker, focus, and report text controls are placeholder-only
  at `cockpit-ui/components/cockpit/thesis-audit/thesis-audit-screen.tsx:664`,
  line 671, and line 745.
- `/updater`: ticker input and year-range select lack programmatic names at
  `cockpit-ui/components/cockpit/updater/updater-screen.tsx:178` and line 188.
- `/operations`: universe process-documents switch, action select, and action
  ticker input lack programmatic names at
  `cockpit-ui/components/cockpit/operations/operations-screen.tsx:581`,
  line 622, and line 638.

## Recommended Implementation Slices

Slice 1, lowest collision:

- `cockpit-ui/components/cockpit/chat/terminal-input.tsx`
- `cockpit-ui/components/cockpit/holdings/holdings-screen.tsx`
- `cockpit-ui/components/cockpit/holdings/holdings-screen.test.tsx`

Reason: these files have current failures and are not touched by the open PRs
inspected in this turn. The implementation should add durable `aria-label` or
proper `label`/`htmlFor` associations without changing layout, data behavior,
financial truth, backend reads, or holdings calculations.

Suggested validation for slice 1:

- focused Holdings Vitest;
- Cockpit UI TypeScript;
- DOM audit for `/full-chat` and `/holdings` asserting zero failures in those
  two routes.

Slice 2, after adjacent PRs are merged or parked:

- News, Updater, Memory, and low-risk select/input label fixes.

Slice 3, only after current adjacent PRs settle:

- Marketplace, Verification, Operations, and Thesis Audit controls, because
  those files overlap active or recent draft PR surfaces.

## DATA_MISSING

- The original `/tmp/tenn-ui-production-deep-audit.json` was not available as a
  durable repo artifact.
- This audit used empty mocked API payloads, so it proves accessible-name
  failures in visible empty/error states. Data-populated row actions or
  conditional controls may contain additional failures that require route-
  specific seeded fixtures.
