# Bug Fix Audit — 2026-03-18

## Scope
This document summarizes what was fixed from the repository bug audit and what remains outstanding.

## Fixed in this change set

1. **ActionRegistry Python resolution hardening**
   - `cockpit/core/actions.py` now resolves Python in priority order:
     1) repo `.venv/bin/python`,
     2) parent workspace `.venv/bin/python`,
     3) `sys.executable` fallback.
   - This removes brittle failures when local `.venv` folders are missing.

2. **`log_change_impact.py` required-field validation restored**
   - Added `_validate_required(args)`.
   - `main()` now exits with status `2` when required fields are missing or left as `TBD`.

3. **`update_ticker_financials.py` quality gate and parser robustness**
   - Added `--zero-rows-policy` with choices:
     - `warn`
     - `auto_rebuild_fail`
     - `strict_fail`
   - Added compatibility guard for parser stubs by using `getattr(args, "dry_run", False)`.
   - Implemented `quality_gate` report section with:
     - policy
     - after_rows
     - passed
     - reasons
     - optional rebuild details
   - Implemented extraction-failure aggregation in report (`extraction_failures.total`) and made it fail status when non-zero.

4. **`resume_pending_downloads.py` extraction failure accounting**
   - Extraction status is now evaluated after `process_document()`.
   - Failed extraction increments per-ticker and totals `extraction_failed_count`.
   - Adds explicit error record `{ "error": "extraction_failed" }` for failed extractions.

5. **Cross-test stub hardening to reduce suite-order contamination**
   - Expanded several test stubs to include required runtime attributes/functions that downstream tests expect (Celery settings, DB `get_db`, pipeline API surface).
   - Files adjusted:
     - `scripts/test_pipeline_service_extraction_accounting.py`
     - `scripts/test_extraction_backlog_tooling.py`
     - `scripts/test_resume_pending_extraction_failures.py`

## Still outstanding / follow-up recommendations

1. **Stronger test isolation strategy**
   - Current fixes reduce contamination risk, but ideal long-term cleanup is to avoid module-level `sys.modules` mutation entirely.
   - Prefer context-managed patching (`patch.dict(..., clear=False)`) with cleanup per test.

2. **Consolidate test stubs**
   - Consider a shared helper fixture/factory for `app.core.config`, `app.core.db`, and `app.services.pipeline` stubs to keep API compatibility consistent.

3. **Optional modernization (non-blocking)**
   - FastAPI startup event deprecation warning (`@app.on_event("startup")`) can be migrated to lifespan handlers.
   - Pydantic `Config` class deprecation can be migrated to `ConfigDict`.

## Validation snapshot (this run)

- Full scripts suite with environment overrides passed (`140 passed`).
- Isolated imports/smoke checks and targeted regression tests were also exercised during diagnosis.
