# News Empty-State Value Audit

## Summary

Issue #116 asked whether `/news` is too passive because it starts from
`DATA_MISSING` until a query is submitted. Current evidence shows the News route
is intentionally search-first and keeps no-query/no-news states honest. The
adjacent Home actionability path is the current proactive context surface and
does not attach missing Home evidence as if it were source-backed. No high
confidence product gap remains in #116.

## Decision

- Close gate: `COMPLETED_WITH_EVIDENCE`
- Finding class: `NO_FOLLOWUP`
- Product remediation landed: NO. This was an audit issue.
- Follow-up required: NO for #116.
- Adjacent open trackers: #40 and #41 remain for broader Jam-derived missing
  search/missing-data reports; they do not block closing this route-specific
  audit.

## Evidence

| Workflow | Current evidence | Result |
| --- | --- | --- |
| First-use `/news` | `cockpit-ui/components/cockpit/news/news-screen.tsx:280` renders News Search; `:300` disables search until query text exists; `:335` renders readiness; `:382` renders the no-query empty state. | Expected search-first state |
| No query / no news | Gemini browser artifact `desktop-news.png` and `audit-results.json` show `NEWS EVIDENCE STATE DATA_MISSING` and no-query guidance. | Honest DATA_MISSING |
| Holdings/watchlist-aware handoff | No direct News-route holdings/watchlist proactive defaults were found. Current architecture keeps proactive handoff in Home/chat actionability instead of inventing News claims. | No News remediation warranted |
| Home recent-context handoff | `cockpit-ui/lib/cockpit-home-actionability.ts:67` blocks chat handoff when Home evidence is DATA_MISSING, and `:206` only builds source actions from attachable news sources. | Honest source boundary |
| User route navigation | Browser artifact for Home included a `Check morning announcements` Full Chat prompt link and `/news` navigation. | Existing proactive entry outside `/news` |

## Boundary Compliance

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No unsourced proactive news summaries were created.
- No product code changed.

## Validation Notes

The audit did not run a fresh browser session because this task is report-only
and existing Gemini browser evidence from 2026-05-26 covers `/news`. Current
static source inspection confirms the no-query and Home evidence-handoff
contracts still exist at this branch HEAD.
