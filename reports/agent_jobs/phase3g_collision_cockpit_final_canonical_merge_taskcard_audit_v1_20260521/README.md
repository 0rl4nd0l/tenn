# Phase 3G Collision: Cockpit Final Canonical Merge Task-Card Audit

Job: `phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521`

Mode: audit only / collision triage report.

## Decision

`docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md` is valid uncommitted Cockpit job-control evidence. It is not an active registry job now. Its associated local report bundle proves the final canonical merge job stopped before claim/merge, so the artifact should not be deleted or absorbed by Strategy Lab.

The smallest safe unblock path after the current active Cockpit registry job clears is:

1. `GO_COCKPIT_FINAL_CANONICAL_MERGE_TASKCARD_PRESERVE_DRAFT_ONLY`
2. Then `GO_PHASE3G_RERUN_AFTER_COCKPIT_FINAL_CARD_RESOLVED`, but only after fresh status and registry checks confirm no remaining out-of-scope Cockpit/audit task cards still block Phase 3G.

Immediate recommendation from final live registry state: `DEFER_ACTIVE_COCKPIT_JOB`. A new active Cockpit Reporting job, `cockpit_ui_overnight_orchestrator_v1_20260521`, overlaps the requested Cockpit final canonical merge card by lane and Cockpit Home files.

## Current Caveat

Current live checks show additional out-of-scope dirty task cards beyond the requested blocker:

- `docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md`
- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md`
- `docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md`

Those were not inspected or modified in this focused audit except as visible dirty-state evidence. If they remain dirty, Phase 3G will still fail overlap even after the final canonical merge card is preserved.

During closeout, registry state changed from no active jobs to two active jobs: `cockpit_ui_overnight_orchestrator_v1_20260521` and `codex_workday_checkin_protocol_v1_20260521`. The Cockpit job overlaps the requested blocker; the workday check-in job does not.

## Boundaries

No Cockpit task-card blocker, Cockpit code, Strategy Lab file, runtime/backend/product code, Tenn store, dependency, service, token, production data, or trading path was modified by this audit.

## Validation Closeout

- Audit task-card validation: passed.
- `status.json` syntax validation: passed.
- Registry `list-active`: passed; final state has active `cockpit_ui_overnight_orchestrator_v1_20260521` and `codex_workday_checkin_protocol_v1_20260521`.
- Registry `check-overlap`: failed as expected on active/dirty out-of-scope work; no claim was taken.
- `agent_job_contract.py check-diff`: failed as expected on pre-existing out-of-scope dirty task cards; wrote `diff-check.json`.
- `git diff --check`: passed.
- `git diff --cached --check`: passed.
- Staged files: none.
- Written files: this audit task card plus the ignored report files in this report directory.
