---
job_id: cockpit_home_missing_producers_audit_v1_20260519
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md
  - reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519/
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit Cockpit Home missing producers after NVMe runtime relaunch, route parity resolution, and APEX/M40 classification.

Do not implement first. Classify which Home `DATA_MISSING` / `PARTIAL` signals are expected, which have existing backend sources that can be safely wired later, and which should remain explicitly deferred.

# Current confirmed context

The live stack is now NVMe-backed:
- frontend `:8081` cwd is `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/cockpit-ui`
- backend compose points to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2`
- backend `/data` and `/reports` point to `/mnt/tenn-nvme2/...`
- backend health passes
- frontend `/api/cockpit/home` returns HTTP 200

Route parity is resolved:
- `/api/cockpit/home` is intentionally owned by the Next.js BFF
- backend direct `/api/cockpit/home` 404 is expected
- backend `/api/news/status` 404 is expected/absent in this branch

APEX/M40 audit is classified:
- APEX model is loaded on `:8001`
- Tesla M40 is in use by llama/APEX
- tiny direct smoke passes
- status is degraded/not fully trusted because Cockpit chat path still has visible-source guard/prompt-expansion behavior

Current Cockpit Home UI shows:
- `Home state: PARTIAL`
- `NO_RECENT_COMMENTARY`
- `NO_MARKET_UPDATE_SIGNALS`
- `NO_SESSION_SUMMARY_ENDPOINT`
- `Market movers: DATA_MISSING`
- `Home narrative: DATA_MISSING`
- `News & Announcements: DATA_MISSING`
- `Attention Queue: READY`
- `Backend liveness: HTTP 200`
- `Market session: POST_MARKET`
- `Holdings: 0/0 priced`

# Goal

Answer:

1. What exact Home producers are missing?
2. Which missing producers have existing backend routes/services/data sources?
3. Which missing producers are intentionally deferred/not built?
4. Which missing producers are empty because no current data exists?
5. Which missing producers are blocked by missing endpoint, missing job, missing data, route mismatch, or disabled producer?
6. What is the smallest safe next implementation, if any?
7. What should remain `DATA_MISSING`?
8. What tests would prevent mock substitution or false `READY` states?

# Required preflight

Run and report:

- `pwd`
- `readlink -f /home/l4nd0/tenn-runtime`
- `cd /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_missing_producers_audit_v1_20260519.md`
- registry/list-active if supported
- registry/check-overlap if supported
- claim if safe; otherwise report why not

# Inspect read-only

Inspect Home route and producer surfaces:

- `cockpit-ui/app/api/cockpit/home/route.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- backend commentary/news routes used by Home
- backend market session / market movers / narrative / portfolio / attention queue routes
- tests for Cockpit Home backend and BFF routes
- recent reports:
  - NVMe2 live-stack relaunch report
  - route parity home/news status audit report
  - APEX/M40 runtime audit report if available

Search for:
- `NO_RECENT_COMMENTARY`
- `NO_MARKET_UPDATE_SIGNALS`
- `NO_SESSION_SUMMARY_ENDPOINT`
- `DATA_MISSING`
- `market-movers`
- `home narrative`
- `commentary/recent`
- `session summary`
- `attention queue`
- `Home state`
- `mock`
- `fallback`

# Runtime/API smoke

Read-only only. Do not create producer data.

Run and report:

- `curl -fsS http://127.0.0.1:8000/api/health`
- `curl -sS http://127.0.0.1:8081/api/cockpit/home | python3 -m json.tool | head -160`
- curl each backend Home section route discovered from code, for example:
  - `/api/cockpit/home/market-session`
  - `/api/cockpit/home/attention-queue`
  - `/api/cockpit/home/market-movers`
  - `/api/cockpit/home/narrative`
  - `/api/cockpit/home/portfolio`
- curl commentary/news routes Home depends on, for example:
  - `/api/commentary/recent?limit=5`
- curl any session-summary route only if code says it exists

Do not call route endpoints that trigger generation/jobs/backfills unless they are clearly read-only.

# Classification required

For each signal, classify:

## `NO_RECENT_COMMENTARY`
- route/source:
- current result:
- root cause:
  - no data
  - missing endpoint
  - producer disabled
  - route mismatch
  - expected empty state
  - DATA_MISSING
- safe next step:

## `NO_MARKET_UPDATE_SIGNALS`
- route/source:
- current result:
- root cause:
- safe next step:

## `NO_SESSION_SUMMARY_ENDPOINT`
- route/source:
- current result:
- root cause:
- safe next step:

## `Market movers: DATA_MISSING`
- route/source:
- current result:
- root cause:
- safe next step:

## `Home narrative: DATA_MISSING`
- route/source:
- current result:
- root cause:
- safe next step:

## `News & Announcements: DATA_MISSING`
- route/source:
- current result:
- root cause:
- safe next step:

# Hard boundaries

Do not:
- hide `DATA_MISSING`
- convert `PARTIAL` to `READY` unless all required sources are genuinely present
- add mocks
- fabricate Home news/movers/narrative
- start news backfills
- run Qdrant resync
- mutate commentary approvals
- write DBs
- mutate memory
- mutate financial truth
- change parser/extraction code
- change APEX/model/runtime config
- change route parity ownership
- edit source code in this audit task
- commit/stash/clean

# Required output

Write:

`reports/agent_jobs/cockpit_home_missing_producers_audit_v1_20260519/README.md`

Include:

- Confirmed facts
- Inferred facts
- Speculative claims
- DATA_MISSING
- Home producer map
- current API response excerpts/summaries
- root cause classification for each missing signal
- whether each signal is:
  - expected empty state
  - missing producer
  - missing endpoint
  - disabled/deferred feature
  - stale BFF expectation
  - data freshness issue
- recommended next safe implementation task, if any
- exact allowed files for a follow-up safe-extension task
- tests that should be added/updated
- validation commands run
- final git status
- registry release status
- Project Memory save recommendation

# Hard stops

Stop and report if:
- active registry shows overlapping Reporting/Home/Cockpit work
- Home producer classification requires mutating data
- determining root cause requires starting a backfill/job
- routes are inconsistent between frontend and backend in a way that risks broad route rewrite
- any implementation would touch Query Orchestration/news/memory/financial truth beyond a small Home adapter
