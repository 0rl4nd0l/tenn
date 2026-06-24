# Decisions

## Owner Decisions

- 2026-06-24 14:44 +10:00 - Change `tenn-handoff` so the closeout prints just
  the short goal for the new session, pointing at the handoff docs. Impact:
  update the repo-native skill/template contract instead of adding a new skill.
- 2026-06-24 14:44 +10:00 - Commit and merge if safe. Impact: GitHub PR
  creation and merge are allowed for this exact branch after focused
  validation, final diff review, live green checks, and clean mergeability.

## Agent Decisions

- 2026-06-24 14:44 +10:00 - Use a fresh sibling worktree from canonical.
  Evidence: `/home/l4nd0/tenn` was stale for implementation; the new worktree
  passed `tenn-git-guard` as `VALID_TASK_WORKTREE`.
- 2026-06-24 14:44 +10:00 - Do not edit shared generic `NEXT_GOAL.md`.
  Evidence: existing handoff docs explicitly keep handoff-specific prompt
  behavior in `HANDOFF_NEXT_GOAL.md`.
- 2026-06-24 14:44 +10:00 - No new visible skill.
  Evidence: the skills surface is intentionally kept at 10 visible
  `SKILL.md` entrypoints.

## Reversed Or Superseded Decisions

- None.
