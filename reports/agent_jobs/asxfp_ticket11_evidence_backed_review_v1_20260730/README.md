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

The second bounded repair corrected the adapter to use the canonical
`issue["metric"]` association while preserving `issue["field"]` as the
provenance attribute. It also scopes real evaluation triggers: canonical
`metric:status` triggers affect only that metric, `context_mismatch:field`
triggers remain document-wide, and unknown shapes fail closed. Production
pipeline staging now enriches raw extraction output with the existing
provenance evaluation summary immediately before observation staging and
converts canonical provenance failures into the evaluation contract's
metric-specific abstain triggers.

## Changed paths

- `docs/agent_tasks/asxfp_ticket11_evidence_backed_review_v1_20260730.md`
- `financial-engine_v2/backend/app/alembic/versions/0015_financial_observation_reviews.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/models/__init__.py`
- `financial-engine_v2/backend/app/models/financial_observations.py`
- `financial-engine_v2/backend/app/services/extraction_eval.py`
- `financial-engine_v2/backend/app/services/financial_observations.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
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

Second bounded repair validation:

- Exact base commit `08420f349077158b8a537912d59e0f07d3b347bf`,
  tree `57b10a1addf6883faef5d14af4385ac95d8d62eb`, and authority
  SHA-256 matched.
- `python3 -m py_compile` for the three changed services and focused test:
  passed.
- Focused pytest was attempted but unavailable in the offline worktree:
  `/usr/bin/python3: No module named pytest`; no dependency installation was
  attempted.
- Focused AST, changed-line 100-column, and `git diff --check`: passed.
- Controller verification in a disposable dependency environment passed:
  `101 passed, 1 deselected, 1 warning`. The warning is the repository's
  existing unknown `asyncio_default_fixture_loop_scope` pytest option.
- Controller verification also normalized source-location evidence against
  the production payload shape: `source` supplies the table/region and the
  non-empty structured `source_cell` mapping is retained as `cell_ref`.

No runtime, database, migration, extraction, OCR, model, service, queue, GPU,
deployment, network, or protected-data action was performed.

## Controller finalization

- Candidate implementation commit:
  `9ba9e4df0125ab91dd22db6fd97cd512b93fb971`
- Candidate implementation tree:
  `617fc0a24928c7dce32916995b973ab0629950e2`
- Branch: `safe/asxfp-11-evidence-review-v1-20260730`
- Worktree: `/home/l4nd0/tenn-asxfp-11-evidence-review-v1-20260730`
- Git status after the candidate commit: clean.
- Exact-head review: pending this report-only identity follow-up.
- Push outcome: not attempted; pending exact-head acceptance.
- PR outcome: not attempted; pending exact-head acceptance.
- Merge outcome: not attempted and not authorized.

This report-only follow-up records the immutable candidate identity. Its own
commit changes no product, migration, API, or test behavior.

## Residual risks

- The migration was inspected and compiled but deliberately not applied.
- Only existing structured provenance-issue and trust-outcome payloads are
  adapted; malformed outcomes without metric context still fail closed.
- Production provenance enrichment can identify canonical provenance
  abstentions without gold expectations. Numeric wrong/missing and context
  quarantine outcomes still require an upstream evaluation result carrying
  the existing trust fields; the adapter does not guess those outcomes from
  raw values.
