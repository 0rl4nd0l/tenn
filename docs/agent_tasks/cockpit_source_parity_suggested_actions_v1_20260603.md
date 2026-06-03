---
job_id: cockpit_source_parity_suggested_actions_v1_20260603
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_source_parity_suggested_actions_v1_20260603.md
  - reports/agent_jobs/cockpit_source_parity_suggested_actions_v1_20260603/README.md
  - reports/agent_jobs/cockpit_source_parity_suggested_actions_v1_20260603/status.json
  - reports/agent_jobs/cockpit_source_parity_suggested_actions_v1_20260603/diff-check.json
  - cockpit-ui/lib/cockpit-chat-actionability.ts
  - cockpit-ui/lib/cockpit-chat-actionability.test.ts
  - cockpit-ui/lib/route-surface.test.ts
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - cockpit-ui/components/cockpit/chat/chat-screen.test.tsx
  - cockpit-ui/scripts/check-route-surface.mjs
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_source_parity_suggested_actions_v1_20260603
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Source Parity And Suggested Actions

## Goal

Resolve the `#288` and `#122` dependency chain in one bounded frontend slice:

- prove that this worktree contains real Cockpit source, not only build artifacts,
- add a route-surface parity guard for the core Cockpit BFF/backend contract,
- wire safe suggested-next actions into the existing confirmation/progress flow,
- keep the work inside the chat/UI/reporting surface without widening into
  unrelated runtime or truth changes.

## GitHub Scope

- `#288` `[Repo Hygiene] Restore Cockpit UI source and add route-surface parity checks`
- `#122` `[Reporting] Wire Cockpit chat suggested next actions to guarded actions and progress logs`
- `#120` is a dependency check only. Do not widen into a broad pending-action
  redesign unless current `#122` work cannot be completed safely without it.

## Primary Lane

Reporting

## Supporting Lanes

- Query Orchestration
- Evaluation

## Mode

SAFE EXTENSION

## Boundaries

- Work only in the exact allowed frontend files plus this task card and report
  bundle.
- Do not edit backend runtime config, extraction logic, parser logic, memory
  stores, Qdrant, Docker/systemd, or production data.
- Do not reintroduce artifact-only `cockpit-ui` assumptions from the
  `tmp/sloppy-fix-demo` branch.
- Reuse the existing `action_preview` plus action-job progress pattern instead
  of inventing a second proposal protocol.
- Suggested actions that execute mutating, long-running, or network/data-changing
  work must still require explicit user confirmation before execution.
- Keep `Review filing group` inside the safe UI context if it does not map
  cleanly to a backend action.

## Required Preflight

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_source_parity_suggested_actions_v1_20260603.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_source_parity_suggested_actions_v1_20260603.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_source_parity_suggested_actions_v1_20260603.md`
- confirm no active shared-registry collision touches the allowed files
- inspect current `cockpit-ui` chat/action code before editing

## Implementation Targets

### `#288`

- add a route-surface check script for representative Cockpit source files plus
  core BFF/backend route pairs
- add focused Vitest coverage for the route-surface guard
- use the existing full-source worktree as the source-restored baseline for this
  slice; do not edit `.next/` or artifact-only surfaces

### `#122`

- convert `Pull market data` and `Run metric extraction` from `(not connected)`
  labels into real guarded action proposal controls when a valid ticker is
  available
- route those controls through preview -> confirmation -> action-job progress
  using the existing chat action surfaces
- keep explicit progress messages visible in chat for queued/running/completed
  or failed outcomes
- keep `Review filing group` wired only to a safe local UI action unless a
  backend action mapping is already clear and bounded

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_source_parity_suggested_actions_v1_20260603.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_source_parity_suggested_actions_v1_20260603.md`
- `node cockpit-ui/scripts/check-route-surface.mjs`
- `corepack pnpm --dir cockpit-ui exec vitest run lib/route-surface.test.ts lib/cockpit-chat-actionability.test.ts components/cockpit/chat/terminal-message.test.tsx components/cockpit/chat/chat-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/chat/terminal-message.tsx components/cockpit/chat/chat-screen.tsx lib/cockpit-chat-actionability.ts`
- `corepack pnpm --dir cockpit-ui exec tsc -p tsconfig.json --noEmit --incremental false`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_source_parity_suggested_actions_v1_20260603.md`
- release registry claim after validation/report capture

## Report

Write final evidence under:

`reports/agent_jobs/cockpit_source_parity_suggested_actions_v1_20260603/`

## Hard Stops

- active registry overlap on the allowed chat/UI files
- `#122` requires broader pending-action redesign outside the bounded surface
- the suggested-action wiring requires backend route ownership changes outside
  the allowed files
- route-surface parity requires editing artifact-only `.next/` output
- validation fails and cannot be explained without widening scope
