# Cockpit Home Missing Producers Audit

Job: `cockpit_home_missing_producers_audit_v1_20260519`  
Mode: `AUDIT ONLY`  
Runtime root: `/home/l4nd0/tenn-runtime -> /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`  
Branch: `migration/clean-runtime-baseline-reconstruct-v1`  
HEAD: `5dd7ee84b49e`

## Confirmed Facts

- Task card was created at `docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md` and contract validation passed.
- The task card required one schema correction from the pasted content: repo-local frontmatter requires opening `---`; the pasted `ob_id` key was written as `job_id`.
- Registry `list-active` returned `active_jobs: []`.
- Registry `check-overlap` returned `ok: false` only because three pre-existing untracked task cards are dirty outside this task card's `allowed_files`:
  - `docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md`
  - `docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md`
  - `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md`
- No registry claim was taken.
- The live backend health endpoint returned HTTP 200 with `{"status":"ok"}`.
- The live frontend BFF endpoint `http://127.0.0.1:8081/api/cockpit/home` returned HTTP 200 with `data_state=PARTIAL`, `degraded=false`, and five top-level missing signals.
- Backend direct aggregate `/api/cockpit/home` remains intentionally absent on this branch. Home is owned by the Next.js BFF route.
- Backend direct `/api/news/status` remains intentionally absent on this branch. Home news uses `/api/commentary/recent?limit=5`, not `/api/news/status`.
- Backend Home section routes exist and returned HTTP 200:
  - `/api/cockpit/home/market-session`
  - `/api/cockpit/home/attention-queue`
  - `/api/cockpit/home/market-movers`
  - `/api/cockpit/home/narrative`
  - `/api/cockpit/home/portfolio`
- No data stores, Qdrant, commentary approvals, backfills, producer jobs, runtime config, APEX/M40 config, memory, parser code, or financial truth were mutated.

## Inferred Facts

- Home `PARTIAL` is currently an honest aggregate of real READY sections plus explicit no-hit/deferred producer signals. It is not a route-parity or NVMe runtime failure.
- `NO_RECENT_COMMENTARY` is not a missing endpoint. The endpoint exists and returns an empty approved-source list.
- `NO_MARKET_UPDATE_SIGNALS` is not a missing endpoint. The endpoint exists and reports no queued market-update followup rows.
- `NO_SESSION_SUMMARY_ENDPOINT`, `NO_THEME_CANDIDATES_ENDPOINT`, and `NO_TOMORROW_PREP_ENDPOINT` are intentionally deferred Home narrative subproducers. The backend narrative route exists, but it currently exists to expose explicit `DATA_MISSING`.
- The codebase has lower-level state-store surfaces for session summaries and market-update reports, but they are not currently Home narrative producers.

## Speculative Claims

- A read-only Home narrative adapter could later expose an existing stored session summary or latest market-update report headline if product semantics approve that source. This is not implemented now and should not be treated as current capability.
- A future market-update run may create queued followups that make `market_movers` become `PARTIAL`, but this audit did not run jobs or create producer data.

## DATA_MISSING

- Direct DB/table counts were not inspected because `production_data_access: false`.
- No session-summary route exists beyond the current `/api/cockpit/home/narrative` route, so no separate session-summary endpoint was curled.
- Current root cause for empty source stores is inferred from read-only API results, not from direct DB or file inspection.
- `reports/` is ignored in this checkout; this report exists on disk but may not appear in plain `git status --short`.

## Home Producer Map

| Home surface | BFF source | Backend route/service/data source | Current API result | Classification |
| --- | --- | --- | --- | --- |
| Backend liveness | `/api/health` | FastAPI health route | READY, HTTP 200 | present |
| Market session | `/api/cockpit/home/market-session` | `build_market_session_snapshot()` using XASX calendar | READY, `POST_MARKET` | present |
| Portfolio | `/api/cockpit/home/portfolio` | `state_store.list_holdings()` plus read-only price enrichment | READY, `0/0 priced` | present, expected empty holdings |
| News & Announcements | `/api/commentary/recent?limit=5` | `SourceRegistry().all()` filtered to approved `youtube_transcript` and `market_commentary` | `items=[]`, `count=0` | expected empty state / no current approved commentary |
| Attention Queue | `/api/cockpit/home/attention-queue` | `state_store.list_market_update_followups(status="queued")` | READY, `items=[]` | present, empty queue is READY |
| Market movers | `/api/cockpit/home/market-movers` | same queued market-update followups, converted into mover signals | `DATA_MISSING`, `NO_MARKET_UPDATE_SIGNALS`, `items=[]` | existing producer, no current producer data/job output |
| Home narrative | `/api/cockpit/home/narrative` | `build_home_narrative_snapshot()` | `DATA_MISSING`, three missing subproducer codes | intentionally deferred/missing subproducers |

