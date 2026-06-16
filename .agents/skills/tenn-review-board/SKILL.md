---
name: tenn-review-board
description: Tenn multi-perspective review wrapper for issues, PRs, branches, reports, plans, and risky decisions. Produces BOARD.md, BOARD_DECISION.json, and NEXT_GOAL.md with an actionable decision.
---

# Tenn Review Board

Use `tenn-review-board` before risky implementation, merge, parking, supersede,
or architecture decisions.

The board is not a discussion loop. It must end with one actionable decision.
Do not run a board for trivial edits.

## Preflight

Run `tenn-git-guard` first for branch, PR, diff, dirty-state, and registry
context. Keep GitHub reads read-only unless explicit owner approval exists.
Review the guard's Task Ledger evidence and duplicate-work classification before
recommending action.

The board must not recommend new implementation when an open PR or merged
canonical implementation already solves the request. In those cases, choose
`park`, `supersede`, `ask_owner`, or a review/merge-oriented next goal instead
of `proceed`.

## Required Perspectives

Run independent perspectives and preserve disagreements:

- architect
- skeptic/red-team
- product/value
- validation/test
- repo hygiene/git guard
- domain expert when the topic needs domain context
- chair

Each perspective must state evidence inspected, finding, uncertainty, risk, and
recommended action.

The board must actively search for credible objections. `BOARD_DECISION.json`
must include a `minority_objection` field: record the objection clearly when one
exists, or set it to `none_found` and explain the checks performed when none is
credible. Never invent dissent just to satisfy the template. Truthfulness beats
forced role-play.

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

The safe default is `ask_owner`, not `proceed`. The chair owns the final
decision and must convert opinions into `BOARD_DECISION.json`.
`BOARD_DECISION.json` must include ledger fields: `ledger_sources_checked`,
`duplicate_work_classification`, `matching_candidates`, and
`duplicate_work_decision`.

## Boundaries

Do not mutate code, data, GitHub, registry state, branches, or worktrees. Do not
turn a board into another report-only loop; the next goal must be executable,
blocked on a named owner decision, or parked with evidence.
