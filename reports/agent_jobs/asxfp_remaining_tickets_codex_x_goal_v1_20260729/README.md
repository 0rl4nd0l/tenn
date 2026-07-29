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
- current bounded ticket: Ticket 06 ten-metric statutory observation projection

## Ordered backlog

1. Ticket 04 residual classifier failure class: draft PR 530.
2. Ticket 05 immutable financial-observation seam: repaired candidate accepted,
   published as draft PR 531, and exact-head CI passed.
3. Ticket 06 ten-metric statutory observation projection: task card prepared
   on the green Ticket 05 stacked head.
4. Tickets 07–15 in declared dependency order.
5. Ticket 16 locked release gate, Ticket 17 canary, and Ticket 18 bounded
   backfill only after prerequisites and explicit Tier 2 approvals.

## Approval boundaries

The active goal authorizes bounded Tier 1 code, documentation, tests, commits,
pushes, and draft PRs. It does not authorize source-PDF or protected-label
access, extraction, OCR/model execution, evaluation, runtime/services,
databases or migrations, queues, Qdrant, GPUs, production-data writes,
deployment, activation, merge, issue closure, canary execution, or backfill.

## Current milestone

Ticket 05 is independently accepted and exact-head green at
`84295111c6ae400de4e6f1c6cd941a45a0f549a3`. Ticket 06 now expands that seam to
exactly the ten existing canonical statutory metrics while preserving sparse
legacy profile values; database-backed proof remains unauthorized.

## Next action

Validate and seed Ticket 06, launch one fresh Codex X implementer, freeze the
candidate, and send the exact delta to a different fresh Codex X reviewer.
