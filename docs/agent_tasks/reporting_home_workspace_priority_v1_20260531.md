---
job_id: reporting_home_workspace_priority_v1_20260531
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md
  - reports/agent_jobs/reporting_home_workspace_priority_v1_20260531/
  - reports/agent_jobs/reporting_home_workspace_priority_v1_20260531/README.md
  - reports/agent_jobs/reporting_home_workspace_priority_v1_20260531/status.json
  - reports/agent_jobs/reporting_home_workspace_priority_v1_20260531/validation.json
  - reports/agent_jobs/reporting_home_workspace_priority_v1_20260531/diff-check.json
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/lib/cockpit-home-api.test.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/reporting_home_workspace_priority_v1_20260531
mutation_mode: safe_extension
production_data_access: false
---

# Reporting Home Workspace Priority V1

Resolve GitHub issue #42 by restoring Cockpit Home's primary workspace panels as the first scroll content while keeping Strategy Lab status and artifact review available lower on the page.

## Scope

- Move the Strategy Lab status and artifact review cards below the Home workspace children.
- Preserve existing Strategy Lab routes, fetch behavior, labels, and read-only framing.
- Add or update a focused Home test proving the Useful Now workspace renders before the Strategy Lab block.

## Forbidden

- No backend, RAG, financial truth, canonical data, DB/Postgres, Qdrant, memory, extraction/parser, provider, runtime, GPU, dependency, lockfile, or route changes.
- No changes to Strategy Lab semantics or data-fetching contracts.
- No edits to contested Cockpit route, chat, memory, holdings, watchlist, thesis, marketplace, or BFF control-path files.
- No cleanup, deletion, or staging of unrelated task-card artifacts.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md`
- focused Vitest for `cockpit-home-api`
- targeted ESLint for changed UI/test files
- TypeScript
- Next build if practical
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md`
