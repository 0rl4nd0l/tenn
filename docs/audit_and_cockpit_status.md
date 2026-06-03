# Active Runtime Audit and Cockpit UI Status

Date: 2026-06-03

## Scope

This note records a local repo audit of:

1. active `financial-engine_v2/` backend risk areas,
2. documentation gaps in canonical execution guidance, and
3. the current `cockpit-ui/` frontend state.

Evidence is from local files and command output only.

## Executive summary

- The active backend test suite currently passes in isolated local mode: `143 passed, 3 warnings`.
- The highest backend risks are unauthenticated mutating API routes, weak input bounds on backfill requests, and financial extraction outputs that lack field-level provenance.
- The `cockpit-ui/` source tree is not present as tracked source in this checkout. Only build artifacts/cache-like files are visible, so frontend fixes cannot be made reliably until source is restored.
- The built Cockpit route manifest expects many `/api/cockpit/*`, `/rag/*`, `/chat`, and extraction-eval surfaces that the active backend does not expose.

## Verification commands run

```bash
cd financial-engine_v2
PYTHONPATH=backend DATABASE_URL=sqlite:///./data/fe_test_analysis.db TASK_MODE=sync \
AUTO_CREATE_TABLES=true ENABLE_EMBEDDINGS=false ENABLE_QDRANT=false ENABLE_EXTRACTION=false \
.venv/bin/python -m pytest scripts/ -q
```

Result:

```text
143 passed, 3 warnings
```

Warnings are known dependency deprecations:
- Pydantic class-based settings config.
- FastAPI `@app.on_event("startup")`.

Cockpit source/state checks:

```bash
find cockpit-ui -maxdepth 3 -type f | sort | head -80
git ls-files cockpit-ui | wc -l
cat cockpit-ui/.next/server/app-paths-manifest.json
```

Observed:
- `git ls-files cockpit-ui | wc -l` returned `0`.
- `cockpit-ui/` contains `.next/`, `node_modules/`, `test-results/`, and `tsconfig.tsbuildinfo`, but no tracked `package.json`, app source, component source, config, or test files.

## Backend audit findings

### P0 — Unauthenticated mutating API can trigger expensive work

Evidence:
- `financial-engine_v2/backend/app/api/routes.py` exposes `POST /api/backfill/asx20` and `POST /api/backfill/ticker/{ticker}`.
- No auth dependency or API-key guard is present in `financial-engine_v2/backend/app/api/routes.py` or `financial-engine_v2/backend/app/main.py`.

Risk:
- A caller can trigger discovery, PDF download, processing, Celery enqueue, or LLM/provider work.

Recommended fix:
- Add mandatory auth for all non-health routes.
- Require stronger admin/operator auth for mutating routes.
- Add rate limiting or job quotas for backfill.

### P0 — Backfill inputs are weakly bounded

Evidence:
- Backfill routes accept `years:int=1` without FastAPI max constraints.
- `pipeline_service.run_pipeline_sync` only rejects `years <= 0`.

Risk:
- Very large `years` values can produce excessive provider calls and work.

Recommended fix:
- Constrain `years`, `ticker`, price `range`, and `interval` at route boundaries.
- Add tests for rejected inputs.

### P1 — Financial extraction lacks field-level provenance

Evidence:
- `ASXPeriodicFinancial` stores metric columns, `confidence_metrics`, and `source_document_id`.
- `ExtractionRun` stores structured JSON but no per-field page/excerpt/table/currency/unit provenance.

Risk:
- Users cannot audit a specific extracted number back to a PDF page/table/span.

Recommended fix:
- Add field-level provenance records or JSON, e.g. `{metric, value, unit, scale, page, excerpt, extraction_run_id}`.
- Prefer non-destructive/versioned metric facts over overwriting rows without source comparison.

### P1 — Extraction correctness risks remain

Evidence:
- `build_extraction_text` now bounds long text, but it samples head, one keyword window, and tail.
- Prompt schema does not require page citations, units, currency, scale, or sign convention.
- `_coerce_float` accepts plain floats but not common accounting forms such as `1,234`, `(123)`, `$1.2m`, or `A$ million`.

