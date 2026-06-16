---
name: tenn-fix
description: Tenn bounded implementation orchestrator. Reads issue or board artifacts, runs Git guard, validates task-card scope, deploys workers only when useful, integrates one coherent change, validates, reviews, and prepares PRs only when allowed.
---

# Tenn Fix

Use `tenn-fix` when Orlando asks for implementation after an issue packet,
board decision, task card, or explicit fix request.

`tenn-fix` is an orchestrator. It owns scope, validation, review, and closeout.

## Workflow

1. Read `ISSUE.md`, `BOARD_DECISION.json`, task card, or the current user fix
   request.
2. Run `tenn-git-guard` preflight.
3. Create or validate a task card before any mutation.
4. Confirm every intended path is inside the task-card `allowed_files`.
5. Deploy bounded `tenn-worker` workers only when they reduce risk or context
   load. Each worker gets one lane, one worktree, one brief, and one result
   file.
6. Integrate one coherent change at a time.
7. Run focused validation proportional to blast radius.
8. Run `tenn-code-reviewer` before PR preparation.
9. Prepare, push, or open a PR only when the task and owner approval permit it.

## Outputs

Produce or update:

- `STATE.md`
- `DECISIONS.md`
- validation notes
- `NEXT_GOAL.md`

For long or risky runs, fold Frame Design into `STATE.md` and `DECISIONS.md`:
current state, evidence, non-negotiables, stop states, owner decisions, and next
safe action.

## Hard Stops

Stop on disallowed paths, overlapping dirty state, missing task card, failed
validation, missing owner approval for GitHub writes, product/runtime/data or
extraction boundary crossings, cleanup requests, or `DATA_MISSING` that would
make mutation unsafe.
