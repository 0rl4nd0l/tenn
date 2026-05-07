---
job_id: cockpit_home_attention_queue_v1_20260507
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_attention_queue_v1_20260507.md
  - reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/**
  - reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/INVESTIGATION.md
  - reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/README.md
  - reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/diff-check.json
  - reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/status.json
  - cockpit-ui/types/cockpit-home.ts
  - cockpit-ui/lib/cockpit-home-contract.ts
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
  - cockpit-ui/lib/mock/cockpit-home-fixtures.ts
  - cockpit-ui/app/api/cockpit/home/route.ts
  - cockpit-ui/components/cockpit/home/**
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/components/cockpit/home/cards/attention-queue-card.tsx
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/cockpit_home.py
  - financial-engine_v2/backend/tests/test_cockpit_home_attention_queue.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_home_attention_queue_v1_20260507
mutation_mode: safe_extension
production_data_access: false
---

# Task

Investigate and, only if safe, wire Cockpit Home Attention Queue v1.

The goal is to replace `NO_ATTENTION_QUEUE_ENDPOINT` only when an existing deterministic local/backend source can support an attention queue contract. If no safe source exists, keep `DATA_MISSING` and produce a report-only finding.

# Context

Cockpit Home is BFF-backed and now has deterministic market-session wiring. Remaining unsupported sections must stay explicit rather than synthesized.

Attention queue was deferred because local follow-up or operational state may exist, but no Home-safe contract has been proven.

# Required preflight

Before any edits:

1. Print branch and HEAD.
2. Run `git status --short --untracked-files=all`.
3. Run `git worktree list`.
4. Show recent relevant commits:
   - Cockpit Home BFF/live wiring
   - market-session milestone
5. Validate this task card using current repo-supported task-card tooling.
6. Run registry/list-active if available.
7. Run registry/check-overlap if available.
8. Claim the task only if there is no lane/file overlap.
9. Stop and report only if collision risk is HIGH.

# Subagent Investigation

The parent agent may use up to three read-only subagents. Subagents must not edit files.

## Subagent A - Home Contract/UI Audit

Inspect:

- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/app/api/cockpit/home/route.ts`
- `cockpit-ui/components/cockpit/home/**`

Report:

- current attention queue contract shape, if any
- current `NO_ATTENTION_QUEUE_ENDPOINT` behavior
- required UI states: READY, PARTIAL, DEGRADED, DATA_MISSING
- tests that need extension
- whether UI can render real queue items without mock substitution

## Subagent B - Backend/Local Source Audit

Inspect existing backend/local state for candidate queue sources. Read-only inspection may include files outside `allowed_files`, but edits are forbidden outside `allowed_files`.

Look for:

- follow-up state
- pending review items
- extraction review queue
- failed jobs or degraded operation summaries
- alerts/notifications
- commentary/research follow-ups
- source-backed tasks already represented locally

Report:

- candidate source files/tables/endpoints
- whether each candidate is deterministic
- whether it is local personal/operational state, not financial truth
- whether it has stable IDs
- whether it has timestamps/status/severity
- whether it can be exposed without production data mutation
- recommended minimal endpoint contract

## Subagent C - Collision/Test Audit

Inspect:

- active registry jobs
- dirty/untracked files
- existing test patterns for Home BFF/backend endpoints
- browser validation requirements

Report:

- collision risk
- exact test commands
- browser validation plan
- hard stops

# Parent Investigation Report

Before implementation, write:

`reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/INVESTIGATION.md`

Include:

- Confirmed facts
- Inferred facts
- DATA_MISSING
- subagent summaries
- candidate source table
- chosen contract, or report-only reason
- implementation go/no-go
- files to touch
- collision risk

# Phase B Implementation Rules

Proceed only if:

- collision risk is LOW or controlled MEDIUM
- no active registry overlap exists
- the source is deterministic and local/backend-owned
- no production data mutation is required
- stable queue item IDs are available or can be deterministically derived
- changes fit within `allowed_files`

Expected endpoint shape, if implemented:

- backend route, likely `GET /api/cockpit/home/attention-queue`
- BFF calls the backend endpoint
- Home contract exposes queue state as READY/PARTIAL/DEGRADED/DATA_MISSING
- queue items include:
  - stable id
  - title
  - reason
  - status
  - severity or priority, if available
  - source/type
  - created/updated timestamp, if available
  - optional target route or source id only if resolvable

If a field is not deterministically available, omit it or mark it unavailable. Do not fabricate.

# Hard Boundaries

Do not touch:

- financial truth extraction
- canonical metric storage
- company memory
- market memory
- thesis memory
- Qdrant
- embeddings
- news ingestion/backfill
- query orchestrator routing
- source-label taxonomy outside Home attention contract needs
- parser routing
- gold labels
- unrelated Cockpit tabs
- market movers
- narrative synthesis
- commentary generation
- source detail resolver unless strictly needed and already proven

Do not create LLM-generated attention items.

Do not convert warnings into financial-truth claims.

Do not hide missing/degraded state.

# Validation

Run the strongest available focused checks.

Frontend:

```bash
cd cockpit-ui
pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts
npx tsc --noEmit --pretty false
pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-contract.ts types/cockpit-home.ts components/cockpit/home --max-warnings=0
```

Backend if backend files change:

```bash
cd financial-engine_v2
.venv/bin/python -m pytest backend/tests/test_cockpit_home_attention_queue.py -q
.venv/bin/python -m ruff check backend/app/services/cockpit_home.py backend/app/routes/cockpit_api.py backend/tests/test_cockpit_home_attention_queue.py
```

General:

```bash
git diff --check
```

Run repo-supported task-card check-diff if available.

Browser validation:

Use an isolated validation backend if the live backend is stale.
Use temporary local state only if needed.
Validate `/api/cockpit/home` returns 200.
Validate `/` renders Home through the BFF.
Confirm `NO_ATTENTION_QUEUE_ENDPOINT` is removed only when real deterministic queue data exists.
Confirm empty queue is not treated as an error.
Confirm unsupported items remain `DATA_MISSING`, `PARTIAL`, or `DEGRADED`.
Confirm no mock fixture text.
Confirm no `/chat` or `/api/chat` request from Home rendering.
Confirm nested buttons remain 0.

# Definition of Done

- Task card exists and validates.
- Investigation report exists.
- If safe source exists, backend plus BFF plus tests are wired.
- If no safe source exists, no endpoint is fabricated and the report explains why.
- Unsupported Home sections remain explicit.
- Tests, lint, type, and browser validation are reported with exact results.
- Registry claim is released.
- Final git status is reported.
- Milestone commit is created only if implementation lands and repo instructions require it.

# Final Report

Write:

`reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/README.md`

Required sections:

- Branch / HEAD
- Task card path
- Registry / lock status
- Preflight summary
- Subagent reports summary
- Candidate source table
- Go/no-go decision
- Files changed
- Tests/lint/type/browser validation with exact results
- What is now live
- What remains DATA_MISSING and why
- Collision risks
- DATA_MISSING
- Final git status
- Project Memory save recommendation
