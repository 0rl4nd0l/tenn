# Phase 3G Unblock Options

## Option Review

`GO_COCKPIT_FINAL_CANONICAL_MERGE_TASKCARD_PRESERVE_DRAFT_ONLY`

Recommended after the active Cockpit registry job clears. Preserve the valid Cockpit final canonical merge task card and its report bundle in a separate Cockpit/repo-hygiene preservation task. Do not let Strategy Lab stage, clean, edit, or absorb it.

`GO_PHASE3G_RERUN_AFTER_COCKPIT_FINAL_CARD_RESOLVED`

Recommended only after the Cockpit blocker and any other out-of-scope dirty cards are resolved and fresh `list-active`, `check-overlap`, and `check-diff` are clean or fail only on explicitly approved Phase 3G files.

`DEFER_ACTIVE_COCKPIT_JOB`

Selected as the immediate action from final live registry state. `cockpit_ui_overnight_orchestrator_v1_20260521` is active in the Reporting lane and overlaps the Cockpit final canonical merge card by lane and Cockpit Home files. Do not start the preservation task while this active job owns the lane/surface.

`DEFER_MANUAL_REVIEW_REQUIRED`

Not selected for the requested blocker. There is enough evidence to classify it. Manual review may still be needed for the two newer out-of-scope Cockpit task cards if they remain dirty, because this audit did not inspect them.

`REJECT_TOO_RISKY`

Not selected. A report-only preservation follow-up can be scoped to task-card/report artifacts and does not require touching Cockpit product code, Strategy Lab, runtime/backend/product code, stores, services, tokens, production data, dependencies, or trading paths.

## Current Phase 3G State

The Phase 3G execution task card currently validates.

Current Phase 3G `check-overlap` fails on out-of-scope dirty files:

- `docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md`
- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md`
- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md`
- `docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md`

Current Phase 3G `check-diff --no-write-report` reports the same disallowed files.

Therefore, Phase 3G is not safe to rerun right now. It is safe to attempt a rerun only after the named Cockpit preservation action resolves the requested blocker and a fresh overlap check confirms no remaining unapproved out-of-scope dirt.
