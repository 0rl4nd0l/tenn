Issue #286 closeout review after PR #364:

- PR #349 merged deterministic accounting-number parsing for common metric strings.
- PR #350 merged payload-level structured `field_provenance`.
- PR #351 merged consumers preferring structured `field_provenance` with legacy fallback.
- PR #364 merged persisted per-metric `metric_provenance` on `ASXPeriodicFinancial`, backed by Alembic migration `0009_metric_provenance` and `_upsert_financial_rows` wiring that persists provenance only for metrics whose values are actually written.

Validation evidence:

- PR #364 is merged into `migration/clean-runtime-baseline-reconstruct-v1` as merge commit `f6b8a606d391f7e040aa97746098a981edb49841`.
- PR #364 checks are green: `lint-and-test` and `scan`.
- CI on PR #364 reported 3077 backend tests passed plus 89 autodev tests passed.
- Focused persistence coverage verifies metric-keyed provenance preserves source document id, extraction run id, page, row reference/excerpt, scale, currency, and period evidence when present, and does not write provenance for null/absent metric values.

Closeout decision: the explicit #286 acceptance criteria are satisfied:

- each persisted metric can trace to document/run/source excerpt/page when available;
- common accounting formats are covered;
- existing extraction tests pass.

Closing as completed with evidence.
