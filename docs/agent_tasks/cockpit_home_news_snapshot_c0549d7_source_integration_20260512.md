---
job_id: cockpit_home_news_snapshot_c0549d7_source_integration_20260512
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - reports/agent_jobs/cockpit_home_news_snapshot_c0549d7_source_integration_20260512/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 2400
output_dir: reports/agent_jobs/cockpit_home_news_snapshot_c0549d7_source_integration_20260512
mutation_mode: safe_extension
production_data_access: false
---

# Task

Integrate the source behavior from `c0549d754cb501254873b34c66d9aec7d12b95d8` (`milestone(reporting): wire home market update signals`) into the current preserve branch.

# Scope

- Bring forward the Cockpit Home market update/news snapshot behavior from commit `c0549d754cb501254873b34c66d9aec7d12b95d8`.
- Allowed source/test files are only:
  - `cockpit-ui/components/cockpit/home/home-page.tsx`
  - `cockpit-ui/lib/cockpit-home-api.ts`
  - `cockpit-ui/lib/cockpit-home-api.test.ts`
- Preserve current HEAD behavior for source labels, DATA_MISSING handling, marketplace recency, sidebar navigation, and existing Home BFF contract semantics.

# Forbidden Surfaces

- Do not edit `financial-engine_v2/**`.
- Do not edit `cockpit-ui/components/cockpit/cockpit-sidebar.tsx`.
- Do not edit marketplace files.
- Do not edit source-label/provenance route files.
- Do not touch runtime data, Qdrant, Postgres, SQLite stores, news stores, company memory, market memory, user thesis memory, or financial truth data.
- Do not restart any runtime during implementation.

# Required Preflight

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md`
- `git status --short --untracked-files=all`
- `git rev-parse --abbrev-ref HEAD`
- `git rev-parse HEAD`

# Implementation Guidance

- Prefer applying the relevant hunks from `git show c0549d754cb501254873b34c66d9aec7d12b95d8 -- cockpit-ui/components/cockpit/home/home-page.tsx cockpit-ui/lib/cockpit-home-api.ts cockpit-ui/lib/cockpit-home-api.test.ts`.
- Do not apply old task/report artifacts from that commit.
- If conflicts require changes outside allowed files, stop and report.
- If resolving source hunks would remove current DATA_MISSING/source-label safeguards, stop and report.

# Validation

- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md`
- `cd cockpit-ui && pnpm test -- cockpit-home-api`
- `cd cockpit-ui && pnpm test -- home-page`
- `cd cockpit-ui && pnpm lint`

# Abort Conditions

- Active registry overlap on any allowed source file.
- Dirty changes in allowed source files before implementation that are not owned by this task.
- Any required edit outside allowed files.
- Any non-trivial conflict in DATA_MISSING/source-label semantics.
- Any need to mutate runtime/data stores.
