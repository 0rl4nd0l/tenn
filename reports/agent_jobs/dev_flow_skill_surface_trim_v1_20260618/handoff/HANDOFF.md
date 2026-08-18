# Handoff

## Executive Summary

The reversible skill-surface trim is implemented locally in a fresh canonical
worktree. Six broad/backend `SKILL.md` entrypoints were deleted, and their
useful behavior was rehomed into core skills, `docs/dev_flow/SKILLS_SURFACE.md`,
and templates. The next action is to commit, push, and open a focused PR under
the owner's explicit approval.

## State

- status: ready_for_pr
- branch: `control-plane/dev-flow-skill-surface-trim-v1-20260618`
- HEAD: `acb7e9a7df6a9b75d14beff16c750693a4aab5e6` plus local diff
- base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- latest_canonical: `bae8eda25633cf651849c5681d7ffcb00160fbf9`
- task_card: `docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md`
- report_bundle: `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/`

## Session ID / Thread ID / Goal ID

- session_id: `DATA_MISSING`
- thread_id: `019ed9d4-f829-7083-a9e5-a5df56a4f5d0`
- codex_goal_id: `DATA_MISSING`
- source_session_ref: `codex:thread:019ed9d4-f829-7083-a9e5-a5df56a4f5d0`

## Branch/Worktree/Base

- worktree: `/home/l4nd0/tenn-dev-flow-skill-surface-trim-v1-20260618`
- upstream: `DATA_MISSING`
- canonical_head_at_start: `acb7e9a7df6a9b75d14beff16c750693a4aab5e6`
- latest_canonical_at_pre_pr_validation:
  `bae8eda25633cf651849c5681d7ffcb00160fbf9`
- merge_base: `acb7e9a7df6a9b75d14beff16c750693a4aab5e6`
- dirty_state: local task-card/docs/skills/report diff only
- latest_canonical_overlap: none

## Completed Work

- Created and validated task card.
- Verified PR #375 merged and PR #367 remains open/superseded.
- Appended a live claimed task-ledger entry.
- Deleted six auxiliary visible skill entrypoints.
- Added the skill-surface doc and frame/operator-notes templates.
- Updated core skills and worker/review templates to carry rehomed behavior.

## What Changed

- Visible `.agents/skills/*/SKILL.md` count is reduced from 16 to 10.
- `tenn-issue` owns candidate ranking instead of `tenn-auto-progress`.
- `tenn-goal-report` owns optional frame mode through templates.
- `tenn-git-guard` owns common task-card/registry safety.
- `tenn-fix` owns worker delegation and final review gate routing through templates.

## Commits

- none

## PRs

- PR #375: merged canonical source for this worktree.
- PR #367: open but superseded; not merged or changed.

## Issues

- none updated

## Files Changed

- See `README.md` for the full touched file list.

## Tests And Validation

- See `VALIDATION.md`.

## Reports/Task Cards Created

- `docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md`
- `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/README.md`
- `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/VALIDATION.md`
- `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/PR_REVIEW.md`
- `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/handoff/HANDOFF.md`
- `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/handoff/NEXT_GOAL.md`
- `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/handoff/LEDGER_ENTRY.json`

## Git Status And Dirt

- Local branch has uncommitted task-card/docs/skills/report changes.
- `reports/` is ignored; force-add report artifacts if committing.

## Ledger Status

- live_ledger: appended claimed entry at `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/task-ledger.jsonl`
- committed_ledger: present but not updated
- task_id: `dev_flow_skill_surface_trim_v1_20260618`
- status: `done` after final append
- next_action: review and commit/PR if accepted

## Docs Impact

- docs_impact: `DOCS_UPDATED`
- docs_checked:
  - `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/SKILL_RECOMMENDATIONS.md`
  - `reports/agent_jobs/dev_flow_skills_bloat_audit_v1_20260617/BACKEND_GUARDRAILS.md`
- docs_changed:
  - `docs/dev_flow/SKILLS_SURFACE.md`
  - `docs/dev_flow/templates/FRAME.md`
  - `docs/dev_flow/templates/OPERATOR_NOTES.md`
  - `docs/dev_flow/templates/WORKER_TASK.md`
  - `docs/dev_flow/templates/WORKER_RESULT.md`
  - `docs/dev_flow/templates/PR_REVIEW.md`
- docs_followup:
  - none
- stale_docs_discovered:
  - historical task cards still mention deleted skills; left unchanged as evidence.
- reason: The visible repo skill surface changed.

## Model And Subagent Routing

- task_tier: `medium`
- recommended_model: `standard coding model`
- actual_model: `GPT-5 Codex`
- why_this_model: Multi-file repo control-plane skill/doc trim.
- worker_model_allowed: `not_applicable`
- worker_decision_limit: `not_applicable`
- escalation_needed: `no`
- subagents_used:
  - none

## Failed Attempts / Mistakes

- First live ledger append failed because `validation.status` was `in_progress`; changed to schema-valid `partial` and reran successfully.

## Open Risks

- No fresh Codex session was started to prove the next advertised skill list.
- No commit or PR existed when this handoff was first written; this continuation
  has owner approval to commit, push, and open a focused PR.

## Owner Decisions Needed

- None for PR creation; the owner approved commit/push/PR follow-through.

## Durable Lessons Learned

- Broad planning and backend guard skills should live behind core Tenn commands
  or docs/templates unless they need first-class user invocation.

## Next 10 Milestones

1. Stage task-card/docs/skills/report files, using `git add -f` for reports.
2. Commit the local diff.
3. Push the branch.
4. Open a focused PR against `migration/clean-runtime-baseline-reconstruct-v1`.
5. Verify PR checks and mergeability.
6. Leave PR #367 unmerged and superseded unless Orlando gives a new decision.

## Next Action

Commit, push, and open a focused PR.

## Short Next `/goal`

Read `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/handoff/HANDOFF.md`, run `tenn-git-guard`, verify the task card and ledger state, then review and commit or revise the local skill-surface trim.

## Do-Not-Touch Boundaries

- Product/runtime/data/extraction/count-24 paths.
- Host-global skill/config roots.
- PR #367 branch/worktree.
- Git cleanup, merge, rebase, reset, stash, or deletion without explicit approval.

## Evidence Grades

- VERIFIED: worktree, branch, HEAD, PR #375 merged state, PR #367 open state, registry read-only state, task card validation, local diff.
- USER_REPORTED: instruction to treat PR #367 as superseded by #375.
- INFERRED: deleted `SKILL.md` files will reduce next-session visible repo skill surface.
- DATA_MISSING: upstream branch, fresh-session advertised skill list.
