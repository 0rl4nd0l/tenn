---
job_id: home_source_detail_takeaways_api_key_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/home_source_detail_takeaways_api_key_v1_20260602.md
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/components/cockpit/home/source-detail-drawer.tsx
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - reports/agent_jobs/home_source_detail_takeaways_api_key_v1_20260602/README.md
  - reports/agent_jobs/home_source_detail_takeaways_api_key_v1_20260602/status.json
  - reports/agent_jobs/home_source_detail_takeaways_api_key_v1_20260602/validation.json
  - reports/agent_jobs/home_source_detail_takeaways_api_key_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/home_source_detail_takeaways_api_key_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Home Source Detail Takeaways API Key

## Scope

Fix GitHub issue #231 by making Cockpit Home client requests include the configured Cockpit API key when available.

## Target Layer

Cockpit Reporting client/BFF orchestration only. Backend commentary and Home endpoints remain the access-control authority.

## Contract Rules

- Cockpit remains a client/orchestration layer.
- Backend API routes remain the sole authority for commentary and Home data.
- Backend `require_api_key` guards must not be weakened, removed, or bypassed.
- No direct Cockpit access to backend data stores, Qdrant, Postgres, or canonical financial truth.

## Acceptance Criteria

- Main `GET /api/cockpit/home` browser requests include `X-API-Key` when a configured key exists.
- Home source-detail takeaways requests include the same key when a configured key exists.
- Source-detail takeaways still send the existing `source_id` and `limit` request body.
- Existing chat takeaways and recent-source drawer behavior is unchanged.
- Tests cover both Home initial-load and source-detail header behavior.
