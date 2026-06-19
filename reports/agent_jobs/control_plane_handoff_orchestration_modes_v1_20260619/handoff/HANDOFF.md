# Handoff

## Executive summary

Control-plane handoff/orchestration mode refinement is implemented on PR #380,
with focused review fixes applied locally. The next session should read this
handoff first, run the standard Tenn preflight, review validation and PR state,
then continue as orchestrator only if follow-up work remains.

## State

- status: pr_review_fixes_validated_ready_to_push
- branch: `control-plane/handoff-orchestration-modes-v1-20260619`
- HEAD: `f44803bba049ea1d2cfe9341b0f9af4379736bdf` plus local diff
- base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- task_card:
  `docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md`
- report_bundle:
  `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/`

## Session ID / thread ID / goal ID

- session_id: `DATA_MISSING`
- thread_id: `019ede57-4580-7ea2-9b4c-6dedc292c708`
- codex_goal_id: `DATA_MISSING`
- source_session_ref: `codex:thread:019ede57-4580-7ea2-9b4c-6dedc292c708`

## Branch/worktree/base

- worktree:
  `/home/l4nd0/tenn-control-plane-handoff-orchestration-modes-v1-20260619`
- upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- canonical_head: `f44803bba049ea1d2cfe9341b0f9af4379736bdf`
- merge_base: `f44803bba049ea1d2cfe9341b0f9af4379736bdf`
- dirty_state: local control-plane task-card, skills, docs, templates, and
  report artifacts only

## Completed work

- Created and validated a task card.
- Wrote design note before behavior edits.
- Added handoff artifact-map, next-first-action, do-not-touch, milestone, and
  next-goal requirements.
- Added `tenn-fix` fresh-session orchestrator mode.
- Added zoom-out / contrarian mode to `tenn-explain` and `tenn-review-board`.
- Updated worker, handoff, explain, board, and next-goal templates.
- Updated `docs/dev_flow/SKILLS_SURFACE.md` to keep orchestration and zoom-out
  as modes, not broad new skills.
- Applied PR #380 review fixes: shared `NEXT_GOAL.md` generic again,
  handoff-specific continuation moved to `HANDOFF_NEXT_GOAL.md`,
  `stop_condition_hit` added to bridge validation/tests, and skill-surface
  metadata marked pending PR #380.
- Applied PR #380 follow-up review fix: `stop_condition_hit` now accepts only
  exact `yes`, `no`, or `DATA_MISSING` values in bridge validation.

## What Changed

- `tenn-handoff` now owns fresh-session continuation with linked artifacts and
  an orchestrator-oriented `NEXT_GOAL.md`.
- `tenn-fix` now has a named fresh-session orchestrator mode for handoff/problem
  continuation.
- `tenn-explain` and `tenn-review-board` now have zoom-out / contrarian modes.
- Worker templates now include lane independence, stop condition, and
  orchestrator review status.
- Visible skill count stayed at 10.

## Commits

- none yet

## PRs

- PR #375: merged, task ledger runtime and repo-native `tenn-handoff`.
- PR #378: merged, visible skill-surface trim.
- PR #380: open, focused control-plane refinement.

## Issues

- none mutated

## Files changed

- See report `README.md`.

## Tests and validation

- See `VALIDATION.md`.

## Reports/task cards created

- `docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md`
- `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/`

## Relevant artifact map

- report_bundles:
  - `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/`
- review_boards:
  - none
- worker_results:
  - none
- task_cards:
  - `docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md`
- validation_artifacts:
  - `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/VALIDATION.md`
  - `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/validation.json`
  - `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/diff-check.json`
- failed_attempts:
  - Initial task-card validation was accidentally run against the stale
    checkout after the first patch landed there; the two misplaced files were
    removed and reapplied by absolute path to the fresh worktree.
- related_handoffs:
  - none for this exact task
- PRs/issues:
  - PR #375
  - PR #378

