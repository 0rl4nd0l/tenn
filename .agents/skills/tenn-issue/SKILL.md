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
   or `CONFLICT`. Stop or narrow on unresolved conflicts.
3. Ask at most one to three high-value clarifying questions only when missing
   input would materially change the issue packet or safety boundary; otherwise
   proceed with stated assumptions.
4. Run `tenn-git-guard` preflight.
5. Search existing issues, PRs, task cards, branches, worktrees, and reports
   read-only before reimplementing or
   proposing new tracker mutations.
6. Use the existing host `diagnose` skill only when the problem needs a repro,
   minimization, hypothesis, instrumentation, fix, or regression test loop.
7. Use `tenn-auto-progress` ideas as a candidate-ranking engine only: rank by safety,
   urgency, owner value, available evidence, collision risk, and validation
   cost. Do not execute the ranked candidates in this skill.
8. For medium/high-risk issues, produce two plausible implementation plans,
   compare tradeoffs, then select one.
9. Produce issue artifacts and an exact next goal.

## Outputs

Write these under the run report directory:

- `ISSUE.md`
- `MILESTONES.md`
- context pack files or a compact context section
- `NEXT_GOAL.md`

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
