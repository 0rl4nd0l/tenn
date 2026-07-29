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
2. Ticket 05 immutable financial-observation seam: active.
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

The original hash-pinned Ticket 05 was recovered and verified. It is explicitly
ready with no declared blocker. Canonical has extraction-run plus mutable
periodic-financial persistence but no immutable financial-observation model,
store, or profile read seam.

## Next action

Run one fresh Codex X implementer against the bounded Ticket 05 card, freeze the
delta, and send it to a separate fresh read-only Codex X reviewer.