## Git status and dirt

- Local task-card, skill, docs, template, bridge, test, and report artifacts
  passed final validation and are pending commit.
- `reports/` artifacts are ignored and require `git add -f`.

## Ledger status

- live_ledger:
  `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/task-ledger.jsonl`
- committed_ledger: `docs/agent_registry/task_ledger/LEDGER.jsonl`
- task_id: `control_plane_handoff_orchestration_modes_v1_20260619`
- status: live `implementation_started`, `pr_opened`, and PR-review
  `implementation_started` entries appended
- next_action: commit and push to PR #380

## Docs Impact

- docs_impact: `DOCS_UPDATED`
- docs_checked:
  - `.agents/skills/tenn-handoff/SKILL.md`
  - `.agents/skills/tenn-fix/SKILL.md`
  - `.agents/skills/tenn-explain/SKILL.md`
  - `.agents/skills/tenn-review-board/SKILL.md`
  - `docs/dev_flow/SKILLS_SURFACE.md`
  - `docs/dev_flow/templates/*`
- docs_changed:
  - see `README.md`
- docs_followup:
  - none
- stale_docs_discovered:
  - none
- reason: control-plane workflow behavior and artifact shape changed

## Model And Subagent Routing

- task_tier: medium
- recommended_model: standard coding model
- actual_model: GPT-5 Codex
- why_this_model: multi-file control-plane docs/skill/template refinement
- worker_model_allowed: not_applicable
- worker_decision_limit: not_applicable
- escalation_needed: no
- subagents_used:
  - none

## Failed attempts / mistakes

- Misapplied the first task-card/design patch to the original checkout because
  the patch tool used the initial cwd. Removed only those two session-created
  files and reapplied them to this fresh worktree by absolute path.

## Open risks

- PR #380 awaits the pushed review-fix commit and fresh CI results.
- No fresh Codex session has consumed the new handoff mode yet.

## Owner decisions needed

- None for PR creation; the owner requested a focused PR.

## Durable Lessons Learned

- For sibling worktrees, use absolute paths with the patch tool when the initial
  cwd is a different checkout.

## What the next session should do first

Read this `HANDOFF.md`, then run branch/HEAD/upstream/dirty preflight,
`tenn-git-guard`, task-card validation, task-ledger validation, and active
registry read-only check before making any claim or edit.

## What not to touch

- Product/runtime/data/extraction/count-24 paths.
- Host-global Codex skill/config roots.
- The PR #378 skill trim.
- Old dirty checkout cleanup or stale PR triage.
- Branch/worktree deletion, merge, rebase, cherry-pick, reset, stash, prune.
- GitHub issue/PR mutation beyond the focused PR requested here.

## Next 5-10 key milestones

1. Commit the allowlisted control-plane diff.
2. Push to PR #380.
3. Re-check PR #380 status and checks.
4. If follow-up is needed, continue from this handoff as orchestrator.

## Next Action

Commit, push to PR #380, and re-check CI.

## Short next `/goal`

Read `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/handoff/HANDOFF.md` first. Run Tenn control-plane preflight, validate the task card and ledger, check the active registry read-only, then act as orchestrator: preserve the boundaries, review validation/PR state, integrate only coherent follow-up changes, and stop on owner-boundary or DATA_MISSING.

## Do-not-touch boundaries

- Product/runtime/data/extraction/count-24.
- Host-global skill/config roots.
- Old dirty checkout cleanup.
- Skill-surface re-bloat.

## Evidence grades

- VERIFIED: branch, HEAD, base, PR #375/#378 merged state, task-card validation,
  registry read-only state, ledger validation, visible skill count before/after
  initial implementation.
- USER_REPORTED: owner requested the focused PR and boundaries.
- INFERRED: fresh sessions will lose less context because handoff artifacts now
  require explicit links and orchestrator next-goal instructions.
- DATA_MISSING: fresh-session consumption proof.
