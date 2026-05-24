# Recommendation

Immediate recommendation: `DEFER_ACTIVE_COCKPIT_JOB`

Next recommendation after the active Cockpit job clears: `GO_COCKPIT_FINAL_CANONICAL_MERGE_TASKCARD_PRESERVE_DRAFT_ONLY`

## Rationale

The blocker is a valid untracked Cockpit task card with a report bundle proving the associated final canonical merge job was blocked before claim/merge. It is job-control evidence and should be preserved by a separate Cockpit/repo-hygiene task, not cleaned up or absorbed by Strategy Lab.

The Cockpit product change targeted by that merge appears already present at current `HEAD` via a patch-equivalent commit, so the preservation should be draft-only/evidence-only unless a fresh Cockpit-specific task proves otherwise.

Final live registry state includes an active Cockpit Reporting job, `cockpit_ui_overnight_orchestrator_v1_20260521`, overlapping this lane/surface. The preservation action should wait until that job releases or a fresh registry sample proves it no longer overlaps.

## Smallest Safe Follow-Up

After the active Cockpit job clears, create a separate preservation task scoped to Cockpit/repo-hygiene evidence only. The exact allowlist should include:

- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md`
- `reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521/README.md`
- `reports/agent_jobs/cockpit_ui_usefulness_final_canonical_merge_v1_20260521/diff-check.json`
- This audit task card/report bundle if the goal is to avoid this audit becoming the next Phase 3G dirty-file blocker.

Forbidden in that follow-up:

- Strategy Lab docs/tests/task cards/reports
- Cockpit product code
- Runtime/backend/product code
- Tenn stores
- Dependencies/lockfiles
- Services/tokens/production data
- Paper/live/trading paths
- Unrelated dirty work

## Phase 3G

After the Cockpit blocker is preserved, run fresh preflight for Phase 3G. If `list-active` is empty and `check-overlap` no longer reports out-of-scope Cockpit/audit cards, Phase 3G can be rerun under its existing bounded task-card contract.

Until then, Phase 3G remains blocked by unrelated repo-hygiene/task-card dirt.
