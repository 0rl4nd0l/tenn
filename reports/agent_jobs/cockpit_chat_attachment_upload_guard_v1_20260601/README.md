# Cockpit Chat Attachment Upload Guard

Issue: https://github.com/0rl4nd0l/tenn/issues/181

## Result

Implemented a narrow server-side API-key guard for
`POST /api/cockpit/chat/attachments/upload`.

## Scope

- Added `Depends(require_api_key)` only to the chat attachment upload route.
- Added focused tests proving missing and wrong API keys are rejected before:
  - holdings CSV import calls `state_store.add_holding`
  - uploaded PDF handling calls `_stage_uploaded_pdf_chunks`
- Added configured-key happy-path coverage for CSV import and PDF source staging.

## Safety

- No router-wide auth change.
- No frontend change required; the existing Cockpit chat upload caller already
  sends `X-API-Key` when configured.
- No production data, Qdrant, memory, extraction, parser, runtime, or model
  surfaces touched.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md --repo-root .`
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_holdings.py -k 'attachment_upload'`
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_holdings.py`
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_holdings.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md`
