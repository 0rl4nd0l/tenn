---
name: tenn-review-board
description: Tenn multi-perspective review wrapper for issues, PRs, branches, reports, plans, and risky decisions. Produces BOARD.md, BOARD_DECISION.json, and NEXT_GOAL.md with an actionable decision.
---

# Tenn Review Board

Use `tenn-review-board` before risky implementation, merge, parking, supersede,
or architecture decisions.

The board is not a discussion loop. It must end with one actionable decision.

## Preflight

Run `tenn-git-guard` first for branch, PR, diff, dirty-state, and registry
context. Keep GitHub reads read-only unless explicit owner approval exists.

## Required Perspectives

Run independent perspectives and preserve disagreements:

- architect
- skeptic/red-team
- product/value
- validation/test
- repo hygiene/git guard
- domain expert when the topic needs domain context

Each perspective must state evidence inspected, finding, uncertainty, risk, and
recommended action.

## Outputs

Write:

- `BOARD.md`
- `BOARD_DECISION.json`
- `NEXT_GOAL.md`

`BOARD_DECISION.json` must choose exactly one:

- `proceed`
- `revise_plan`
- `block`
- `ask_owner`
- `supersede`
- `park`

## Boundaries

Do not mutate code, data, GitHub, registry state, branches, or worktrees. Do not
turn a board into another report-only loop; the next goal must be executable,
blocked on a named owner decision, or parked with evidence.
