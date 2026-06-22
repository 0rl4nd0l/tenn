---
name: tenn-explain
description: Tenn layman-depth explanation wrapper for issues, PRs, branches, reports, skills, hooks, subsystems, architecture, and zoom-out checks. Report-local by default, with optional EXPLAIN.md.
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

## Zoom-Out / Contrarian Mode

Use this mode when Orlando asks to zoom out, stress-test whether the current
lane is solving the real problem, or when a workflow appears trapped in narrow
fixes or reports.

Answer explicitly:

- Are we solving the real root problem?
- Are we overfitting to one file, document, bug, screenshot, or artifact?
- Are we trapped in report-only loops?
- Are we making broad system progress?
- Would a failure-class, document-class, route-class, or workflow-class approach
  be better than another narrow fix?
- What is the best next action by production-readiness value?

For financial extraction work, push the explanation toward failure classes,
document classes, breadth, provenance, confidence, and regression coverage
rather than one-off PDF fixes. Mark runtime, corpus, or canonical-number claims
as `DATA_MISSING` unless verified in the current run.

## Durable Output

Write `EXPLAIN.md`, `COUNTER_LINEAGE.md`, or a zoom-out section only when the
explanation is reusable, non-trivial, or needed as handoff evidence. Do not
mutate product/runtime/data/extraction files, GitHub, registry state,
host-global files, branches, or worktrees.
