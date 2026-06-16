---
name: tenn-explain
description: Tenn layman-depth explanation wrapper for issues, PRs, branches, reports, skills, hooks, subsystems, and architecture. Report-local by default, with optional EXPLAIN.md.
---

# Tenn Explain

Use `tenn-explain` when Orlando asks what something is, why it exists, what
changed, what is broken, or what to do next.

Default mutation mode is read-only or report-local. For branch or PR topics,
run `tenn-git-guard` before making current-state claims.
Do not present current branch, PR, report, or runtime status as verified unless
it was checked in the current run.

## Required Explanation Shape

Cover:

- what it is
- why it exists
- current state
- what changed
- what is broken
- risks
- what Orlando should do next

Use plain language, but keep the explanation deep enough to preserve operational
truth. Mark unavailable evidence as `DATA_MISSING`.
Label evidence as `VERIFIED`, `USER_REPORTED`, `INFERRED`, `UNKNOWN`, or
`CONFLICT` when explaining status.

## Durable Output

Write `EXPLAIN.md` only when the explanation is reusable, non-trivial, or needed
as handoff evidence. Do not mutate product/runtime/data/extraction files,
GitHub, registry state, host-global files, branches, or worktrees.
