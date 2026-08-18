## Tenn Issue Contract Normalization

Task: `jam_failure_to_request_search_triage_v1_20260526`

Classification: `DATA_MISSING` with adjacent links, not normalized as an implementation-ready bug.

## Lane

Primary lane: Query Orchestration
Supporting lanes: Reporting, Provenance
Mode: audit

## GitHub Tracking

Recommended labels applied by #106 normalization: `lane:query-orchestration`, `lane:reporting`, `lane:provenance`, `mode:audit`, `priority:p2`, `risk:medium`, `state:data-missing`, `state:needs-review`, `type:validation-gap`, `type:usability`

Milestone: M3 - Query + Memory Integrity

## Source Evidence

- Jam capture: https://jam.dev/c/438df5f2-c338-4462-9cea-a31154c69d7c
- Original GitHub issue: #40, created from Jam on 2026-05-25.
- Captured URL: `http://localhost:8081/full-chat`.
- Screenshot state: full chat shows `market update today`, a `DATA_MISSING / evidence gaps` answer, a visible missing `recent_news` gap, and suggested next controls including `Check recent news (not connected)`.
- Jam metadata was available, but console-log retrieval through the Jam connector returned HTTP 404 during normalization.

## Why This Matters

The screenshot suggests a user-facing chat/search workflow gap, but it does not
prove whether the failure is a disconnected suggested action, missing recent-news
projection, evidence-envelope behavior, or stale runtime state. Treating it as a
confirmed product bug would bypass the Tenn issue protocol.

## Required Task Card

`docs/agent_tasks/jam_failure_to_request_search_triage_v1_20260526.md`

## Required Report Path

`reports/agent_jobs/jam_failure_to_request_search_triage_v1_20260526/`

## Allowed Files / Surfaces

- Task card and report artifacts for this audit.
- Read-only Jam metadata/screenshot/network/console inspection.
- Read-only inspection of full-chat suggested action wiring, news/search action wiring, existing issue links, and evidence-envelope reports.
- Later implementation files only after this audit proves the exact failing route and a separate task card names those files.

## Forbidden Files / Surfaces

- Product/backend/frontend/runtime code changes in this triage task.
- DB, Qdrant, news, or memory mutation.
- Canonical financial truth mutation.
- Parser routing, extraction prompts, gold labels, model/runtime/GPU/service config changes.
- Hidden fallback answers or source-label relaxation.
- Broad issue closeout or unrelated issue edits.

## Validation

- Retrieve Jam screenshot and metadata.
- Attempt console/network evidence extraction; record `DATA_MISSING` if unavailable.
- Reproduce the full-chat prompt only in a no-mutation environment.
- Check whether existing issues #83, #104, #107, and #116 cover the same root cause.
- Preserve `DATA_MISSING` when current-news or search evidence is unavailable.

## Hard Stops

- Jam evidence cannot prove the failing action or route.
- Reproduction would require live data or runtime mutation.
- The root cause is covered by an existing issue and should be linked instead of duplicated.
- Any fix would weaken evidence labels or fabricate current-news support.

## Definition of Done

- The screenshot-only report is either linked to an existing exact tracker,
  superseded with evidence, or converted into a bounded implementation task.
- If no exact failing action can be proven, the issue remains
  `state:data-missing` with explicit missing evidence.
- No product/runtime/data mutation occurs during triage.

## DATA_MISSING

- Exact user action that failed.
- Browser network payloads for the suggested action or search request.
- Console error payloads; Jam console fetch returned HTTP 404 in this pass.
- Current-route reproduction at a known branch/HEAD/runtime URL.
- Whether this is covered by #83, #104, #107, or #116.

## Follow-Up / Parking / Dependencies

- Adjacent but not exact duplicate: #83 news projection/materialization parity.
- Adjacent but not exact duplicate: #104 cross-route evidence-envelope matrix.
- Adjacent but not exact duplicate: #107 visible context bridge for full chat.
- Adjacent but not exact duplicate: #116 News empty-state value audit.

## Original Jam Evidence

**Screenshot:**
https://cdn-jam-screenshots.jam.dev/18e05d5e12ea22ec6d5372e810ba4365/screenshot/45938f73-336c-450c-8644-26e269974812.png

**Website URL:**
http://localhost:8081/full-chat

**Device and browser info:**
Chrome 148.0.7778.168 (1920x992) | macOS (x86) 15.6.1

**Date and time:**
May 25th 2026 | 1:45am UTC

**Developer information:**
https://jam.dev/c/438df5f2-c338-4462-9cea-a31154c69d7c
