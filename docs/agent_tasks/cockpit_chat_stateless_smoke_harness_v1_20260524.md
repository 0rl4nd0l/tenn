---
job_id: cockpit_chat_stateless_smoke_harness_v1_20260524
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_stateless_smoke_harness_v1_20260524.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/cockpit_service.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/README.md
  - reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/status.json
  - reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/validation.json
  - reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Chat Stateless Smoke Harness

## Objective

Add a dev/test-only safe way to exercise the existing `/api/cockpit/chat` response envelope without persisting chat history, auto-diagnostic reports, Tenn memory, Qdrant, news stores, financial truth, extraction outputs, runtime topology, model/GPU configuration, Docker, cron, or services. Use a CSL filing-only price-trend smoke fixture as the first regression.

## Scope

- Preserve normal `/api/cockpit/chat` behavior by default.
- Add an explicit stateless smoke request gate that reuses the same response metadata/source envelope path.
- Ensure the stateless smoke mode bypasses chat-history persistence and auto-flag writes.
- Add focused tests proving normal persistence still occurs and stateless smoke does not persist.
- Add a CSL fixture proving filing/context-only price-trend text still surfaces `market_data_missing` and `unsupported_or_not_verified`.

## Forbidden

- Do not change retrieval ranking, source selection, Qdrant, Postgres, news SQLite files, Tenn memory stores, financial truth, extraction, parser routing, runtime topology, Docker, cron, systemd, model/GPU configuration, or old worktrees.
- Do not restart backend, frontend, llama, Docker, or systemd units.
- Do not install dependencies.
- Do not broaden into frontend UI changes or live prompt execution.

## Deliverables

- Backend route/service implementation.
- Focused backend tests.
- `reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/README.md`
- `reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/status.json`
- `reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/validation.json`
- `reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/diff-check.json`

## Validation

- Validate task card and registry overlap.
- Claim/release registry job.
- Run focused compile, pytest, ruff.
- Run JSON validation for report artifacts.
- Run `git diff --check`.
- Run task-card `check-diff`.
