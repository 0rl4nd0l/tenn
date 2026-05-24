---
job_id: cockpit_ui_wait_then_actionability_rollout_v1_20260524
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_ui_wait_then_actionability_rollout_v1_20260524.md
  - reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/README.md
  - reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/diff-check.json
  - reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/status.json
  - cockpit-ui/components/cockpit/news/news-screen.tsx
  - cockpit-ui/components/cockpit/news/news-screen.test.tsx
  - cockpit-ui/lib/cockpit-news-actionability.ts
  - cockpit-ui/lib/cockpit-news-actionability.test.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit UI Wait-Then-Actionability Rollout

## Goal

Wait for active Tenn agent work to clear, then implement exactly one small
Cockpit UI actionability slice using existing data only.

## Primary Lane

Reporting

## Supporting Lanes

- Evaluation
- Provenance
- Query Orchestration
- Repo Hygiene

## Mode

WAIT -> AUDIT -> SAFE EXTENSION

## Boundaries

- Do not claim or mutate while another active registry job exists.
- Treat active Cockpit UI, Reporting, runtime topology, Docker, systemd, cron,
  parser, extraction, memory, Qdrant, news, or overlapping docs/task-card work
  as a hard stop for implementation.
- The initial broad Cockpit UI allowlist was for discovery only.
- Before UI editing, this card was narrowed to the News surface exact files.
- Do not edit backend APIs, data stores, parser routes, extraction, runtime
  topology, Docker, systemd, cron, Strategy Lab, Appendix 4C, or Appendix 5B.
- Do not add data requirements or hide `DATA_MISSING`.
- Do not mutate production data.

## Required Preflight

- Wait for `python3 scripts/agent_job_registry.py list-active` to return an
  empty `active_jobs` list, up to six hours.
- Run the requested preflight commands from `/home/l4nd0/tenn`.
- Confirm Appendix 5B commit
  `c5e3f7c50ce3cc2f2597a0bfd1406cddeb818967` is an ancestor of `HEAD`.
- Validate this task card.
- Run registry `check-overlap` and claim only if safe.
- Inspect the recent Cockpit Home actionability report if present.
- Inspect recent runtime/repo topology reports if present without performing
  runtime actions.

## Audit Scouts

- UI Surface Scout: inspect Cockpit News, Watchlist, Full Chat handoff, and Home
  actionability helper.
- Evidence-State Scout: identify which state can be displayed honestly from
  existing data.
- Test/Smoke Scout: identify the smallest validation set for the chosen slice.
- Collision Scout: verify no active registry job, tracked dirty file, or
  untracked job-control artifact would be absorbed or cleaned.

## Candidate Order

1. News actionability/readiness panel.
2. Full Chat handoff evidence-state clarity.
3. Watchlist actionability clarity.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_ui_wait_then_actionability_rollout_v1_20260524.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_ui_wait_then_actionability_rollout_v1_20260524.md`
- `git diff --check`
- Targeted ESLint on changed UI/test files.
- Focused Vitest for changed helper/component tests.
- `corepack pnpm --dir cockpit-ui exec tsc -p tsconfig.json --noEmit --incremental false`
- Playwright smoke if practical and safe.
- `corepack pnpm --dir cockpit-ui build` if practical.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_ui_wait_then_actionability_rollout_v1_20260524.md`

## Report

Write final evidence under:

`reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/`
