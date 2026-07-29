# ASXFP Ticket 11 closeout

## Outcome

Implemented an additive evidence-backed financial observation review queue.
Existing provenance-issue conflict/ambiguity shapes and trust-outcome
abstention/quarantine shapes now feed the queue directly; the invented
`observation_reviews` input remains supported for compatibility. Candidates
missing location evidence are retained with machine-readable
`missing_evidence_*` reasons. Pending items expose source document, page,
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

- Repair base commit `6bed5f6fa9df04e3f94fc73152d66cef54184ed8`,
  tree `f267179ee3a9c68df83d3af8d38301f4705ff30d`, and authority-file
  SHA-256: matched.
- `python3 -m py_compile` on the changed service and focused test: passed
  (exit 0).
- Changed-file AST and 100-column static scan: passed (exit 0).
- `git diff --check`: passed (exit 0).
- Focused pytest in a disposable dependency environment: passed,
  `83 passed, 1 warning`.

No runtime, database, migration, extraction, OCR, model, service, queue, GPU,
deployment, network, or protected-data action was performed.

## Controller finalization (required; not yet known)

- Delivery commit: `CONTROLLER_MUST_FILL_AFTER_LOCAL_COMMIT`
- Delivery tree: `CONTROLLER_MUST_FILL_AFTER_LOCAL_COMMIT`
- Branch: `codex-x/20260729T202843Z-6bed5f6fa9-b21b74`
- Worktree:
  `/home/l4nd0/codex-x-launcher-successor-v1-20260725/.state/runs/20260729T202843Z-6bed5f6fa9-b21b74/workspace/source`
- Final Git status: `CONTROLLER_MUST_FILL_AFTER_LOCAL_COMMIT`
- Push outcome: `NOT_ATTEMPTED_AND_PROHIBITED`
- PR outcome: `NOT_ATTEMPTED_AND_PROHIBITED`
- Merge outcome: `NOT_ATTEMPTED_AND_PROHIBITED`

The controller must replace every `CONTROLLER_MUST_FILL_AFTER_LOCAL_COMMIT`
placeholder from the post-commit repository state before accepting closeout.
The repair worker must not fabricate these future values.

## Residual risks

- The migration was inspected and compiled but deliberately not applied.
- Only existing structured provenance-issue and trust-outcome payloads are
  adapted; malformed outcomes without metric context still fail closed.
