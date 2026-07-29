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
- first bounded ticket: Ticket 04 cross-page half-year bundle follow-up

## Ordered backlog

1. Ticket 04 residual classifier failure class.
2. Ticket 05 immutable financial-observation seam.
3. Tickets 06 and 07 after Ticket 05.
4. Tickets 08–15 according to their declared dependencies.
5. Ticket 16 locked release gate, then Ticket 17 canary and Ticket 18 bounded
   backfill, only after their prerequisites and explicit Tier 2 approvals.

## Current evidence

- Tickets 01–03 are integrated code/custody prerequisites.
- Ticket 04 implementation merged through PR 529.
- A bounded local 12-document diagnostic improved classification but exposed a
  remaining cross-page half-year bundle class.
- The protected Ticket 03 holdout stays on the trusted local machine and is not
  publishable.

## Approval boundaries

The active goal authorizes bounded Tier 1 code, documentation, tests, commits,
pushes, and draft PRs. It does not authorize source-PDF or protected-label
access, extraction, OCR/model execution, evaluation, runtime/services,
databases, queues, Qdrant, GPUs, production-data writes, deployment,
activation, merge, issue closure, canary execution, or backfill execution.

## Current milestone

Ticket 04 is classified `NEW_FAILURE_CLASS`. The permanent gate is a synthetic
cross-page half-year bundle regression. The first Codex X implementer may edit
only the current task-card allowlist; a fresh independent reviewer must accept
the frozen delta before parent-owned publication.

## Validation

Validation evidence will include task-card validation, exact changed paths,
RED/GREEN focused tests, focused existing tests, changed-file lint/compile,
`git diff --check`, and independent reviewer verdict.

## Next action

Publish the orchestration seed, launch the fresh offline Codex X implementer
from its exact remote SHA, and freeze the resulting Ticket 04 delta.
