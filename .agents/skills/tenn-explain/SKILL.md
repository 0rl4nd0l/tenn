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
For daemon, runtime, extraction, ingestion, automation, collector, scheduler,
service, or pipeline status, separate activity evidence from functionality
evidence. Services, timers, logs, tests, reports, artifacts, and merged PRs are
activity evidence only. Functionality evidence requires the intended live output
proof fields from `AGENTS.md`; if missing, say `PARTIAL`, `BROKEN`, or
`DATA_MISSING`, not done.
For branch, PR, report, task-card, or "has this already been done?" questions,
include Task Ledger evidence when available. If the live or committed ledger is
unavailable, say `DATA_MISSING` and summarize the bounded fallback search used
before explaining current state.
When explaining dirt or stale work, cite the relevant ledger entry, task id,
branch, source session reference, and session/thread ID when available. If the
session or thread reference is `DATA_MISSING`, say so directly.

## Required Explanation Shape

Cover:

- what it is
- why it exists
- current state
- activity evidence versus functionality evidence when runtime-like status is
  involved
- ledger and duplicate-work status when relevant
- what changed
- what is broken
- risks
- what Orlando should do next

Use plain language, but keep the explanation deep enough to preserve operational
truth. Mark unavailable evidence as `DATA_MISSING`.
Label evidence as `VERIFIED`, `USER_REPORTED`, `INFERRED`, `UNKNOWN`,
`CONFLICT`, or `DATA_MISSING` when explaining status.

## Counter Lineage Mode

Use this mode when Orlando asks about surprising metrics, counts, scores, pass
rates, daemon status, evaluation results, or challenges a number with phrases
like "why only", "shouldn't this be higher", "is the daemon doing it", or "that
doesn't make sense".

Required shape:

- headline answer
- what the number counts
- what it does not count
- raw/captured count
- candidate count
- accepted count
- evaluated count
- filters
- exclusions
- source artifacts
- freshness
- what changes the number
- next operational action

Trace the counter lineage as raw/captured -> candidate -> accepted -> evaluated
-> reported. If any stage cannot be verified in the current run, mark it
`DATA_MISSING` instead of filling a plausible number.

When functionality is claimed, add the `Runtime Functionality Proof` table from
`AGENTS.md` and explicitly state whether the intended live output is
`WORKING`, `PARTIAL`, `BROKEN`, or `DATA_MISSING`.

## Durable Output

Write `EXPLAIN.md` or `COUNTER_LINEAGE.md` only when the explanation is
reusable, non-trivial, or needed as handoff evidence. Do not mutate
product/runtime/data/extraction files, GitHub, registry state, host-global
files, branches, or worktrees.
