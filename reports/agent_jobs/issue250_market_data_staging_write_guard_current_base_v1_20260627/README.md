# Issue #250 Market Data Staging Write Guard

Status: DONE_WITH_RISK

## Summary

This task keeps market-data GET routes public for non-staging reads, but adds an
operator boundary before OpenBB sidecar refresh and staging persistence when
`openbb_sidecar_enable_staging_writes` is enabled.

The change is intentionally narrow:

- `GET /api/price` now requires the configured `X-API-Key` before the OpenBB
  sidecar branch can run when staging writes are enabled.
- `GET /api/fundamentals/profile`, `/summary`, and `/statements` now require
  the configured `X-API-Key` before OpenBB sidecar refresh and staging
  persistence when staging writes are enabled.
- Focused tests prove missing or wrong keys are rejected before provider or
  persistence calls.
- Focused tests prove staging-disabled GETs remain public.
- Focused tests prove matching keys preserve the sidecar + staging path.
- The backend API surface doc now records the conditional guard contract.

## Scope Boundaries

No production DB, Qdrant, Redis, news store, memory store, source PDF,
extraction output, prompt, gold label, runtime/model/GPU/service config, or
production data was mutated.

This does not promote OpenBB staging payloads into canonical ASX financial
metrics and does not change existing ingestion, backfill, process, or analysis
route guards.

## Result

Issue #250 code remediation is complete in this worktree and ready for PR. Live
backend service functionality was not started or proven, so closeout uses
`DONE_WITH_RISK` rather than live-runtime `DONE`.
