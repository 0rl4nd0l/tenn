# Deprecation Plan

This is a plan only. Nothing was deleted or cleaned.

## Keep

- `diagnose`
- `code-reviewer`
- `improve-codebase-architecture`
- repo `AGENTS.md`
- repo `.agents/skills/tenn-goal-report`
- repo `.agents/skills/tenn-task-card-registry-safety`
- task-card/registry/hook scripts
- merge parking registry

## Merge Into New Workflow

- `tenn-auto-progress` into `/issue`
- `tenn-frame-design` into `/issue` and `/fix` long-run templates
- `tenn-git-hygiene` into `tenn-git-guard`
- host `tenn-issue-finder`, `tenn-issue-closeout`,
  `tenn-issue-resolution-reviewer` into `/issue`, `/fix`, and
  `/review-board`
- `handoff` into report-local `STATE.md`/`NEXT_GOAL.md`

## Rename Or Rehome

- Claude command docs remain Claude-specific references.
- Architecture cleanup should be Tenn-wrapped and not use stale `.cursor/rules`
  assumptions by default.

## Deprecate

- Direct generic `triage` for Tenn because labels and mutation behavior differ.
- Host `~/.codex/rules/default.rules` as a general Tenn rule source.

## Owner Boundary

- Host Codex config and hooks.
- Cockpit flag orchestrator.
- Financial Truth extraction skill.
- Worktree cleanup/pruning.
- Current dirty `.githooks/pre-push` and existing dirty report artifacts.

## Delete Candidates

No delete candidate is safe to name from this report-only audit alone. Deletion
requires a follow-up cleanup task with exact path hashes, ownership evidence,
and approval.
