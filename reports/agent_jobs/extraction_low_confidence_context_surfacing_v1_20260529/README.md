# Extraction Low Confidence Context Surfacing V1

## Scope

SAFE EXTENSION in the Financial Truth lane. This job closes the report-only
`ok_low_confidence` truth-surface gap without running extraction, canary,
backfill, or datastore mutation.

## Implemented

- `GET /api/context/ticker` financial rows now include:
  - `extraction_status`
  - `extraction_run_id`
- `latest_financial_snapshot` includes the same fields.
- `low_confidence_financials` now includes rows when either:
  - `confidence_metrics` is below the configured threshold, or
  - the latest persistable source extraction run has
    `status='ok_low_confidence'`.
- `low_confidence_reason` distinguishes:
  - `metric_confidence_below_threshold`
  - `extraction_run_ok_low_confidence`
- `/api/context/verification` uses the same low-confidence semantics with and
  without a ticker filter.

The run-status projection intentionally uses the latest persistable source run
only (`ok` or `ok_low_confidence`). Later failed runs remain visible through
`extraction_failures`, but they do not relabel an already-persisted financial
row.

## Boundaries

- No third canary batch was run.
- No broad backfill or production extraction was run.
- No production DB write or direct SQL mutation was performed.
- No Qdrant, Redis, news, memory, source-PDF, parser-routing, prompt,
  gold-label, runtime, model, GPU, service, schema, migration, Cockpit UI, or
  GitHub mutation was performed.
- The unrelated Query Orchestration task-card dirt in the baseline worktree was
  not touched.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_low_confidence_context_surfacing_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_low_confidence_context_surfacing_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_low_confidence_context_surfacing_v1_20260529.md --repo-root .`
- `python3 -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_context_endpoints.py`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_context_endpoints.py`
- `PYTHONPATH=.:financial-engine_v2:financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_context_endpoints.py -q`
  - `39 passed`
- `PYTHONPATH=.:financial-engine_v2:financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_backend_api_client_context.py financial-engine_v2/backend/tests/test_context_endpoints.py -q`
  - `58 passed`
- `PYTHONPATH=.:financial-engine_v2:financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -q -k 'non_aud or ok_low_confidence or source_explicit_idr'`
  - `4 passed, 156 deselected`
- SQLite-backed context SQL smoke:
  - `sqlite_context_smoke ok`
- `git diff --check`
- Post-change code-review pass: no remaining findings after changing the
  status projection to latest persistable extraction runs only.

Known validation note:

- The first SQLite smoke attempt failed before exercising the SQL because the
  direct Python call used FastAPI `Query(...)` default objects instead of route
  primitive values. The rerun passed with explicit primitive params.

## Remaining Blockers

- Third #96 canary still requires explicit operator approval and live
  loaded-code proof.
- AAU must be rerun alone after a bounded backend/worker/gpu_worker reload is
  approved.
- Full accurate-extraction graduation still requires the approved canary result,
  post-run payload scorecards, and broader accuracy evidence.
