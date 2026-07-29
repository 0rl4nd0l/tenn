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
- current bounded ticket: Ticket 08 Appendix 4C quarterly cash profile

## Ordered backlog

1. Ticket 04 residual classifier failure class: draft PR 530.
2. Ticket 05 immutable financial-observation seam: repaired candidate accepted,
   published as draft PR 531, and exact-head CI passed.
3. Ticket 06 ten-metric statutory observation projection: independently
   accepted, published as draft PR 532, and exact-head CI passed.
4. Ticket 07 quarter-only and year-to-date observations: present in the exact
   Ticket 08 base.
5. Ticket 08 Appendix 4C quarterly cash profile: bounded local implementation
   and validation complete, pending any separately requested review/transition.
6. Tickets 09–15 in declared dependency order.
7. Ticket 16 locked release gate, Ticket 17 canary, and Ticket 18 bounded
   backfill only after prerequisites and explicit Tier 2 approvals.

## Approval boundaries

The active goal authorizes bounded Tier 1 code, documentation, tests, commits,
pushes, and draft PRs. It does not authorize source-PDF or protected-label
access, extraction, OCR/model execution, evaluation, runtime/services,
databases or migrations, queues, Qdrant, GPUs, production-data writes,
deployment, activation, merge, issue closure, canary execution, or backfill.

## Current milestone

Ticket 08 builds a focused evidence-gated Appendix 4C cash profile on exact
commit `dc4e99e305218dfea072e9c78cb13476dc6899fe`, preserving Ticket 07's
source-bound, collision-free `period_only` and `year_to_date` observations.

## Next action

Restore launcher Git-wrapper audit writability, commit only the seven
allowlisted Ticket 08 files, then use that frozen commit/tree for any
separately requested review or next owner-directed transition.
