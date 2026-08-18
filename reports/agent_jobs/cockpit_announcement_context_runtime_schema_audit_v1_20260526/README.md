# Cockpit Announcement Context Runtime Schema Audit

Issue: #84, `[Provenance] Audit missing cockpit_announcement_context runtime schema`

## Decision

Keep #84 open. This pass classifies the root cause as a schema ownership gap,
not a safe report-only fix. Implementation needs a separate schema/materializer
task card with explicit migration and validation ownership.

## Current Evidence

- Issue #84 is open and requests the task card/report path used by this bundle.
- Duplicate search for `cockpit_announcement_context` found #84 and adjacent
  #104 only. #104 covers cross-route evidence-envelope validation, not this
  runtime schema ownership gap.
- No open or closed PR search result directly targets
  `cockpit_announcement_context`.
- Current container inventory did not show live `fe_backend`, `fe_postgres`, or
  `fe_qdrant` containers, so this pass did not refresh the May 26 live
  `UndefinedTable` log evidence.
- Repo search found `financial-engine_v2/backend/app/api/context.py` querying
  `cockpit_announcement_context` for `announcement_context`.
- Repo search found tests in
  `financial-engine_v2/backend/tests/test_context_endpoints.py` that explicitly
  validate missing-table fallback behavior.
- Alembic migration search found no `cockpit_announcement_context` ownership
  under `financial-engine_v2/backend/app/alembic/versions`.
- The only create-table path found in repo code is the ad hoc materializer in
  `financial-engine_v2/scripts/update_ticker_financials.py`.
- Downstream backend and Cockpit code consume `announcement_context`, and
  source-label code can surface `cockpit_announcement_context` when rows exist.

## Interpretation

The table is treated as a materialized provenance surface by context consumers,
but repo schema ownership is not encoded in Alembic. The current fallback is
intentional and honesty-preserving: missing table errors do not crash the
context route, and fallback status remains visible. That fallback does not
resolve whether the table should be migrated, materialized by a bounded loader,
or formally deprecated as optional.

## Implementation Boundary

This audit did not create or execute migrations and did not modify DB state.
The next implementation must first decide ownership:

- required materialized table: add schema/migration ownership plus materializer
  validation;
- optional/deprecated surface: reduce noisy runtime errors while preserving
  explicit `DATA_MISSING` / degraded evidence;
- legacy-only surface: remove or retire consumers only through a separate
  contract review.

## Safe Next Step

Create a dedicated schema/materializer task after active registry conflicts are
clear. That task should own exact Alembic, materializer, context-route, and
focused test files, or explicitly decide that the surface is optional and keep
missing context visible.
