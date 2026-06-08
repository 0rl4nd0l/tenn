---
job_id: cockpit_news_status_route_guard_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_news_status_route_guard_v1_20260602.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/services/news_health_status.py
  - financial-engine_v2/backend/tests/test_cockpit_news_status.py
  - reports/agent_jobs/cockpit_news_status_route_guard_v1_20260602/README.md
  - reports/agent_jobs/cockpit_news_status_route_guard_v1_20260602/status.json
  - reports/agent_jobs/cockpit_news_status_route_guard_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_news_status_route_guard_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_news_status_route_guard_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Task

Resolve GitHub issue #247 by making the unauthenticated Cockpit news status route return a redacted public status payload.

# Context

`GET /api/cockpit/news/status` currently returns `build_a2m_news_health_status()` directly. Open PRs already touch `financial-engine_v2/backend/app/routes/cockpit_api.py`, so this task must not edit the route file. The accepted issue path allows either API-key guarding or public redaction. This task chooses public redaction to avoid route-file collision.

# Requirements

1. Validate this task card before implementation.
2. Inspect active jobs and exact open-PR file overlap before implementation.
3. Claim this task if no overlap remains.
4. Preserve split-truth status fields such as `chat_synthesis=DATA_MISSING` and `projection_repair=not_run`.
5. Do not claim A2M/news projection repair, run rebuild/resync jobs, or probe Qdrant/live chat.
6. Remove absolute paths, artifact roots, evidence report locations, and internal collection identity from the default public status payload.
7. Keep full internal diagnostics available only through an explicit service-builder option for tests or future guarded callers.
8. Do not change backend route registration, extraction, financial truth, memory, Qdrant, parser code, runtime/GPU config, or news repair logic.

# Validation

Run focused backend tests for `financial-engine_v2/backend/tests/test_cockpit_news_status.py`.

# Required Output

Write a short report to `reports/agent_jobs/cockpit_news_status_route_guard_v1_20260602/README.md` with:

- patch summary
- overlap/collision evidence
- validation commands and results
- files intentionally not touched
- remaining blockers or follow-up work
