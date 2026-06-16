---
name: tenn-worker
description: Tenn bounded worker contract for subagents used by tenn-fix. One worker, one lane, one worktree, one result file, no invisible dirt.
---

# Tenn Worker

Use `tenn-worker` only when an orchestrator assigns a bounded unit of work.

One worker gets one lane, one worktree, one brief, and one result file. Workers
must not share a mutation surface.
`WORKER_RESULT.md` is mandatory.

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
- parent task id
- Task Ledger expectations: child ledger entry or required ledger fields in
  `WORKER_RESULT.md`

## Required Behavior

1. Run `tenn-git-guard` in the assigned worktree.
2. Confirm the task card and allowed files before mutation.
3. Write a child ledger entry when the brief provides an approved ledger write
   path, or include ledger fields in `WORKER_RESULT.md` when ledger writes are
   unavailable.
4. Work only inside assigned scope.
5. Run focused validation if mutation occurred.
6. Leave no invisible dirt. Every changed, untracked, generated, ignored, or
   skipped file must be reported.
7. Stop instead of widening scope.

## Output

Write `WORKER_RESULT.md` with:

- branch
- worktree
- parent task id
- lane
- ledger status or `DATA_MISSING`
- task status
- files changed
- touched files
- tests or checks run
- result path
- risks
- blockers and `DATA_MISSING`
- recommended action

The orchestrator decides whether to integrate, park, or discard worker output.
The worker must not push, merge, rebase, delete, clean, or mutate GitHub unless
the brief explicitly allows that exact action.

If the worker cannot finish inside its lane, it must stop with blockers and
leave all dirt visible in `WORKER_RESULT.md`.
