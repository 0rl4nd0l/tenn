---
name: tenn-issue
description: Tenn wrapper for turning vague owner problems into executable issue packets. Runs Git guard, uses diagnose only when debugging or repro is needed, ranks candidates with auto-progress ideas, and writes report-local planning artifacts by default.
---

# Tenn Issue

Use `tenn-issue` when Orlando gives a vague problem, broken behavior, candidate
workstream, or "what should we do next?" prompt.

Default mutation mode is report-local only. Do not create, edit, comment on, or
close GitHub issues unless explicitly approved.

## Workflow

1. Restate the owner problem without shrinking it into an easier slice.
2. Label issue evidence as `VERIFIED`, `USER_REPORTED`, `INFERRED`, `UNKNOWN`,
   `CONFLICT`, or `DATA_MISSING`. Stop or narrow on unresolved conflicts.
3. Ask at most one to three high-value clarifying questions only when missing
   input would materially change the issue packet or safety boundary; otherwise
   proceed with stated assumptions.
4. Run `tenn-git-guard` preflight.
5. Use the guard's Task Ledger search before framing new work. Prefer
   `python3 scripts/agent_task_ledger.py search` by task id, issue id, PR id,
   branch, worktree, touched paths, and text. Include live ledger, committed
   ledger, task cards, reports, branches, worktrees, PRs, issues, and likely
   touched files when available.
6. Search existing issues, PRs, task cards, branches, worktrees, and reports
   read-only before reimplementing or proposing new tracker mutations.
7. If similar work exists, include it in `ISSUE.md` with the duplicate-work
   classification and decide whether the next action is continue, adopt,
   supersede, preserve, or ask Orlando. Do not frame a duplicate new issue as
   fresh work.
8. If owner confusion is about a metric, count, pass rate, daemon status,
   evaluation result, or surprising low/high number, run counter-lineage mode
   before opening a broad issue. Trace raw/captured -> candidate -> accepted ->
   evaluated -> reported, including denominator, filters, exclusions,
   freshness, and source artifacts.
9. Use the existing host `diagnose` skill only when the problem needs a repro,
   minimization, hypothesis, instrumentation, fix, or regression test loop.
10. Use `tenn-auto-progress` ideas as a candidate-ranking engine only: rank by safety,
   urgency, owner value, available evidence, collision risk, and validation
   cost. Do not execute the ranked candidates in this skill.
11. For medium/high-risk issues, produce two plausible implementation plans,
   compare tradeoffs, then select one.
12. Produce issue artifacts and an exact next goal.

## Outputs

Write these under the run report directory:

- `ISSUE.md`
- `MILESTONES.md`
- context pack files or a compact context section
- `NEXT_GOAL.md`

`ISSUE.md` must include a Task Ledger section with ledger availability,
duplicate-work classification, matching candidates, and the selected action:
continue, adopt, supersede, preserve, ask owner, or proceed as new work.
When prior work has session/thread/source references, include them. If the
reference is `DATA_MISSING`, say so instead of implying traceability exists.

`NEXT_GOAL.md` must contain a directly executable next prompt or a precise
`WAITING_ON_USER` approval request. Do not end with another report-only loop
unless that report directly enables implementation, closeout, cleanup approval,
PR/merge, or owner decision.

For long or risky work, fold Frame Design into the issue packet by including
scope, non-negotiables, evidence sources, stop states, and success shape in
`ISSUE.md` and `MILESTONES.md`.

## Stop States

Use `WAITING_ON_USER` for GitHub writes, product/runtime/data/extraction
mutation, ambiguous ownership, missing credentials, merge/rebase/cleanup, or any
decision that would cross the current task-card boundary.

Use `DATA_MISSING` when current evidence cannot be safely obtained.
