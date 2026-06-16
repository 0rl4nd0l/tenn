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
2. Ask at most one or two clarifying questions only when missing input would
   materially change the issue packet or safety boundary.
3. Run `tenn-git-guard` preflight.
4. Search existing issues, PRs, task cards, and reports read-only before
   proposing new tracker mutations.
5. Use the existing host `diagnose` skill only when the problem needs a repro,
   minimization, hypothesis, instrumentation, fix, or regression test loop.
6. Use `tenn-auto-progress` ideas as a candidate-ranking engine: rank by safety,
   urgency, owner value, available evidence, collision risk, and validation
   cost. Do not execute the ranked candidates in this skill.
7. Produce issue artifacts and a concrete next goal.

## Outputs

Write these under the run report directory:

- `ISSUE.md`
- `MILESTONES.md`
- context pack files or a compact context section
- `NEXT_GOAL.md`

For long or risky work, fold Frame Design into the issue packet by including
scope, non-negotiables, evidence sources, stop states, and success shape in
`ISSUE.md` and `MILESTONES.md`.

## Stop States

Use `WAITING_ON_USER` for GitHub writes, product/runtime/data/extraction
mutation, ambiguous ownership, missing credentials, merge/rebase/cleanup, or any
decision that would cross the current task-card boundary.

Use `DATA_MISSING` when current evidence cannot be safely obtained.
