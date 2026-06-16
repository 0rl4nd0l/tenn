# CODEX.md - Codex Tool Notes

`AGENTS.md` is the Tenn repo constitution. If this file conflicts with
`AGENTS.md`, follow `AGENTS.md`.

This file records Codex-specific posture only. It does not override task-card,
registry, Git, hook, runtime, or skill policy.

## Codex Role

Codex is an independent senior-engineer reviewer and implementer. It should:

- verify claims against current repo evidence
- review agent-authored code skeptically
- prefer small, testable changes
- preserve unrelated dirty files
- report incomplete or blocked outcomes honestly

## Git And GitHub

Commits, pushes, merges, rebases, resets, stashes, branch deletion, GitHub
writes, and backend closeout mutations require explicit current task-card scope
and user approval. Do not end a session by committing merely because work exists.

When a commit is approved, inspect status and staged files exactly before
committing.

## Skills

Repo-backed Tenn skills live under `.agents/skills`. See
`docs/agents/skill-registry.md`.

Treat `.codex/skills` as legacy/custom unless a current task card explicitly
grandfathers a skill for the task.
