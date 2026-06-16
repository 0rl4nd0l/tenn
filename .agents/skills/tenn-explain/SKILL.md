---
name: tenn-explain
description: Tenn layman-depth explanation wrapper for issues, PRs, branches, reports, skills, hooks, subsystems, and architecture. Report-local by default, with optional EXPLAIN.md.
---

# Tenn Explain

Use `tenn-explain` when Orlando asks what something is, why it exists, what
changed, what is broken, or what to do next.

Default mutation mode is read-only or report-local. For branch or PR topics,
run `tenn-git-guard` before making current-state claims.

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

## Durable Output

Write `EXPLAIN.md` when the topic is non-trivial, likely to be reused, or needed
as handoff evidence. Do not mutate product/runtime/data/extraction files, GitHub,
registry state, host-global files, branches, or worktrees.