## Current API Response Summary

Frontend Home BFF excerpt:

```text
ok=true
data_state=PARTIAL
degraded=false
data_missing=[
  NO_RECENT_COMMENTARY,
  NO_MARKET_UPDATE_SIGNALS,
  NO_SESSION_SUMMARY_ENDPOINT,
  NO_THEME_CANDIDATES_ENDPOINT,
  NO_TOMORROW_PREP_ENDPOINT
]
market_session=READY POST_MARKET
portfolio=READY 0/0 priced
market_movers=[]
news=[]
attention_queue_state=READY 0 queued
narrative=DATA_MISSING
```

Backend section results:

```text
/api/cockpit/home/market-session -> 200 READY POST_MARKET
/api/cockpit/home/portfolio -> 200 READY, holdings_count=0, priced_holdings_count=0
/api/cockpit/home/attention-queue -> 200 READY, items=[]
/api/cockpit/home/market-movers -> 200 DATA_MISSING, NO_MARKET_UPDATE_SIGNALS, items=[]
/api/cockpit/home/narrative -> 200 DATA_MISSING, NO_SESSION_SUMMARY_ENDPOINT, NO_THEME_CANDIDATES_ENDPOINT, NO_TOMORROW_PREP_ENDPOINT
/api/commentary/recent?limit=5 -> 200, items=[], count=0
```

## Missing Signal Classification

### `NO_RECENT_COMMENTARY`

- Route/source: BFF calls backend `GET /api/commentary/recent?limit=5`.
- Current result: HTTP 200, `{"items":[],"count":0}`.
- Root cause: no current approved commentary sources from `SourceRegistry`; not a missing endpoint and not a route mismatch.
- Category: expected empty state; no current data; visible `DATA_MISSING` for the Home news section.
- Safe next step: do not fabricate news and do not mutate approvals. Leave `DATA_MISSING` until approved commentary exists through a separate approved ingestion/review workflow.

### `NO_MARKET_UPDATE_SIGNALS`

- Route/source: BFF calls backend `GET /api/cockpit/home/market-movers`; backend `build_market_movers_snapshot()` reads queued market-update followups from `state_store.list_market_update_followups(status="queued")`.
- Current result: HTTP 200, `data_state=DATA_MISSING`, `degraded=true`, `items=[]`, code `NO_MARKET_UPDATE_SIGNALS`.
- Root cause: no queued market-update followup rows are available to convert into mover signals.
- Category: missing data / missing job output; existing endpoint and producer adapter; not a route mismatch.
- Safe next step: no Home code is needed for the empty state. A separate operator/job task may run or schedule market-update production, but this audit must not start it.

### `NO_SESSION_SUMMARY_ENDPOINT`

- Route/source: BFF calls backend `GET /api/cockpit/home/narrative`; backend `build_home_narrative_snapshot()` returns explicit missing narrative state.
- Current result: HTTP 200, `data_state=DATA_MISSING`, `session_summary=null`, and code `NO_SESSION_SUMMARY_ENDPOINT`.
- Root cause: Home v1 has no backend session-summary producer wired into the narrative snapshot.
- Category: intentionally deferred feature / missing subproducer. The narrative route exists; the session-summary producer does not.
- Safe next step: only if product semantics approve it, add a small read-only Home narrative adapter that consumes an existing stored session summary or market-update report and preserves `DATA_MISSING` when absent.

### `Market movers: DATA_MISSING`

