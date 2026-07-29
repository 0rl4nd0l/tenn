# ASXFP Ticket 11 closeout

## Outcome

Implemented an additive evidence-backed financial observation review queue.
Conflicting, ambiguous, abstained, and quarantined candidates are retained with
machine-readable reasons. Pending items expose source document, page,
table/region, row, cell, period, currency, and scale context.

Trusted observations continue through the existing accepted-observation path
without review. Approval creates an accepted observation only when both a
proposed numeric value and complete source-location evidence remain attached;
the resulting provenance records the review identity and reason codes.

## Changed paths

- `docs/agent_tasks/asxfp_ticket11_evidence_backed_review_v1_20260730.md`
- `financial-engine_v2/backend/app/alembic/versions/0015_financial_observation_reviews.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/models/__init__.py`
- `financial-engine_v2/backend/app/models/financial_observations.py`
- `financial-engine_v2/backend/app/services/financial_observations.py`
- `financial-engine_v2/backend/tests/test_financial_observation_reviews.py`
- `financial-engine_v2/backend/tests/test_financial_observations.py`
- `reports/agent_jobs/asxfp_ticket11_evidence_backed_review_v1_20260730/README.md`

## Validation

- Exact base commit, tree, and authority-file SHA-256: matched.
- `python3 -m py_compile` on all changed Python modules/tests: passed (exit 0).
- Focused pytest in a disposable dependency environment: passed,
  `78 passed, 1 warning`.
- Changed-file 100-column static scan: passed (exit 0).
- `git diff --check`: passed (exit 0).

No runtime, database, migration, extraction, OCR, model, service, queue, GPU,
deployment, network, or protected-data action was performed.

## Residual risks

- The migration was inspected and compiled but deliberately not applied.
- Producers must emit the additive `observation_reviews` candidate contract;
  this ticket does not alter extraction or model execution.
