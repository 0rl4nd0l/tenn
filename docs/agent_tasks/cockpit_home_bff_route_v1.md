---
job_id: cockpit_home_bff_route_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_bff_route_v1.md
  - reports/agent_jobs/cockpit_home_bff_route_v1/**
  - cockpit-ui/app/api/cockpit/home/route.ts
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-contract.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
  - cockpit-ui/types/cockpit-home.ts
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_home_bff_route_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Create Cockpit Home BFF Route v1.

Primary lane: Reporting
Supporting lanes: Query Orchestration, Provenance

# Context

Cockpit Home has a committed frontend contract scaffold but is not wired to real backend/BFF data yet.

Known milestone:
- Cockpit Home contract scaffold landed before this task.
- The scaffold defines deterministic Home state fields, source/evidence identity fields, DATA_MISSING/degraded semantics, source-label mapping, and attached-source handoff shape using backend-resolvable `{ source_id, source_kind }`.

Goal:
- Add a narrow frontend BFF route at `cockpit-ui/app/api/cockpit/home/route.ts`.
- Add a small BFF assembly/helper layer if useful.
- Return a typed response that conforms to the existing Cockpit Home contract.
- Prefer deterministic degraded/DATA_MISSING states when upstream data is unavailable.
- Do not wire the Home page to this route yet.

# Allowed work

Allowed:
- Add `cockpit-ui/app/api/cockpit/home/route.ts`.
- Add `cockpit-ui/lib/cockpit-home-api.ts`.
- Add focused tests for BFF response assembly and degraded/DATA_MISSING behavior.
- Extend the existing Cockpit Home contract/types only if needed for the route.
- Write report artifacts under `reports/agent_jobs/cockpit_home_bff_route_v1/`.

# Forbidden work

Do not:
- edit backend runtime code
- edit `financial-engine_v2/backend/app/routes/cockpit_api.py`
- edit `financial-engine_v2/backend/app/services/cockpit_service.py`
- edit `financial-engine_v2/backend/app/services/query_orchestrator.py`
- edit `financial-engine_v2/cockpit/core/chat.py`
- wire `cockpit-ui/app/page.tsx` or `home-page.tsx` to live data yet
- mutate databases, Qdrant, news stores, memory stores, or production/local data
- run ingestion, reindex, resync, or long-running jobs
- change legacy `/chat`
- add hidden frontend retrieval directly against Qdrant/Postgres/files
- let LLM output define canonical numbers, source IDs, evidence IDs, health states, or trust labels
- commit without explicit later instruction

# Required preflight

Run and report:

- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short --untracked-files=all`
- `git worktree list`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_bff_route_v1.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_bff_route_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn`

Claim only if safe.

# Implementation constraints

The route should:
- be deterministic
- use existing frontend proxy/helper patterns where available
- never directly read Postgres, Qdrant, filings, embeddings, news stores, memory stores, or local production data
- preserve backend source-label semantics
- return explicit degraded/DATA_MISSING states when upstream surfaces are unavailable or not implemented
- keep holdings/personal portfolio data separate from canonical financial truth
- avoid source trust upgrades
- not call legacy `/chat`

Acceptable v1 behavior:
- It is okay if some sections return deterministic degraded/DATA_MISSING placeholders because no dedicated backend endpoint exists yet.
- It is okay if the route composes only existing safe surfaces where current frontend BFF patterns already exist.
- It is not okay to fabricate source-backed evidence or canonical financial truth.

# Validation

Run focused validation:

- focused Vitest test for the new BFF helper/route if available
- existing `cockpit-home-contract.test.ts`
- `npx tsc --noEmit --pretty false` from `cockpit-ui/`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_bff_route_v1.md`

# Final report

Write:

`reports/agent_jobs/cockpit_home_bff_route_v1/README.md`

Include:

1. Branch / HEAD / worktree / dirty status
2. Task card and registry status
3. Files changed
4. Route contract implemented
5. Upstream surfaces used or intentionally not used
6. DATA_MISSING / degraded semantics
7. Source-label and source-ID behavior
8. Chat handoff behavior
9. Tests run and exact results
10. Collision risk
11. DATA_MISSING
12. Whether Home UI live wiring can be considered next
13. Project Memory save recommendation

Hard stop:
Stop and report only if:
- isolated worktree is not clean before task files are created
- registry overlap appears
- task-card validation fails
- backend edits appear necessary
- production data access would be required
- implementation would require changing legacy `/chat`
- implementation would require direct frontend access to Qdrant/Postgres/files
- collision risk becomes HIGH
