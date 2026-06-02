# Cockpit News Status Route Public Redaction

## Scope

- Issue: GitHub #247, "[Reporting] Gate or redact Cockpit news status before exposing projection paths"
- Lane: Reporting
- Worktree: `/home/l4nd0/tenn-cockpit-news-status-route-guard-v1-20260602`
- Branch: `safe/cockpit-news-status-route-guard-v1-20260602`
- Mode: SAFE EXTENSION

## Patch Summary

- Kept `GET /api/cockpit/news/status` read-only and route-compatible by avoiding `financial-engine_v2/backend/app/routes/cockpit_api.py`.
- Changed `build_a2m_news_health_status()` to return a redacted public payload by default.
- Public payload still preserves split-truth fields including:
  - `chat_synthesis=DATA_MISSING`
  - `projection_repair=not_run`
  - canonical SQLite projection status (`missing`, `partial`, or `present`)
- Public payload now redacts operator-only diagnostics:
  - news artifact root path
  - canonical SQLite projection path inventory and absolute paths
  - evidence report paths
  - Qdrant collection identity
- Added `include_diagnostics=True` as an explicit service-builder opt-in for future guarded callers/tests that need full path-bearing diagnostics.
- Updated `docs/architecture/19_backend_api_surface.md` to record the redacted public route contract.

## Overlap Evidence

- Registry `check-overlap` for this task returned `ok: true`.
- Exact open-PR file overlap check found active PRs touching `financial-engine_v2/backend/app/routes/cockpit_api.py`, so this task deliberately avoided the route file and used the accepted public-redaction solution.
- No exact open PR overlap was found on:
  - `financial-engine_v2/backend/app/services/news_health_status.py`
  - `financial-engine_v2/backend/tests/test_cockpit_news_status.py`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_news_status_route_guard_v1_20260602.md --write-report` passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_news_status_route_guard_v1_20260602.md` passed.
- Red test before patch: focused news-status pytest failed 3 redaction/opt-in assertions as expected.
- Green test after patch:
  `PYTHONPATH=/home/l4nd0/tenn-cockpit-news-status-route-guard-v1-20260602/financial-engine_v2/backend:/home/l4nd0/tenn-cockpit-news-status-route-guard-v1-20260602/financial-engine_v2 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_cockpit_news_status.py`
  passed, 4 tests.
- `python -m ruff check financial-engine_v2/backend/app/services/news_health_status.py financial-engine_v2/backend/tests/test_cockpit_news_status.py` passed.
- `git diff --check` passed.

## Files Intentionally Not Touched

- `financial-engine_v2/backend/app/routes/cockpit_api.py` was not touched because active open PRs already modify it.
- No news repair, rebuild, resync, live Qdrant probe, live chat synthesis smoke, extraction, financial truth, memory, parser, runtime/GPU config, or production data was touched.

## Remaining Follow-Up

- A future guarded backend operator route can call `build_a2m_news_health_status(include_diagnostics=True)` if path-bearing diagnostics need to be exposed behind `X-API-Key`.
