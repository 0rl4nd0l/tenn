# Handoff Skill

## Implemented

Added `.agents/skills/tenn-handoff/SKILL.md`.

The skill requires a Tenn report-local handoff that includes:

- session/thread/goal identity or `DATA_MISSING`
- branch, worktree, base, and dirty state
- completed work
- commits, PRs, issues, task cards, reports
- validation and failed attempts
- ledger status and duplicate-work classification
- next 10 milestones
- short fresh-session `/goal`
- do-not-touch boundaries
- evidence grades

## Host Boundary

The host-global skill `/home/l4nd0/.codex/skills/handoff/SKILL.md` was read but
not modified. Proposed host guidance is in `HOST_HANDOFF_PATCH.md`.

## Template

Added `docs/dev_flow/templates/HANDOFF.md` and covered its required sections in
`tests/test_agent_task_ledger.py`.
