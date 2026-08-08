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
- current bounded ticket: Ticket 05 immutable financial-observation seam

## Ordered backlog

1. Ticket 04 residual classifier failure class: draft PR 530.
2. Ticket 05 immutable financial-observation seam: repaired candidate accepted
   and published as draft PR 531; exact-head CI pending.
3. Tickets 06–15 in declared dependency order.
4. Ticket 16 locked release gate, Ticket 17 canary, and Ticket 18 bounded
   backfill only after prerequisites and explicit Tier 2 approvals.

## Approval boundaries

The active goal authorizes bounded Tier 1 code, documentation, tests, commits,
pushes, and draft PRs. It does not authorize source-PDF or protected-label
access, extraction, OCR/model execution, evaluation, runtime/services,
databases or migrations, queues, Qdrant, GPUs, production-data writes,
deployment, activation, merge, issue closure, canary execution, or backfill.

## Current milestone

The hash-pinned Ticket 05 implementation adds the narrow immutable `revenue`
observation seam while preserving the mutable periodic-financial compatibility
projection. A fresh Codex X reviewer accepted exact product tree
`214630a1db822bb0014c0c0478f7b27c354a7c59`; database-backed proof remains
unauthorized.

## Next action

Wait for exact-head draft-PR checks, then prepare Ticket 06 from the accepted
Ticket 05 dependency without merging or executing Tier 2 work.
