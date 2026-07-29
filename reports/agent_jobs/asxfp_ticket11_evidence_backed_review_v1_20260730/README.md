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

The fresh rejection repair applies that enrichment to each mapping in the
actual `period_observations` collection at the same staging seam. Explicit
abstain/quarantine outcomes with valid metric or context scopes now enter
review even without `field_provenance`; their absent location fields are
retained as `missing_evidence_*` reasons. Unknown metrics, malformed members,
and unscoped trigger shapes remain ignored fail-closed.

This exact-head repair completes the decision lifecycle. Every approval and
rejection now requires and persists a non-empty decision actor plus non-empty
unique machine-readable decision reason codes, with an automatic UTC decision
timestamp. The optional note is supplemental only. Approval-created
observation provenance records the decision audit as a distinct nested object
without replacing the candidate review ID or candidate reason codes.
Rejection remains non-promoting. The review read and decision endpoints are
now listed in both canonical API inventory entry points.

The still-unapplied migration stores decision reason codes as PostgreSQL JSONB.
Its constraint enforces lifecycle consistency and a non-empty array containing
only non-blank strings. Normalization and uniqueness are service invariants,
validated before persistence; database-enforced element uniqueness is not
claimed.

## Changed paths

- `docs/agent_tasks/asxfp_ticket11_evidence_backed_review_v1_20260730.md`
- `docs/architecture/19_backend_api_surface.md`
- `financial-engine_v2/README.md`
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

Exact-head lifecycle repair validation:

- Exact base commit `33327e0a44833d270b6a02324abc1815d27f3adb`
  and authority SHA-256
  `e28516984ca7b020f028385908c383b1e3fcb2b41617e30f7561bff34bdebea8`
  matched.
- `python3 -m py_compile` for the migration, model, API route, service, and
  focused review test passed.
- Focused pytest was attempted but unavailable in the offline worktree:
  `/usr/bin/python3: No module named pytest`; no dependency installation was
  attempted.
- Controller verification in a disposable dependency environment passed:
  `107 passed, 1 deselected, 1 warning`. The warning is the repository's
  existing unknown `asyncio_default_fixture_loop_scope` pytest option.
- Controller Ruff, `py_compile`, task-card validation, allowlist diff check,
  and `git diff --check` all passed.

Fresh exact-head rejection-repair validation:

- Exact base commit `c958a7e77da1b782d58edb5c3531ab93a45e0fcd`,
  tree `90e078fe3cc94351ae9e7a84f7656c655193eb1c`, parent Ticket 10
  `c57698a2e852d74d84dbb30402a0d654515d6a44`, and authority SHA-256
  `e28516984ca7b020f028385908c383b1e3fcb2b41617e30f7561bff34bdebea8`
  matched.
- Focused fake-only pytest was attempted with
  `python3 -m pytest -q
  financial-engine_v2/backend/tests/test_financial_observation_reviews.py -k
  'without_provenance or nested_period_observations'`; the offline interpreter
  reported `No module named pytest`. No installation was attempted.
- `python3 -m py_compile` for the migration, model, service, and focused test:
  passed.
- Changed-Python AST compilation, exact task-card allowlist comparison, and
  `git diff --check`: passed.
- Ruff was attempted but unavailable in the offline interpreter:
  `/usr/bin/python3: No module named ruff`.
- The Git index remained empty; the seven repair paths are unstaged.
- Controller verification in the disposable dependency environment passed:
  `112 passed, 1 deselected, 1 warning`. The warning is the repository's
  existing unknown `asyncio_default_fixture_loop_scope` pytest option.
- Controller Ruff check passed after four allowlisted import-only
  modernizations, with the file's two pre-existing `FURB157` Decimal-style
  findings excluded. `ruff format --check` reports broader pre-existing
  formatting drift across these legacy files, so no broad mechanical rewrite
  was applied.
- Controller `py_compile`, task-card validation, exact allowlist diff check,
  and `git diff --check` passed.

No runtime, database, migration, extraction, OCR, model, service, queue, GPU,
deployment, network, or protected-data action was performed.

## Controller finalization

- Candidate implementation commit:
  `f59074fc0d45630de298d54f4e75a5ec5827ecb0`
- Candidate implementation tree:
  `713fb7578019909ffaf01131751ad30a59b7b197`
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
- The migration's PostgreSQL decision-audit constraint was not exercised
  against a live database, as prohibited by this repair boundary.
- PostgreSQL does not enforce uniqueness between JSONB array elements;
  decision-reason normalization and uniqueness remain service-validated.
- Only existing structured provenance-issue and trust-outcome payloads are
  adapted; malformed outcomes without metric context still fail closed.
- Production provenance enrichment can identify canonical provenance
  abstentions without gold expectations. Numeric wrong/missing and context
  quarantine outcomes still require an upstream evaluation result carrying
  the existing trust fields; the adapter does not guess those outcomes from
  raw values.
