---
job_id: cockpit_home_live_wiring_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_live_wiring_v1.md
  - reports/agent_jobs/cockpit_home_live_wiring_v1/**
  - reports/agent_jobs/cockpit_home_live_wiring_v1/README.md
  - cockpit-ui/app/page.tsx
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/components/cockpit/home/market-status-header.tsx
  - cockpit-ui/components/cockpit/home/data-health-strip.tsx
  - cockpit-ui/components/cockpit/home/market-pulse-card.tsx
  - cockpit-ui/components/cockpit/home/portfolio-impact-card.tsx
  - cockpit-ui/components/cockpit/home/news-announcements-card.tsx
  - cockpit-ui/components/cockpit/home/attention-queue-card.tsx
  - cockpit-ui/components/cockpit/home/session-summary-card.tsx
  - cockpit-ui/components/cockpit/home/theme-candidates-card.tsx
  - cockpit-ui/components/cockpit/home/source-detail-drawer.tsx
  - cockpit-ui/components/cockpit/home/contextual-assistant.tsx
  - cockpit-ui/components/cockpit/home/evidence-badge.tsx
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-contract.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
  - cockpit-ui/types/cockpit-home.ts
approval_required: true
timeout_seconds: 2400
output_dir: reports/agent_jobs/cockpit_home_live_wiring_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Wire Cockpit Home UI to GET /api/cockpit/home.

Primary lane: Reporting
Supporting lanes: Provenance, Query Orchestration

# Context

Cockpit Home currently has:
- typed frontend contract scaffold
- GET /api/cockpit/home BFF route
- deterministic degraded / DATA_MISSING response semantics
- source-label mapping and attached-source handoff contract

Goal:
- Replace mock-only Home state with BFF-backed state loading.
- Preserve the existing mock session states only as explicit dev/demo fallback if needed, not as silent production truth.
- Render loading, degraded, partial, empty, and DATA_MISSING states clearly.
- Do not wire backend runtime code.
- Do not implement source detail resolver or chat handoff beyond what the current contract safely supports.

# Required preflight

Run and report:

- `pwd`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short --untracked-files=all`
- `git worktree list`
- verify base contains:
  - `d6a8f109cf34 feat(reporting): add cockpit home bff route`
  - `f7a7454 milestone(reporting): cockpit home contract scaffold`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_live_wiring_v1.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_live_wiring_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1`

Claim only if safe.

# Allowed work

Allowed:
- Add client-side load/fetch path for `/api/cockpit/home`.
- Update Home components only as needed to render BFF response fields.
- Add/extend focused frontend tests for:
  - loading state
  - degraded state
  - DATA_MISSING state
  - partial state
  - mock fallback not being silently source-backed
  - source-label display mapping
  - no trust upgrade for context/no-hit/missing/degraded evidence
- Write final report.

# Forbidden work

Do not:
- edit backend runtime code
- edit `financial-engine_v2/backend/app/routes/cockpit_api.py`
- edit `financial-engine_v2/backend/app/services/cockpit_service.py`
- edit `financial-engine_v2/backend/app/services/query_orchestrator.py`
- edit `financial-engine_v2/cockpit/core/chat.py`
- mutate databases, Qdrant, news stores, memory stores, or production/local data
- run ingestion, reindex, resync, or long-running jobs
- change legacy `/chat`
- create direct frontend access to Postgres, Qdrant, filings, embeddings, news stores, or memory stores
- fabricate source IDs, evidence IDs, source-backed status, health states, or canonical financial numbers
- implement a new source detail resolver unless already supported by the BFF contract
- implement full Home-to-chat source hydration unless safely supported by existing contract and tests
- commit without explicit later instruction

# Implementation constraints

The UI must:
- fetch only from `/api/cockpit/home`
- preserve existing market open / pre-market / post-market / degraded visual states where possible
- show explicit loading and degraded states
- render DATA_MISSING visibly where sections are unavailable
- preserve backend evidence labels without upgrading trust
- distinguish local personal holdings from financial truth
- avoid hiding partial backend failures behind mock data
- keep mock fixtures clearly marked as demo/dev fallback if still used

# Validation

Run:

From `cockpit-ui/`:
- focused unit/component tests added or updated for Home live wiring
- `pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`
- any relevant Home component tests if present
- `npx tsc --noEmit --pretty false`
- `pnpm exec eslint` on changed Home/BFF files

From repo root:
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_live_wiring_v1.md`

# Final report

Write:

`reports/agent_jobs/cockpit_home_live_wiring_v1/README.md`

Include:
1. Branch / HEAD / worktree / dirty status
2. Task card and registry status
3. Base commits verified
4. Files changed
5. UI data-loading behavior
6. Loading / degraded / DATA_MISSING rendering behavior
7. Mock fallback behavior
8. Source-label and trust behavior
9. Chat/source handoff behavior, if any
10. Tests run and exact results
11. Collision risk
12. DATA_MISSING
13. Whether this is safe to commit
14. Whether a browser validation task should follow
15. Project Memory save recommendation

Hard stop:
Stop and report only if:
- isolated worktree is not clean before task files are created
- registry overlap appears
- task-card validation fails
- backend edits appear necessary
- Home UI cannot be wired without fabricating data or hiding degraded states
- implementation requires direct data-store access
- implementation requires legacy /chat changes
- collision risk becomes HIGH

After completing:
- Do not commit.
- Report exact files changed and exact validation results.
