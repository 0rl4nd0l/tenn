# Recommendation

Decision: `GO_COCKPIT_TASKCARD_PRESERVE_TASK_CARD_DRAFT_ONLY`

## Required Follow-Up

Create a separate Cockpit/Repo Hygiene preservation task card with a narrow allowlist for:

- `docs/agent_tasks/cockpit_ui_usefulness_integrate_v1_20260521.md`
- that preservation task's report directory

The task should preserve/checkpoint the Cockpit task-card draft artifact only. It must not touch Strategy Lab files, Cockpit code, runtime/backend code, stores, dependencies, services, tokens, production data, or trading paths unless a later explicit mutation task approves that scope.

## Rationale

The blocker is not active work. It is a valid uncommitted task-card artifact from a Cockpit job that completed in an isolated integration worktree and released its registry claim. Deleting or absorbing it from Phase 3G would cross ownership boundaries. Preserving it under a separate Cockpit task is the smallest safe action that removes the collision while keeping Strategy Lab clean.

## Phase 3G Next Step

After the Cockpit task-card artifact is resolved, rerun Phase 3G only from fresh preflight:

- confirm branch, HEAD, dirty status, and `/home/l4nd0/tenn` resolution;
- confirm shared registry active jobs;
- run Phase 3G `check-overlap`;
- verify no unrelated dirty files sit outside the Phase 3G allowlist;
- then rerun the approved Phase 3G consolidation if those gates pass.

Until then, Phase 3G remains blocked.

## Not Authorized By This Audit

- Cleaning, removing, staging, unstaging, committing, merging, cherry-picking, stashing, or resetting the Cockpit task card.
- Editing Cockpit code.
- Editing Strategy Lab docs, tests, or task cards.
- Touching runtime/backend/product code, Tenn stores, dependencies, services, tokens, production data, or paper/live/trading paths.
