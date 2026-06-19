# Control Plane Handoff Orchestration Modes V1

## Summary

Implemented a narrow control-plane refinement from fresh canonical
`f44803bba049ea1d2cfe9341b0f9af4379736bdf` after PR #375 and PR #378.

The change keeps the visible repo skill surface at 10 entrypoints. It adds:

- stricter `tenn-handoff` fresh-session continuation requirements
- explicit `tenn-fix` fresh-session orchestrator mode
- zoom-out / contrarian modes in `tenn-explain` and `tenn-review-board`
- template fields for artifact maps, first next action, stop conditions,
  orchestrator review, and production-readiness checks
- `docs/dev_flow/SKILLS_SURFACE.md` guidance that orchestration and zoom-out
  are modes, not new broad visible skills

PR #380 review follow-up fixes:

- restored shared `docs/dev_flow/templates/NEXT_GOAL.md` to a generic directly
  executable next-goal template
- added handoff-only `docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md`
- updated `tenn-handoff` and `HANDOFF.md` to reference the handoff-only prompt
  contract
- added `stop_condition_hit` to OpenCode bridge result validation and focused
  tests
- restricted `stop_condition_hit` to exact `yes`, `no`, or `DATA_MISSING`
  values, rejecting ambiguous text such as `maybe`, `unknown`, and `n/a`
- updated worker result docs to carry stop condition and impact fields
- marked skill-surface freshness metadata as pending PR #380

## Files Changed

- `docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md`
- `.agents/skills/tenn-handoff/SKILL.md`
- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-explain/SKILL.md`
- `.agents/skills/tenn-review-board/SKILL.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `docs/dev_flow/templates/HANDOFF.md`
- `docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md`
- `docs/dev_flow/templates/NEXT_GOAL.md`
- `docs/dev_flow/templates/WORKER_TASK.md`
- `docs/dev_flow/templates/WORKER_RESULT.md`
- `docs/dev_flow/templates/BOARD.md`
- `docs/dev_flow/templates/BOARD_DECISION.json`
- `docs/dev_flow/templates/EXPLAIN.md`
- `docs/dev_flow/worker_bridge/README.md`
- `scripts/opencode_worker_bridge.py`
- `tests/test_opencode_worker_bridge.py`
- `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/*`

## Visible Skill Count

- Before: 10
- After: 10
- New visible skill added: no

## Boundaries Preserved

- No product/runtime/data/extraction/count-24 paths changed.
- No host-global Codex skill/config paths changed.
- No old dirty checkout cleanup or stale PR triage performed.
- No branch deletion, worktree deletion, merge, rebase, cherry-pick, reset,
  stash, prune, or issue/PR closeout performed.

## Current Status

- status: pr_review_fixes_validated_ready_to_push
- branch: `control-plane/handoff-orchestration-modes-v1-20260619`
- base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- task_card:
  `docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md`
- report_bundle:
  `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/`

## Next Action

Commit the PR review fix, push to PR #380, and re-check CI.
