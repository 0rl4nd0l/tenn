---
job_id: cockpit_home_bff_route_v1_integration
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_bff_route_v1_integration.md
  - docs/agent_tasks/cockpit_home_bff_route_v1.md
  - reports/agent_jobs/cockpit_home_bff_route_v1_integration/**
  - reports/agent_jobs/cockpit_home_bff_route_v1/**
  - cockpit-ui/app/api/cockpit/home/route.ts
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_home_bff_route_v1_integration
mutation_mode: safe_extension
production_data_access: false
---

# Task

Integrate Cockpit Home BFF Route v1 from isolated branch.

Primary lane: Reporting  
Supporting lanes: Provenance, Query Orchestration

# Context

Isolated milestone:
- `c00ee6b36087 feat(reporting): add cockpit home bff route`

Validation reported on isolated branch:
- `pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`: passed, 2 files / 7 tests
- `npx tsc --noEmit --pretty false`: passed
- `pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-api.test.ts`: passed
- `git diff --check`: passed
- registry active jobs empty after release

# Goal

Cherry-pick or otherwise integrate only the Cockpit Home BFF Route v1 commit into a clean integration branch.

# Allowed work

Allowed:
- task card
- report artifacts
- the five files from the isolated commit
- resolving conflicts only within those files, if needed

# Forbidden work

Do not:
- work in the dirty preserve worktree
- touch remaining untracked preserve task cards
- edit backend runtime code
- edit Home page UI wiring
- mutate data stores
- run ingestion/reindex/resync jobs
- change legacy `/chat`
- stage unrelated files
- commit unrelated work

# Required preflight

Run and report:

- `pwd`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short --untracked-files=all`
- `git worktree list`
- verify whether base contains the contract scaffold commit
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_bff_route_v1_integration.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_bff_route_v1_integration.md --repo-root /mnt/sdb2/home/l4nd0/tenn`

Claim only if safe.

# Integration

Cherry-pick:

- `c00ee6b36087`

Hard stop if the cherry-pick touches files outside allowed_files.

# Validation

Run:

- `git diff --cached --check` if staged
- `git diff --check`
- from `cockpit-ui/`:
  - `pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`
  - `npx tsc --noEmit --pretty false`
  - `pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-api.test.ts`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_bff_route_v1_integration.md`

# Final report

Write:

`reports/agent_jobs/cockpit_home_bff_route_v1_integration/README.md`

Include:
1. Branch / HEAD / worktree / dirty status
2. Task card and registry status
3. Whether the contract scaffold commit was already present
4. Cherry-pick result
5. Exact files changed/committed
6. Validation run and exact results
7. Registry release status
8. Remaining dirty files, if any
9. Whether this is safe to merge/fast-forward/cherry-pick into preserve
10. Whether Home UI live wiring can be considered next
11. Project Memory save recommendation

Do not commit unless the cherry-pick itself creates the commit cleanly or the task-card flow requires a narrow integration commit. Report the exact outcome.
