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
3. Stop when the guard returns `OPEN_PR_WAIT` or `MERGED_USE_CANONICAL` unless
   Orlando explicitly overrides with continue, adopt, or supersede instructions.
   Stop on `OWNER_BOUNDARY` or `UNKNOWN_ASK` when the next meaningful step needs
   an owner decision.
4. Create or validate a task card before any mutation.
5. Confirm every intended path is inside the task-card `allowed_files`.
6. Write or update Task Ledger state when the workflow is implementation-capable:
   `claimed` at task acceptance, `implementation_started` before edits,
   `blocked` or `waiting_on_user` before stopping, `pr_opened` after PR
   creation, and `done`, `merged`, `parked`, or `superseded` at closeout as
   applicable. Use `waiting_on_timer` for timer waits and `owner_boundary` when
   ownership or approval blocks progress. Prefer
   `python3 scripts/agent_task_ledger.py append` only when live ledger mutation
   is allowed by the task card or owner approval. Otherwise write the intended
   entry under the report bundle and record why live append was skipped. If the
   ledger file is unavailable, record `DATA_MISSING` in the report and continue
   only after the guard's bounded fallback search is clean.
7. Do not implement from a headline metric, score, count, pass rate, daemon
   status, or evaluation result until denominator, filters, exclusions,
   freshness, and pipeline stage are understood. Use counter-lineage evidence
   when the number is surprising or challenged.
8. Default to the smallest safe diff first. If one readable line solves the
   task, change one line; remove unnecessary related lines only when safely in
   scope.
9. Use RED/GREEN validation where practical: capture a failing regression test
   or focused check before the fix, then rerun after the change.
10. Execute one bounded milestone per run.
11. Deploy bounded `tenn-worker` workers only when they reduce risk or context
   load. Each worker gets one lane, one worktree, one brief, and one result
   file.
12. Integrate one coherent change at a time.
13. Run focused validation proportional to blast radius.
14. Run `tenn-code-reviewer` before PR preparation.
15. Prepare, push, or open a PR only when the task and owner approval permit it.
16. When stopping before completion, run or follow `tenn-handoff` so the next
    session has git state, ledger state, validation, and a short next `/goal`.

## Outputs

Produce or update:

- `STATE.md`
- `DECISIONS.md`
- validation notes
- `NEXT_GOAL.md`

`STATE.md` or `DECISIONS.md` must record Task Ledger availability, current
ledger status, duplicate-work classification, ledger update result, and any
`DATA_MISSING` fallback searches.

Closeout must be one of: PR opened, local commit, failing regression test,
issue closed, owner decision, or blocked with exact reason. Do not complete with
a report-only artifact unless it directly unlocks one of those outcomes.

For long or risky runs, fold Frame Design into `STATE.md` and `DECISIONS.md`:
current state, evidence, non-negotiables, stop states, owner decisions, and next
safe action.

## Hard Stops

Stop on disallowed paths, overlapping dirty state, missing task card, failed
validation, missing owner approval for GitHub writes, product/runtime/data or
extraction boundary crossings, cleanup requests, or `DATA_MISSING` that would
make mutation unsafe.
