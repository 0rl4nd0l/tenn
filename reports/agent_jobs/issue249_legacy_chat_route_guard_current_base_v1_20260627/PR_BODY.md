## Summary

- Guard legacy `POST /chat` and `POST /api/chat` with the existing local API-key dependency.
- Add route-auth tests proving missing/wrong keys are rejected before analysis and strategy side effects.
- Update backend API surface docs for the guarded legacy chat contract.

## Validation

- RED: focused backend pytest failed before implementation with `20 failed, 22 passed`.
- GREEN: focused backend pytest passed after implementation with `42 passed`.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue249_legacy_chat_route_guard_current_base_v1_20260627.md`

## Notes

No runtime service, DB, Qdrant, Redis, news, memory, source PDF, extraction,
prompt, gold-label, model/GPU, or production data mutation was performed.

Fixes #249.
