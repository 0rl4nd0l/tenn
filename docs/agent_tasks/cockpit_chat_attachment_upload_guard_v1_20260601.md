---
job_id: cockpit_chat_attachment_upload_guard_v1_20260601
lane: Reporting
supporting_lanes:
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md
  - reports/agent_jobs/cockpit_chat_attachment_upload_guard_v1_20260601/
  - reports/agent_jobs/cockpit_chat_attachment_upload_guard_v1_20260601/README.md
  - reports/agent_jobs/cockpit_chat_attachment_upload_guard_v1_20260601/diff-check.json
  - reports/agent_jobs/cockpit_chat_attachment_upload_guard_v1_20260601/status.json
  - reports/agent_jobs/cockpit_chat_attachment_upload_guard_v1_20260601/validation.json
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_api_holdings.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_chat_attachment_upload_guard_v1_20260601
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Chat Attachment Upload Guard

Issue: https://github.com/0rl4nd0l/tenn/issues/181

## Objective

Add a narrow backend API-key guard to `POST /api/cockpit/chat/attachments/upload`
so attachment uploads cannot import holdings or stage uploaded PDF chat sources
without the configured local API key.

## Safety Scope

- Keep the change limited to the existing Cockpit backend upload route and
  focused upload tests.
- Do not add router-wide authentication or broaden the adjacent action-control
  route hardening work.
- Do not change production DB, Qdrant, news, memory stores, parser routing,
  extraction prompts, gold labels, runtime/model/GPU/service config, or source
  files.
- Do not weaken existing file type, size, CSV, XLSX, PDF, source, or holdings
  validation.

## Acceptance Criteria

- When `settings.local_api_key` is configured, missing or incorrect
  `X-API-Key` upload requests fail before holdings import.
- When `settings.local_api_key` is configured, missing or incorrect
  `X-API-Key` upload requests fail before uploaded PDF chunk staging.
- Negative tests prove `state_store.add_holding` and
  `_stage_uploaded_pdf_chunks` are not called on rejected requests.
- Existing upload behavior remains available when the correct API key is sent.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md --repo-root .`
- Focused backend tests for missing-key rejection, wrong-key rejection, no
  holdings mutation, no PDF staging, and successful authenticated upload.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_attachment_upload_guard_v1_20260601.md`
