# ASXFP remaining tickets Codex X goal

Status: RUNNING

## Goal

Use Codex X to complete the remaining ASX Financial Profile Extraction tickets
from current canonical truth, one bounded implementation and independent review
at a time.

## Canonical identity

- repository: `0rl4nd0l/tenn`
- canonical branch:
  `migration/clean-runtime-baseline-reconstruct-v1`
- starting canonical commit:
  `b01885d6cd55242339662e91d18141aeb725f089`
- current bounded ticket: Ticket 07 quarter-only and year-to-date observations

## Ordered backlog

1. Ticket 04 residual classifier failure class: draft PR 530.
2. Ticket 05 immutable financial-observation seam: repaired candidate accepted,
   published as draft PR 531, and exact-head CI passed.
3. Ticket 06 ten-metric statutory observation projection: independently
   accepted, published as draft PR 532, and exact-head CI passed.
4. Ticket 07 quarter-only and year-to-date observations: task card prepared on
   the green Ticket 06 stacked head.
5. Tickets 08–15 in declared dependency order.
6. Ticket 16 locked release gate, Ticket 17 canary, and Ticket 18 bounded
   backfill only after prerequisites and explicit Tier 2 approvals.

## Approval boundaries

The active goal authorizes bounded Tier 1 code, documentation, tests, commits,
pushes, and draft PRs. It does not authorize source-PDF or protected-label
access, extraction, OCR/model execution, evaluation, runtime/services,
databases or migrations, queues, Qdrant, GPUs, production-data writes,
deployment, activation, merge, issue closure, canary execution, or backfill.

## Current milestone

Ticket 06 is independently accepted and exact-head green at
`f063c2a4cb4b9c677f35498de4b80f31dba55ba6`. Ticket 07 now makes
`period_only` and `year_to_date` first-class, source-bound, collision-free
observation contexts while preserving every legacy profile row.

## Next action

Validate and seed Ticket 07, launch one fresh Codex X implementer, freeze the
candidate, and send the exact delta to a different fresh Codex X reviewer.