Risk:
- Correct values may be missed or coerced to `None`; extracted values may be unit-ambiguous.

Recommended fix:
- Add deterministic table extraction before LLM extraction.
- Expand accounting-number parsing.
- Require provenance/unit fields in extraction schema.

### P1 — Unknown announcements default to quarterly classification

Evidence:
- `_classify()` in `financial-engine_v2/backend/app/providers/asx_provider.py` returns `("quarterly", "other")` for unrecognized titles.

Risk:
- Non-financial announcements can be treated as quarterly documents.

Recommended fix:
- Use a neutral class such as `("announcement", "other")`.
- Only run financial extraction for allowlisted report classes/subtypes.

### P2 — API/worker parity is improved but still fragile

Evidence:
- API and worker now route core backfill through `pipeline_service.run_pipeline_sync`.
- The API still creates a separate Celery instance in `routes.py` rather than importing the canonical `app.celery_app`.
- Backend worker wrapper and Docker worker wrapper are duplicated files.

Risk:
- Future Celery config/task registration drift.

Recommended fix:
- Use one Celery app/config everywhere.
- Add parity tests for both backend and worker-package wrappers.

### P2 — `GET /api/docs` leaks local PDF paths

Evidence:
- `financial-engine_v2/backend/app/api/routes.py` returns `pdf_path` in `/api/docs`.

Risk:
- Exposes local filesystem layout.

Recommended fix:
- Redact `pdf_path` from public responses or expose downloads through an authenticated BFF/download route.

## Cockpit UI investigation

### Blocker — source is absent from this checkout

`cockpit-ui/` appears to be an untracked built artifact/cache directory, not a source tree.

Observed files include:
- `.next/`
- `node_modules/`
- `test-results/`
- `tsconfig.tsbuildinfo`

Missing as tracked source:
- `package.json`
- `app/`
- `components/`
- `lib/`
- `tests/`
- `next.config.*`
- `vitest.config.*`
- `playwright.config.*`

Until source is restored, frontend implementation work should be treated as blocked.

### Built route surface is much larger than backend route surface

The built manifest includes routes such as:
- `/api/cockpit/action/execute`
- `/api/cockpit/claims/verify`
- `/api/cockpit/holdings`
- `/api/cockpit/home`
- `/api/cockpit/memory/*`
- `/api/cockpit/metrics/*`
- `/api/cockpit/watchlist`
- `/chat`
- many marketplace and feedback routes

The active backend currently exposes only:
- `GET /api/health`
- `GET /api/docs`
- `GET /api/financials`
- `GET /api/risk`
- `GET /api/price`
- `POST /api/backfill/asx20`
- `POST /api/backfill/ticker/{ticker}`

Implication:
- Many Cockpit flows likely depend on a separate Next BFF layer, missing backend routes, or source code not present in this checkout.

### Hard missing route candidate: `/api/cockpit/config`

Source maps/build references indicate multiple UI components call `/api/cockpit/config`, but the built app-path manifest does not list an `app/api/cockpit/config/route` entry.

Likely affected areas:
- chat screen
- sidebar
- status bar
- settings
- operations GPU workload card
- verification screen

Recommended next step:
- Restore Cockpit source and add/verify a `/api/cockpit/config` BFF route, or remove the dependency from UI components.

## Documentation updates made

This note is the canonical local audit record for the current run.

Also update `docs/current_system.md` to align quickstart instructions with the canonical backend execution path rather than root `python run.py`.

## Recommended next implementation order

1. Add backend auth/input constraints for mutating API routes.
2. Restore or quarantine `cockpit-ui/` source; do not treat `.next/` artifacts as source.
3. Add route parity checks between Cockpit expected BFF routes and backend/Next route manifests.
4. Add field-level financial provenance and stricter extraction schemas.
5. Fix classification default for unknown ASX announcements.
6. Consolidate Celery app usage.
