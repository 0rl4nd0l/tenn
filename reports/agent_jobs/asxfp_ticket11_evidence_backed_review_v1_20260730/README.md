# ASXFP Ticket 11 closeout

## Outcome

The bounded Ticket 11 CI repair makes the decision-reason ORM column portable
to SQLite schema compilation by using generic JSON with a PostgreSQL JSONB
variant. The migration and its PostgreSQL-only lifecycle constraint remain
unchanged, and ORM DDL emits that JSONB-dependent constraint only for
PostgreSQL. SQLite tests do not receive or claim the production lifecycle
constraint. The repair also restores the established `process_document`
caller contract: mutable extraction dictionaries are enriched in place and
the exact payload object reaches `_upsert_financial_rows`; generic mappings
are safely copied. The staging payload is enriched once, shared by both
financial sinks, and continues through the same fail-closed trust predicate.

The current fresh-head rejection repair closes both reported P1 paths.
Production staging passes the single enriched payload to both projection
sinks, and one trust gate prevents explicit abstain/quarantine plus malformed,
unknown, or unscoped trust metadata from reaching either the legacy profile or
accepted observations. Valid scoped unresolved values still queue for review.
Explicit trusted outcomes with no triggers retain automatic projection, and
the repair does not synthesize trust outcomes.

Approval now uses conflict-safe `INSERT ... RETURNING` and compares the
persisted identity with the exact reviewed observation before marking the
review approved. A deterministic identity conflict raises, leaves the review
pending, commits nothing, and returns the API's existing fail-closed 400
semantics after rollback. Actor, unique non-empty reasons, automatic UTC
decision time, rejection non-promotion, candidate provenance identity, and
review-decision provenance remain intact.

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
- A direct static-import assertion was also attempted, but the offline
  interpreter reported `No module named 'sqlalchemy'`.
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

Current fresh exact-head rejection-repair validation:

- Exact base commit `136c889ec7cce81d6c02d31717f0449693eefd9b`,
  tree `3f898a3867fdb2185521e3306d34f45a41f40d03`, parent Ticket 10
  `c57698a2e852d74d84dbb30402a0d654515d6a44`, and authority SHA-256
  `e28516984ca7b020f028385908c383b1e3fcb2b41617e30f7561bff34bdebea8`
  matched.
- Focused fake-only pytest was attempted with
  `python3 -m pytest -q
  financial-engine_v2/backend/tests/test_financial_observation_reviews.py -k
  'scoped_unresolved_payload or malformed_or_unscoped or
  approval_identity_conflict'`; the offline interpreter reported
  `No module named pytest`. No installation was attempted.
- `python3 -m py_compile` for the three changed production modules and focused
  test passed.
- Ruff was attempted but unavailable in the offline interpreter:
  `/usr/bin/python3: No module named ruff`.
- `git diff --check` passed after the task-card/report closeout update.
- The changed product/test/task-card/report paths are within the existing
  Ticket 11 allowlist and remain unstaged.
- Controller verification in the disposable dependency environment passed:
  `119 passed, 1 deselected, 1 warning`. The warning is the repository's
  existing unknown `asyncio_default_fixture_loop_scope` pytest option.
- Controller Ruff passed for the changed financial-observation service and
  focused test after three import-only test cleanups, with the file's two
  pre-existing `FURB157` Decimal-style findings excluded. Undefined-name and
  syntax rules passed for the legacy API/pipeline files; broader Ruff reports
  their pre-existing FastAPI, import, optional-type, and exception-style debt.
- Controller `py_compile`, task-card validation, exact allowlist diff check,
  and `git diff --check` passed.

Bounded Ticket 11 CI-repair validation:

- Exact base commit `7740cac802a3bab071a1815a6090d5672369883c`,
  tree `ff005d3f9433bb960352b2df29b894c25327fe35`, and authority
  SHA-256 `e28516984ca7b020f028385908c383b1e3fcb2b41617e30f7561bff34bdebea8`
  matched before edits.
- CI run `30493177763`, job `90715762859`, reported 11 failures after
  3732 passing tests on that exact head.
- Focused regressions cover SQLite/PostgreSQL ORM type and lifecycle-constraint
  DDL selection plus in-place mutable-dict enrichment with safe
  generic-mapping copying.
- The existing out-of-allowlist payload guardrail test was inspected but not
  edited.
- Focused pytest was attempted, but the offline interpreter reported
  `/usr/bin/python3: No module named pytest`; no installation was attempted.
- `python3 -m py_compile` passed for the three changed production modules and
  focused Ticket 11 test.
- Direct AST compilation passed for the same four Python files.
- Ruff was attempted, but the offline interpreter reported
  `/usr/bin/python3: No module named ruff`.
- Controller focused validation passed: `119 passed, 1 warning` across
  `test_financial_observation_reviews.py`, `test_financial_observations.py`,
  and `test_rag_payload_guardrails.py`.
- Controller `python3 -m py_compile` passed for the three changed production
  modules and focused Ticket 11 test.
- Controller changed-file Ruff `0.15.6` passed.
- Exact task-card allowlist inspection passed for all six changed files.
- `git diff --check` passed.

No runtime, database, migration, extraction, OCR, model, service, queue, GPU,
deployment, network, or protected-data action was performed.

## Controller finalization

- Candidate implementation commit:
  `bebbee77f92da2b1ee0539d5ab811543998c7d20`
- Candidate implementation tree:
  `111b6135800ec195ec2462973c3272bb51b87c09`
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

- Focused pytest could not run in the offline interpreter because pytest is not
  installed; compile/static validation does not execute SQLAlchemy
  `INSERT ... RETURNING` against PostgreSQL.
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
