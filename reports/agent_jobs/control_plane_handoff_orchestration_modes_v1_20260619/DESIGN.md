# Design Note

## Current Evidence

- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `f44803bba049ea1d2cfe9341b0f9af4379736bdf`.
- PR #375 is merged and introduced repo-native task ledger plus `tenn-handoff`.
- PR #378 is merged at the base tip and trimmed the visible repo skill surface.
- Active registry read-only check returned no active jobs.
- Task ledger validation passed against live and committed sources.
- Duplicate searches found prior ledger/handoff and skill-surface work, but no
  active duplicate for this exact refinement.

## What Already Exists

- `tenn-handoff` already requires git state, task ledger state, validation,
  milestones, do-not-touch boundaries, evidence grades, and `NEXT_GOAL.md`.
- `docs/dev_flow/templates/HANDOFF.md` already has sections for state,
  validation, reports/task cards, ledger, docs impact, model/subagent routing,
  failed attempts, risks, milestones, next action, next goal, and boundaries.
- `tenn-fix` already presents itself as an orchestrator, requires task-card and
  ledger discipline, supports bounded workers, and says small workers must not
  make high-risk decisions.
- `WORKER_TASK.md` and `WORKER_RESULT.md` already require worker lane, worktree,
  allowed files, result path, decision limit, and Codex final decision-making.
- `tenn-review-board` already has multi-perspective review, risk/model routing,
  minority objection handling, and exactly one actionable decision.
- `tenn-explain` already has counter-lineage mode for confusing metrics.
- `docs/dev_flow/SKILLS_SURFACE.md` already records the trimmed visible command
  set and the rehomed auxiliary entrypoints.

## What Is Missing

- Handoff does not explicitly require links or paths for all relevant report
  bundles, review boards, worker results, task cards, PRs/issues, validation
  artifacts, failed attempts, known risks, and related handoffs.
- Handoff's fresh-session prompt does not explicitly require the next session
  to read the handoff first, run preflight, then act as orchestrator.
- Handoff asks for the next 10 milestones, but not specifically the next 5-10
  key milestones of a larger repair.
- `tenn-fix` has orchestration behavior, but no named fresh-session
  orchestrator mode for continuing from a handoff/problem statement.
- Worker templates need an explicit stop condition and integration review
  status to make delegation safer for fresh orchestrator sessions.
- Zoom-out / contrarian review exists only implicitly through board
  perspectives and counter-lineage. It needs a named mode with root-problem,
  report-loop, breadth, and production-readiness questions.
- The skill-surface doc does not yet state that orchestration and zoom-out are
  modes, not new broad visible skills.

## Where To Implement

- Implement handoff continuation requirements in `.agents/skills/tenn-handoff/SKILL.md`,
  `docs/dev_flow/templates/HANDOFF.md`, and `docs/dev_flow/templates/NEXT_GOAL.md`.
- Implement orchestrator mode in `.agents/skills/tenn-fix/SKILL.md`,
  `docs/dev_flow/templates/WORKER_TASK.md`, and
  `docs/dev_flow/templates/WORKER_RESULT.md`.
- Implement zoom-out / contrarian mode in `.agents/skills/tenn-explain/SKILL.md`,
  `.agents/skills/tenn-review-board/SKILL.md`,
  `docs/dev_flow/templates/EXPLAIN.md`, `docs/dev_flow/templates/BOARD.md`,
  and `docs/dev_flow/templates/BOARD_DECISION.json`.
- Update `docs/dev_flow/SKILLS_SURFACE.md` to preserve the intentionally small
  visible surface and explain how to avoid skill-bloat regression.

## Exact Files To Change

- `docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md`
- `.agents/skills/tenn-handoff/SKILL.md`
- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-explain/SKILL.md`
- `.agents/skills/tenn-review-board/SKILL.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `docs/dev_flow/templates/HANDOFF.md`
- `docs/dev_flow/templates/NEXT_GOAL.md`
- `docs/dev_flow/templates/WORKER_TASK.md`
- `docs/dev_flow/templates/WORKER_RESULT.md`
- `docs/dev_flow/templates/BOARD.md`
- `docs/dev_flow/templates/BOARD_DECISION.json`
- `docs/dev_flow/templates/EXPLAIN.md`
- `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/*`

## Stop Conditions

- A changed path falls outside the task-card allowlist.
- Visible skill count increases or a new visible skill is created.
- Any product/runtime/data/extraction/count-24 or host-global path changes.
- Registry, GitHub issue/PR body, merge/rebase/cherry-pick, branch deletion,
  worktree cleanup, or stale-checkout cleanup becomes necessary.
- Task ledger or task-card validation fails in a way that would make mutation
  unsafe.
- Current canonical has drifted and now contains a superior implementation of
  this exact behavior.
