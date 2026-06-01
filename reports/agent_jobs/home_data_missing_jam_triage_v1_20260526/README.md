# Home Data Missing Jam Triage

Issue: #41, `missing data`

## Decision

Keep #41 open as `DATA_MISSING`. The refreshed Jam evidence confirms a broad
Cockpit Home missing-data state, but it still splits across separate Home
portfolio, commentary/news, market-update signal, and narrative/workflow
surfaces. No single root cause is proven, and product changes would be unsafe
from this audit alone.

## Evidence Refreshed

- Jam `b5925467-3c7e-4fd8-bac0-3ca558e01ab4` is a screenshot-type Jam linked
  to GitHub #41.
- Screenshot route is Cockpit Home at `http://localhost:3000/`.
- Screenshot shows `Useful Now` with three `DATA_MISSING` signals:
  - `Portfolio gap`
  - `News gap`
  - `Market Movers gap`
- Screenshot shows the portfolio gap as a backend portfolio endpoint timeout
  after 3000ms.
- Screenshot shows the news gap as no approved recent commentary sources.
- Screenshot shows the market-movers gap as no queued market-update follow-up
  signals.
- Screenshot shows `Market Pulse` and `News & Announcements` preserving
  `DATA_MISSING` instead of fabricating summaries.
- Screenshot shows `My Portfolio Impact` marked `LOCAL PERSONAL DATA` with
  `DATA_MISSING` numeric fields and no canonical-financial-truth claim.
- Screenshot shows the attention queue as `READY` with no queued items.

## Connector Results

- Jam metadata retrieval succeeded.
- Jam screenshot retrieval succeeded.
- Jam network retrieval succeeded with redacted browser/network events.
- Jam user-event retrieval succeeded, but the events are navigation/reload
  events only and do not prove a user click root cause.
- Jam console retrieval returned HTTP 404 even though metadata reports a ready
  console payload.

## Current Runtime Probe

No current local service was available for a safe read-only reproduction:
ports 3000, 3001, and 8000 had no listeners, and bounded curl probes to the
Home BFF and backend health/portfolio routes failed with connection refused.
No backend, frontend, worker, database, Qdrant, news, memory, or runtime
service was started for this audit.

## Gap Mapping

- `Portfolio gap` and `My Portfolio Impact`: covered by #86 and draft PR #179
  for audit/result-review. Do not close #41 on that basis because #179 keeps
  #86 open and records follow-up product clarity work after Home PR ownership
  settles.
- `News gap` and `News & Announcements`: partially adjacent to #83 for news
  projection/materialization parity and closed #116 for News empty-state value.
  No current exact issue proves a Home recent-commentary producer fix, so this
  remains `DATA_MISSING` under #41.
- `Market Movers gap` and `Market Pulse`: no exact tracker was found for
  `NO_MARKET_UPDATE_SIGNALS`. Closed #114 helps nightly news freshness inputs
  but does not prove queued market-update follow-up signals now exist. This
  remains `DATA_MISSING` under #41 unless a bounded follow-up is approved.
- Home narrative producer gaps are adjacent rather than directly visible in
  this screenshot crop. #151 and draft PR #159 cover the read-only narrative
  decision path.
- #44 is closed and covered a distinct partial-banner truncation issue, not
  this broad Jam triage.

## Safe Closeout Decision

Do not close #41 as fixed. Do not mutate product code from this evidence
alone. Leave #41 open with links to the mapped trackers and use a later bounded
task card if the unresolved `NO_RECENT_COMMENTARY` or
`NO_MARKET_UPDATE_SIGNALS` gaps should become implementation work.

## Remaining DATA_MISSING

- A current `/api/cockpit/home` response body from the failure environment.
- A current backend `/api/cockpit/home/portfolio` response body from the
  failure environment.
- Browser console logs from the Jam.
- A non-navigation user-event timeline proving a specific click or workflow.
- A current reproduction against a known running branch/runtime URL.
- An exact Home recent-commentary producer route/fix.
- An exact Home market-update signal producer route/fix.
