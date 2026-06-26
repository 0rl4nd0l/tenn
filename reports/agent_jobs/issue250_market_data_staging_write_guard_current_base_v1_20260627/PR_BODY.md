## Summary

- Require the configured local API key before OpenBB sidecar refresh and staging persistence when market-data staging writes are enabled.
- Keep staging-disabled market-data GET routes public.
- Add focused tests for missing/wrong keys, matching keys, and staging-disabled behavior.
- Update backend API surface docs for the conditional guard contract.

## Validation

- RED: focused market-data route auth pytest failed before implementation with `8 failed, 8 passed`.
- GREEN: focused market-data route auth pytest passed after implementation with `16 passed`.
- Shared API-key tests: `15 passed`.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/tests/test_market_data_route_auth.py`
- `python3 -m py_compile financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/tests/test_market_data_route_auth.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue250_market_data_staging_write_guard_current_base_v1_20260627.md`

## Notes

No runtime service, DB, Qdrant, Redis, news, memory, source PDF, extraction,
prompt, gold-label, model/GPU, or production data mutation was performed.

Fixes #250.
