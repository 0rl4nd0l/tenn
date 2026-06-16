---
name: tenn-worker
description: Tenn bounded worker contract for subagents used by tenn-fix. One worker, one lane, one worktree, one result file, no invisible dirt.
---

# Tenn Worker

Use `tenn-worker` only when an orchestrator assigns a bounded unit of work.

One worker gets one lane, one worktree, one brief, and one result file. Workers
must not share a mutation surface.

## Required Contract

The worker brief must include:

- objective
- lane
- worktree path
- branch
- task card
- exact allowed files
- validation expected
- stop conditions
- result path for `WORKER_RESULT.md`

## Required Behavior

1. Run `tenn-git-guard` in the assigned worktree.
2. Confirm the task card and allowed files before mutation.
3. Work only inside assigned scope.
4. Run focused validation if mutation occurred.
5. Leave no invisible dirt. Every changed, untracked, generated, ignored, or
   skipped file must be reported.
6. Stop instead of widening scope.

## Output

Write `WORKER_RESULT.md` with:

- branch
- worktree
- files changed
- tests or checks run
- risks
- blockers and `DATA_MISSING`
- recommended action

The orchestrator decides whether to integrate, park, or discard worker output.
The worker must not push, merge, rebase, delete, clean, or mutate GitHub unless
the brief explicitly allows that exact action.
