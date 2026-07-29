# ASXFP Ticket 05 immutable observation seam

Status: REPAIRED AFTER REJECT — REVIEW PENDING

- canonical_base: `b01885d6cd55242339662e91d18141aeb725f089`
- authoritative_ticket_sha256:
  `27f03834bba372c3c3f470cf1a1fa7f90b7a586b7015e6b453a77599920aac78`
- implementation: candidate delta prepared from launcher-pinned
  `f2fd19bc9ac7948e7cab941796b7d0ae9dc18d84`
- rejected_candidate: `15eabc815a918fbc882d6e839a05f81d63545152`
- rejected_tree: `7af688369aa56cc04678c91b8c7b46a77f098ea6`
- independent_review: session `019fae0c-ffce-7c11-ba66-74f14c6c2fe1`
  rejected the candidate with three blockers; repaired review is pending
- protected_corpus_access: prohibited
- database_execution: not authorized
- merge: not authorized

## Objective

Promote one existing statutory metric, `revenue`, through an immutable,
idempotent observation seam and deterministic compatibility read without
executing a database or touching protected corpus artifacts.

## Implementer evidence

- Repair RED adds focused fake-only coverage for reachable production evidence,
  closed vocabularies, low-confidence/highlights/adjusted abstention,
  conflict-safe SQL, preserved source scale, and compatibility context
  matching.
- Focused test runner unavailable:
  `python3 -m pytest -q tests/test_financial_observations.py` exited `1`
  because pytest is not installed.
- Application import validation is also unavailable because SQLAlchemy is not
  installed in the execution environment.
- No database, migration, runtime, protected corpus, PDF, extraction, model,
  evaluation, service, queue, Qdrant, GPU, deployment, activation, canary, or
  backfill action was run.
- Static validation and the frozen binary-diff hash are recorded at closeout.

## Repair

- Production `ok` payloads can reach persistence only with direct
  income-statement revenue evidence, explicit source-text period basis/end,
  explicit native currency, and source-cell scale provenance.
- Arbitrary period, currency, source-scale, accounting-basis, scale, metric,
  and trust values fail closed in service and database constraints.
- Persistence uses PostgreSQL `ON CONFLICT DO NOTHING` and leaves commit,
  rollback, and transaction ownership to the workflow.
- Compatibility reads require the observation currency and absolute-unit scale
  to match the legacy row context before overlay.
