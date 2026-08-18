## Tenn Issue Contract Normalization

Task: `home_data_missing_jam_triage_v1_20260526`

Classification: `DATA_MISSING` with existing issue links. The Jam capture is
too broad to implement directly.

## Lane

Primary lane: Reporting
Supporting lanes: Cockpit, Runtime, Query Orchestration
Mode: audit

## GitHub Tracking

Recommended labels applied by #106 normalization: `lane:reporting`, `lane:cockpit`, `mode:audit`, `priority:p1`, `risk:medium`, `state:data-missing`, `state:needs-review`, `type:bug`, `type:validation-gap`

Milestone: M5 - Cockpit Analyst Workflow

## Source Evidence

- Jam capture: https://jam.dev/c/b5925467-3c7e-4fd8-bac0-3ca558e01ab4
- Original GitHub issue: #41, created from Jam on 2026-05-25.
- Captured URL: `http://localhost:3000/`.
- Screenshot state: Cockpit Home shows `DATA_MISSING` for Useful Now, portfolio gap, news gap, market movers gap, market pulse, and portfolio impact.
- Jam metadata was available, but no console/network postprocessing payloads were available from the Jam connector during normalization.

## Why This Matters

The screenshot points to user-visible Home data gaps, but it does not isolate a
single root cause. Portfolio, news/commentary, market-update, and Home rendering
paths have different owners and validation requirements.

## Required Task Card

`docs/agent_tasks/home_data_missing_jam_triage_v1_20260526.md`

## Required Report Path

`reports/agent_jobs/home_data_missing_jam_triage_v1_20260526/`

## Allowed Files / Surfaces

- Task card and report artifacts for this audit.
- Read-only Jam screenshot/metadata inspection.
- Read-only inspection of Home BFF payloads, backend Home portfolio route, news/commentary status, market-movers status, and existing Home issues.
- Later implementation files only after a separate task card identifies the exact failing route.

## Forbidden Files / Surfaces

- Product/backend/frontend/runtime code changes in this triage task.
- DB, Qdrant, news, or memory mutation.
- Canonical financial truth mutation.
- Parser routing, extraction prompts, gold labels, model/runtime/GPU/service config changes.
- Fabricating portfolio totals, news summaries, or market movers.
- Broad issue closeout or unrelated issue edits.

## Validation

- Retrieve Jam screenshot and metadata.
- Reproduce Home with a known branch/HEAD/runtime URL when safe.
- Capture frontend `/api/cockpit/home` response and backend Home portfolio behavior.
- Determine whether each visible gap is covered by #86, #83, #114, or #116.
- Preserve `DATA_MISSING` for unavailable upstream data.

## Hard Stops

- Jam evidence cannot isolate the root cause.
- Reproduction would require production data mutation.
- The issue splits across existing trackers and should be linked instead of duplicated.
- Any fix would fabricate missing data or weaken honesty labels.

## Definition of Done

- Each visible Home gap in the capture is mapped to an existing issue, a new
  bounded follow-up, `NO_FOLLOWUP`, or `DATA_MISSING`.
- If no single root cause is proven, this issue remains `state:data-missing`.
- No product/runtime/data mutation occurs during triage.

## DATA_MISSING

- Current frontend `/api/cockpit/home` response at failure time.
- Current backend `/api/cockpit/home/portfolio` response at failure time.
- Console and network payloads; Jam had no available processed events in this pass.
- Whether the market-movers gap is caused by #83, #114, or a separate Home BFF gap.
- Whether the portfolio panel gap is fully covered by #86.

## Follow-Up / Parking / Dependencies

- Portfolio panel coverage: #86.
- News empty-state/value coverage: #116.
- News projection/materialization coverage: #83.
- Nightly ticker-universe repair and market update freshness: #114.

## Original Jam Evidence

**Screenshot:**
https://cdn-jam-screenshots.jam.dev/d1246a09b9d5b177ae413d5228102165/screenshot/2b7f3bfc-9741-49ec-b2aa-6d5fb6a2f7e3.png

**Website URL:**
http://localhost:3000/

**Device and browser info:**
Chrome 148.0.7778.168 (1920x992) | macOS (x86) 15.6.1

**Date and time:**
May 25th 2026 | 2:48am UTC

**Developer information:**
https://jam.dev/c/b5925467-3c7e-4fd8-bac0-3ca558e01ab4