- Route/source: backend `GET /api/cockpit/home/market-movers` via `build_market_movers_snapshot()`.
- Current result: HTTP 200, `data_state=DATA_MISSING`, `NO_MARKET_UPDATE_SIGNALS`, `items=[]`.
- Root cause: no current queued market-update followup signals. If followups exist, the route can return PARTIAL mover items with explicit `MARKET_MOVER_PRICE_FIELDS_MISSING` because queued followups do not carry deterministic price/change fields.
- Category: existing producer, no current data/job output; should remain `DATA_MISSING` while empty.
- Safe next step: keep current `DATA_MISSING`. Do not synthesize movers from prices, prose, news, or market state.

### `Home narrative: DATA_MISSING`

- Route/source: backend `GET /api/cockpit/home/narrative`.
- Current result: HTTP 200, `data_state=DATA_MISSING`, `session_summary=null`, `theme_candidates=[]`, `tomorrow_prep=[]`.
- Root cause: deferred narrative subproducers for session summary, theme candidates, and tomorrow prep.
- Category: disabled/deferred feature and missing subproducers; not a live route failure.
- Safe next step: smallest implementation, if approved, is read-only session summary wiring only. Theme candidates and tomorrow prep should remain `DATA_MISSING` unless a source-backed deterministic producer is specified.

### `News & Announcements: DATA_MISSING`

- Route/source: BFF news section is built from backend `GET /api/commentary/recent?limit=5`.
- Current result: HTTP 200, `items=[]`, `count=0`; BFF `news=[]` and top-level `NO_RECENT_COMMENTARY`.
- Root cause: no approved commentary data currently available.
- Category: expected empty state / no current data; not missing endpoint, not route mismatch.
- Safe next step: keep `DATA_MISSING`; do not use `/api/news/status`, RAG, Qdrant, web search, or mock news to fill this panel.

## Expected vs Missing vs Deferred

| Signal | Expected empty state | Missing producer | Missing endpoint | Disabled/deferred | Stale BFF expectation | Data freshness issue |
| --- | --- | --- | --- | --- | --- | --- |
| `NO_RECENT_COMMENTARY` | yes | no | no | no | no | current approved commentary empty |
| `NO_MARKET_UPDATE_SIGNALS` | yes | no | no | no | no | queued followups empty |
| `NO_SESSION_SUMMARY_ENDPOINT` | no | yes | subproducer only | yes | no | no proof from API |
| `Market movers: DATA_MISSING` | yes | no | no | no | no | queued followups empty |
| `Home narrative: DATA_MISSING` | no | yes | subproducers only | yes | no | no proof from API |
| `News & Announcements: DATA_MISSING` | yes | no | no | no | no | current approved commentary empty |

## What Should Remain `DATA_MISSING`

- `News & Announcements` should remain `DATA_MISSING` until `GET /api/commentary/recent?limit=5` returns approved commentary sources with resolvable source IDs.
- `Market movers` should remain `DATA_MISSING` until queued `market_update_followups` exist. If followups exist but do not include deterministic price/change fields, mover rows should remain `PARTIAL` with `MARKET_MOVER_PRICE_FIELDS_MISSING`.
- `Home narrative` should remain `DATA_MISSING` for session summary, theme candidates, and tomorrow prep until a read-only, source-backed producer is explicitly built.
- `/api/news/status` should remain absent for this branch/profile unless a separate product task defines a concrete status payload.
- Backend direct `/api/cockpit/home` should remain absent unless a separate task explicitly changes route ownership. Current public Home ownership is the Next.js BFF.

## Smallest Safe Next Implementation

No implementation is required to fix the current empty commentary or empty market-mover states. Those are honest no-data states.

If a source-code follow-up is desired, the smallest safe implementation is a Home narrative read-only adapter:

- Use only existing backend state-store reads.
- Expose at most a stored session summary or latest deterministic market-update report headline as `session_summary`.
- Do not generate text.
- Do not derive theme candidates or tomorrow prep unless a deterministic source is specified.
- Preserve `DATA_MISSING` when no source row exists.
- Keep the frontend/BFF route ownership unchanged.

Suggested follow-up safe-extension allowed files:

```yaml
allowed_files:
  - docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260519.md
  - financial-engine_v2/backend/app/services/cockpit_home.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_home_attention_queue.py
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-live-shape.test.ts
  - reports/agent_jobs/cockpit_home_narrative_readonly_adapter_v1_20260519/
```

Do not include Query Orchestration, news loaders, Qdrant, memory mutation, parser/extraction code, financial truth, runtime config, or route ownership changes in that follow-up.

