---
job_id: cockpit_home_remaining_endpoints_investigate_wire_v1_20260507
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507.md
  - reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/**
  - reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/INVESTIGATION.md
  - reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/README.md
  - reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/diff-check.json
  - reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/status.json
  - cockpit-ui/types/cockpit-home.ts
  - cockpit-ui/lib/cockpit-home-contract.ts
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
  - cockpit-ui/lib/mock/cockpit-home-fixtures.ts
  - cockpit-ui/app/api/cockpit/home/route.ts
  - cockpit-ui/components/cockpit/home/**
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/cockpit_home*.py
  - financial-engine_v2/backend/app/services/cockpit_home.py
  - financial-engine_v2/backend/tests/test_cockpit_home*.py
  - financial-engine_v2/backend/tests/test_cockpit_home_market_session.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507
mutation_mode: safe_extension
production_data_access: false
---

# Task

Investigate the remaining Cockpit Home backend/BFF endpoint gaps using read-only subagents where useful, produce a reconciled report, then wire only the low-risk deterministic remaining Home contracts that can be supported by existing repo data without crossing Tenn truth boundaries.

# Context

Cockpit Home is already BFF-backed through `GET /api/cockpit/home` and no longer mock-only. The UI now honestly surfaces backend gaps as `PARTIAL`, `DEGRADED`, and `DATA_MISSING`.

Known visible missing signals include:

- `NO_MARKET_SESSION_ENDPOINT`
- `NO_MARKET_MOVERS_ENDPOINT`
- `NO_ATTENTION_QUEUE_ENDPOINT`
- `PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS`
- `PORTFOLIO_DAY_CHANGE_UNAVAILABLE`
- `NO_RECENT_COMMENTARY`

Do not hide gaps with mock/demo data. Do not fabricate market state, source IDs, evidence IDs, canonical financial numbers, news summaries, or narrative synthesis.

# Required preflight

Before any investigation or writes:

1. Print branch and HEAD.
2. Run `git status --short --untracked-files=all`.
3. Run `git worktree list`.
4. Show recent commits relevant to Cockpit Home.
5. Check whether a task-card mechanism exists and validate this card if supported.
6. Run registry/list-active if available.
7. Check for active lane/file overlap.
8. Stop and report only if collision risk is HIGH.

Use current repo-supported commands. Do not assume exact registry command syntax without verifying help/docs.

# Subagent investigation plan

The parent agent may use up to three read-only subagents. Subagents must not edit files or make commits.

## Subagent A - Home contract inventory

Inspect:

- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/app/api/cockpit/home/route.ts`
- `cockpit-ui/components/cockpit/home/**`

Report:

- every Home field currently live, partial, degraded, or DATA_MISSING
- expected source of each field
- existing tests covering the contract
- which fields can be deterministically wired now
- which fields must remain DATA_MISSING

## Subagent B - Backend endpoint/source feasibility

Inspect existing backend routes/services relevant to Home, especially:

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- existing holdings/portfolio pricing paths
- existing news/commentary/market status paths
- existing source/detail/evidence-id paths
- existing alert/review/attention queue paths, if any

Report:

- existing endpoints that can safely feed Home
- missing endpoints
- source of truth for each endpoint
- whether each output is deterministic, local personal data, external web context, memory context, or DATA_MISSING
- implementation risk per endpoint

## Subagent C - Collision/test/runtime audit

Inspect:

- active task cards or registry locks
- dirty/untracked/deleted files touching Reporting/Cockpit/Home/backend routes
- existing tests that should be extended
- browser validation expectations
- likely lint/type/test commands

Report:

- collision risk
- test plan
- browser validation plan
- exact stop conditions

# Parent reconciliation report

Before implementation, write:

`reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/INVESTIGATION.md`

Include:

- Confirmed facts
- Inferred facts
- DATA_MISSING
- endpoint-by-endpoint table
- proposed wiring plan
- files to touch
- collision risk
- whether Phase B is safe

# Phase B implementation rules

Proceed to implementation only if:

- collision risk is LOW or controlled MEDIUM
- active registry shows no overlap
- dirty files do not touch the allowed surfaces
- subagent reports agree on endpoint ownership
- required files are within `allowed_files`
- implementation can remain a safe extension

Wire remaining Home contracts in this priority order, but only where deterministic existing data exists:

1. Market session / next event
2. Portfolio summary improvements with currency safety
3. Market movers or news summary, only if an existing deterministic source exists
4. Attention queue, only if an existing deterministic source exists
5. Source detail / Home-to-chat handoff only if resolvable source/evidence IDs already exist

For each field:

- If real deterministic data exists, wire it.
- If data does not exist, keep `DATA_MISSING` with a precise reason.
- If data is partial, expose `PARTIAL` or `DEGRADED` honestly.
- If holdings/portfolio data is used, label it local personal data, not financial truth.
- If currency aggregation is ambiguous, do not aggregate as a single total.
- If market movers/news/commentary cannot be deterministically sourced, do not synthesize.

# Hard boundaries

Do not touch:

- financial truth extraction logic
- canonical metric storage
- company memory
- market memory
- thesis memory
- Qdrant
- embeddings
- news ingestion/backfill pipelines
- source-label taxonomy outside Home contract needs
- query orchestrator routing
- parser routing
- gold labels
- unrelated Cockpit tabs
- root HTML hydration warning
- Vercel Analytics dev logging

Do not introduce new cloud dependencies.

Do not use LLM narrative synthesis to fill Home endpoint gaps.

Do not implement broad architecture rewrites.

# Validation

Run the strongest available subset, including:

```bash
cd cockpit-ui
pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts
npx tsc --noEmit --pretty false
pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-contract.ts types/cockpit-home.ts components/cockpit/home --max-warnings=0
```

If backend files change, also run focused backend tests, for example:

```bash
cd financial-engine_v2
python -m pytest backend/tests/test_cockpit_home*.py -q
```

Also run:

```bash
git diff --check
```

Run repo-supported task-card/check-diff validation if available.

Browser validation target:

Start/use the existing Cockpit dev server according to current repo docs. Validate `/` renders Home through the live BFF route. Confirm previously visible missing signals are replaced only where real deterministic data exists. Confirm unsupported sections still show DATA_MISSING/PARTIAL/DEGRADED. Confirm no mock/demo substitution. Confirm no sidebar nested-button regression. Confirm no accidental `/chat` or `/api/chat` request from Home rendering unless explicitly expected.

# Definition of done

- Investigation report exists.
- Endpoint-by-endpoint gap table exists.
- Only safe deterministic endpoints are wired.
- Unsupported endpoints remain visibly DATA_MISSING/PARTIAL/DEGRADED.
- Tests/lint/type checks are reported with exact results.
- Browser validation is reported with exact route/status observations.
- Report includes changed files, branch, HEAD, task card, registry status, remaining risks, DATA_MISSING, and save recommendation.
- Worktree final status is reported.

# Final report

Write:

`reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/README.md`

Required sections:

- Branch / HEAD
- Task card path
- Registry / lock status
- Preflight summary
- Subagent reports summary
- Endpoint-by-endpoint decision table
- Files changed
- Tests/lint/type/browser validation with exact results
- What is now live
- What remains DATA_MISSING and why
- Collision risks
- DATA_MISSING
- Final git status
- Project Memory save recommendation
