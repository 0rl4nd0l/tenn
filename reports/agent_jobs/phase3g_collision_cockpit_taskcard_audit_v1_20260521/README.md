# Phase 3G Cockpit Task-Card Collision Audit

Job: `phase3g_collision_cockpit_taskcard_audit_v1_20260521`

Lane: Reporting

Mode: AUDIT ONLY / COLLISION TRIAGE REPORT

Decision: `GO_COCKPIT_TASKCARD_PRESERVE_TASK_CARD_DRAFT_ONLY`

Final validation status: report complete; Phase 3G remains blocked in this dirty checkout.

## Summary

The blocker `docs/agent_tasks/cockpit_ui_usefulness_integrate_v1_20260521.md` is a valid uncommitted Cockpit Reporting task card. It is not an active registry job now. It matches the same task-card artifact in the isolated Cockpit integration worktree, whose report bundle shows the Cockpit job was released after producing merge-ready commit `2617337678bc82f03024dd06781dc1b52ddf63a9`.

This is not Strategy Lab evidence and Phase 3G must not clean, delete, stage, unstage, or absorb it. The smallest safe unblock is a separate Cockpit/Repo Hygiene preservation step that handles only the Cockpit task-card draft artifact. After that, Phase 3G can be rerun from fresh preflight if no out-of-allowlist dirty work remains.

During final validation, unrelated live-repo drift appeared: `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md` and active registry job `sloppy_fix_manual_only_pr_landing_v1`. Those were not inspected or touched beyond status/registry reporting.

## Audit Answers

1. Classification: valid uncommitted job-control artifact from a completed/released Cockpit Reporting integration job; preservation candidate, not active Strategy Lab work.
2. Active registry job: no active jobs in the current shared registry sample.
3. Report bundle: no canonical target report bundle was present; the isolated Cockpit worktree contains `README.md`, `status.json`, and `diff-check.json` proving the job released cleanly from the isolated branch.
4. Safe isolated path: yes. Run a separate Cockpit task-card preservation task with ownership of only `docs/agent_tasks/cockpit_ui_usefulness_integrate_v1_20260521.md` and its own report path. Do not include Strategy Lab files.
5. Phase 3G rerun safety: conditionally safe only after the Cockpit artifact is resolved and a fresh preflight confirms no active registry overlap and no unrelated out-of-allowlist dirt.
6. Exact follow-up: immediate `GO_COCKPIT_TASKCARD_PRESERVE_TASK_CARD_DRAFT_ONLY`; subsequent `GO_PHASE3G_RERUN_AFTER_COCKPIT_RESOLVED` after fresh checks pass.

## Evidence Files

- `preflight.md`
- `blocking_file_classification.md`
- `phase3g_unblock_options.md`
- `recommendation.md`
- `status.json`
- `diff-check.json`

## Boundary Result

No Cockpit code, Strategy Lab docs/tests/task cards, runtime/backend/product code, Tenn stores, dependencies, services, tokens, production data, or trading paths were modified by this audit. The only intended writes are this audit task card and this report bundle.
