# Phase 3G Unblock Options

## Option: GO_COCKPIT_TASKCARD_PRESERVE_TASK_CARD_DRAFT_ONLY

Recommended immediate action.

Run a separate Cockpit/Repo Hygiene task that owns only:

- `docs/agent_tasks/cockpit_ui_usefulness_integrate_v1_20260521.md`
- its own report path

The task should preserve the Cockpit integration task card as Cockpit Reporting job-control evidence without touching Strategy Lab files. It should not merge the Cockpit code unless that is separately approved.

Why this is the smallest safe unblock:

- The file is valid task-card evidence.
- The underlying Cockpit job has an isolated released report bundle and merge-ready commit.
- The target checkout has only the uncommitted task card artifact, not active Cockpit code changes.
- A separate Cockpit preservation task removes the Phase 3G collision without letting Strategy Lab clean or absorb unrelated work.

## Option: GO_PHASE3G_RERUN_AFTER_COCKPIT_RESOLVED

Conditionally safe after the Cockpit artifact is resolved.

Required fresh checks before rerun:

- `/home/l4nd0/tenn` still resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch and HEAD are rechecked.
- Registry `list-active` and Phase 3G `check-overlap` pass.
- The Cockpit task card is no longer dirty outside the Phase 3G allowlist.
- This audit task card/report dirt is either already checkpointed by its own lane or otherwise absent from the Phase 3G target dirty state.
- Strategy Lab source worktrees and candidate files are rechecked.

## Option: DEFER_ACTIVE_COCKPIT_JOB

Not selected.

Reason: current registry sample reports no active jobs. The Cockpit isolated report shows the job was released.

## Option: DEFER_MANUAL_REVIEW_REQUIRED

Not selected for the task-card collision itself.

Manual review would become relevant only if the next task tries to merge the Cockpit UI code, because that is outside this audit and outside Phase 3G.

## Option: REJECT_TOO_RISKY

Not selected.

Reason: a report-only classification and a separate task-card preservation path are low/medium risk and do not require touching runtime, backend, Cockpit code, Strategy Lab files, stores, dependencies, services, tokens, production data, or trading paths.

## Current Phase 3G Status

Phase 3G remains blocked in the current dirty checkout. It should not be rerun until the Cockpit task-card artifact is resolved by a separate Cockpit/Repo Hygiene action and fresh preflight proves the target checkout is clean enough for the Phase 3G allowlist.