## Tests To Add Or Keep

- Backend test: empty `build_market_movers_snapshot()` must return `DATA_MISSING` with `NO_MARKET_UPDATE_SIGNALS`, never `READY`.
- Backend test: empty `build_attention_queue_snapshot()` remains `READY` with zero queued items, so empty operational queue is not conflated with missing market movers.
- Backend test: `/api/cockpit/home/narrative` must stay `DATA_MISSING` until a real producer supplies `session_summary`; empty `session_summary`, empty `theme_candidates`, and empty `tomorrow_prep` cannot be `READY`.
- Backend test: `/api/commentary/recent` with no approved rows returns `items=[]`, and the BFF maps that to `NO_RECENT_COMMENTARY`.
- BFF test: upstream `market-movers` HTTP 200 with `DATA_MISSING` must keep aggregate Home `PARTIAL` and data-health `Market movers=DATA_MISSING`.
- BFF test: upstream `narrative` HTTP 200 with empty narrative fields must keep narrative `DATA_MISSING`, not `READY`.
- UI test: live Home must not render mock fixture company/news text when BFF returns empty news or market movers.
- Live shape test: when `news`, `market_movers`, `session_summary`, `theme_candidates`, or `tomorrow_prep` are empty, the response must carry matching `data_missing` reasons.
- Route-parity test: backend direct `/api/cockpit/home` and `/api/news/status` remain absent for this branch/profile while backend Home section routes remain present.

## Validation Commands Run

- `pwd` -> `/home/l4nd0`
- `readlink -f /home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `cd /home/l4nd0/tenn-runtime`
- `git branch --show-current` -> `migration/clean-runtime-baseline-reconstruct-v1`
- `git rev-parse --short=12 HEAD` -> `5dd7ee84b49e`
- `git status --short`
- `git worktree list`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md` -> pass
- `python3 scripts/agent_job_registry.py list-active` -> pass, `active_jobs=[]`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md` -> failed only on unrelated dirty task cards outside allowed files
- Claim skipped because `check-overlap` was not clean
- `curl -fsS http://127.0.0.1:8000/api/health`
- `curl -sS http://127.0.0.1:8081/api/cockpit/home | python3 -m json.tool | head -160`
- `curl -sS http://127.0.0.1:8000/api/cockpit/home/market-session | python3 -m json.tool`
- `curl -sS http://127.0.0.1:8000/api/cockpit/home/attention-queue | python3 -m json.tool`
- `curl -sS http://127.0.0.1:8000/api/cockpit/home/market-movers | python3 -m json.tool`
- `curl -sS http://127.0.0.1:8000/api/cockpit/home/narrative | python3 -m json.tool`
- `curl -sS http://127.0.0.1:8000/api/cockpit/home/portfolio | python3 -m json.tool`
- `curl -sS 'http://127.0.0.1:8000/api/commentary/recent?limit=5' | python3 -m json.tool`
- `curl -sS -o /dev/null -w '%{http_code}\n' ...` for each backend section route and commentary recent -> all 200

The first attempt to combine `curl -w HTTP_STATUS` with `python3 -m json.tool` failed with JSON `Extra data` because the status line was appended to the body. The endpoints were rerun as pure JSON and status was checked separately.

## Registry Release Status

- Claim was skipped, so no release was required.
- Registry was not mutated for this job.
- Final `python3 scripts/agent_job_registry.py list-active` returned `active_jobs=[]`.

## Final Git Status

Final `git status --short`:

```text
?? docs/agent_tasks/apex_m40_runtime_stability_audit_v1_20260519.md
?? docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md
?? docs/agent_tasks/nvme2_live_stack_relaunch_from_runtime_v1_20260519.md
?? docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md
```

This job created only:

```text
?? docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md
!! reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519/
```

The other three untracked task cards were pre-existing unrelated audit task cards and were not modified by this job.

## Project Memory Save Recommendation

SAVE_RECOMMENDED: persist that after the NVMe runtime relaunch and route-parity resolution, Cockpit Home `PARTIAL` is caused by honest no-hit/deferred Home producers: empty approved commentary, empty queued market-update followups, and intentionally missing narrative subproducers. Also persist that current safe next source-code work is a read-only Home narrative adapter only, while commentary/news/movers should not be mocked or backfilled inside Home.
