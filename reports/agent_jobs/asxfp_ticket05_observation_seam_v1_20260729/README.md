# ASXFP Ticket 05 immutable observation seam

Status: ACCEPTED — DRAFT PR 531 PUBLISHED — CI PENDING

- canonical_base: `b01885d6cd55242339662e91d18141aeb725f089`
- authoritative_ticket_sha256:
  `27f03834bba372c3c3f470cf1a1fa7f90b7a586b7015e6b453a77599920aac78`
- implementation_seed: `f2fd19bc9ac7948e7cab941796b7d0ae9dc18d84`
- rejected_candidate: `15eabc815a918fbc882d6e839a05f81d63545152`
- rejected_tree: `7af688369aa56cc04678c91b8c7b46a77f098ea6`
- repaired_candidate: `af320c097728cdfcb7ddf93452c5d4b576997408`
- accepted_product_tree: `214630a1db822bb0014c0c0478f7b27c354a7c59`
- combined_diff_sha256:
  `1116113b7b3a4f46c8a13b0706b4650fe4259c8ab8568c8cf9a48d23c9ad91ed`
- product_commit: `c30e5ccf0ffefd5a33856d9b736301bd2dbab612`
- draft_pr: `https://github.com/0rl4nd0l/tenn/pull/531`
- rejected_review: session `019fae0c-ffce-7c11-ba66-74f14c6c2fe1`
- repair_implementer: session `019fae12-cd0e-7e52-b544-69b46180cc00`
- accepted_review: session `019fae1d-a559-7db3-aba7-955ba15cfb5e`,
  verdict `ACCEPT`
- protected_corpus_access: prohibited
- database_execution: not authorized
- merge: not authorized

## Objective

Promote one existing statutory metric, `revenue`, through an immutable,
idempotent observation seam and deterministic compatibility read without
executing a database or touching protected corpus artifacts.

## Codex X evidence

- Repair RED adds focused fake-only coverage for reachable production evidence,
  closed vocabularies, low-confidence/highlights/adjusted abstention,
  conflict-safe SQL, preserved source scale, and compatibility context
  matching.
- The isolated implementer could not execute dependency-backed tests because
  pytest and SQLAlchemy were unavailable there. The parent subsequently ran
  them in disposable `uv` environments without changing project dependencies.
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

## Independent review

The first candidate was rejected on production reachability, open vocabularies,
and concurrency-unsafe idempotence. A different fresh Codex X reviewer inspected
the repaired exact commit, tree, and combined diff and returned `ACCEPT` with
no blockers. Remaining nonblocking risks are deliberately strict abstention,
weak SQL fakes, duplicated vocabulary declarations, no database-backed
PostgreSQL conflict proof, and no independent recomputation of normalized value
from the preserved raw source cell.

## Parent validation

- `tests/test_financial_observations.py`: 7 passed.
- Existing pipeline/model focused command: 27 passed.
- `tests/test_models_import_contract.py`: 3 passed.
- `tests/test_process_document_api.py`: 2 tests collected successfully on
  Python 3.11; endpoint execution was skipped because the route writes
  extraction-run status.
- Ruff lint for all changed Python: passed.
- Python compile with an external bytecode cache: passed.
- Migration AST/identity/upgrade/downgrade structure inspection: passed;
  migration execution remained prohibited.
- Task validation, task scope, `git diff --check`, and staged binary check:
  passed.
- Non-gating Ruff format probe reports five files would be reformatted,
  including pre-existing formatting in modified files.

No PDF, protected corpus artifact, extraction, OCR, model, evaluation,
database, migration execution, runtime, service, queue, Qdrant, GPU,
deployment, activation, canary, backfill, production write, or merge occurred.
