---
job_id: cockpit_accessible_controls_memory_updater_v1_20260601
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_memory_updater_v1_20260601.md
  - reports/agent_jobs/cockpit_accessible_controls_memory_updater_v1_20260601/README.md
  - reports/agent_jobs/cockpit_accessible_controls_memory_updater_v1_20260601/status.json
  - reports/agent_jobs/cockpit_accessible_controls_memory_updater_v1_20260601/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_memory_updater_v1_20260601/diff-check.json
  - reports/agent_jobs/cockpit_accessible_controls_memory_updater_v1_20260601/accessibility_after.json
  - cockpit-ui/components/cockpit/memory/memory-screen.tsx
  - cockpit-ui/components/cockpit/updater/updater-screen.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
stale_after_seconds: 7200
output_dir: reports/agent_jobs/cockpit_accessible_controls_memory_updater_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: pr_create
related_issue: 53
---

# Cockpit Accessible Controls: Memory and Updater

## Objective

Fix the narrow issue #53 accessibility gap on the Cockpit Memory and Updater
screens by adding durable programmatic names to visible inputs and select
triggers that currently rely on placeholder text or nearby visual labels.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-reporting-accessible-controls-memory-updater-v1-20260601`.
- Branch: `safe/reporting-accessible-controls-memory-updater-v1-20260601`.
- Parent live branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Issue: #53.
- Primary lane: Reporting.
- Intended files: this task card, this job's report artifacts, and the two
  narrow Cockpit UI component files listed in `allowed_files`.
- Contested surfaces touched: none from the AGENTS contested list.
- Collision risk: MEDIUM because the Memory page is a memory-management UI
  surface; changes must remain presentation-only and must not alter memory
  persistence, routing, or backend requests.
- Decision: proceed as SAFE EXTENSION after validation, overlap check, and
  registry claim.

## Contract Check

- Target system layer: Cockpit client UI only.
- Relevant contract rules: backend remains the sole authority; Cockpit is a
  client/orchestration layer; Cockpit must not bypass retrieval/storage layers
  or define canonical data.
- What must not change: backend APIs, extraction, retrieval, memory storage,
  financial truth, source/evidence labels, user-thesis behavior, Qdrant,
  Postgres, runtime/model/GPU configuration, route semantics, and visible
  layout/data behavior.
- Why safe: the change only adds accessible names to existing controls and
  preserves current values, handlers, placeholders, component structure, and API
  calls.
- GPU process check required: no. This task does not spawn, restart, or depend
  on `llama-server`.

## Required Behavior

- Memory ticker filter input has a durable accessible name.
- Memory search input has a durable accessible name.
- Memory statement textarea has a durable accessible name.
- Updater ticker input has a durable accessible name.
- Updater year-range select trigger has a durable accessible name.
- Existing placeholders, layout, values, handlers, API calls, and disabled
  states remain unchanged.

## Forbidden

- Backend changes.
- Memory store writes outside normal UI behavior.
- Qdrant, Postgres, news, extraction, or production data mutation.
- Route rewiring, synthetic memory data, or fallback data.
- Financial truth, source/evidence label, or retrieval changes.
- Broad #53 accessibility rewrites outside Memory and Updater.
- Touching files owned by active PRs or unrelated cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_memory_updater_v1_20260601.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_memory_updater_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_memory_updater_v1_20260601.md --repo-root .`
- Targeted ESLint for touched UI files.
- TypeScript check for the Cockpit UI.
- Rendered Chromium DOM accessibility audit for `/memory` and `/updater` with
  mocked backend responses.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_controls_memory_updater_v1_20260601.md --repo-root .`
- Registry release and final status check.

## Final Report Requirements

- Files changed.
- Exact validation commands and results.
- Rendered accessibility audit result.
- Explicit statement that backend, persistence, retrieval, financial truth,
  source labels, and GPU/runtime configuration were not changed.
- Remaining blockers or DATA_MISSING.
