---
job_id: marketplace_recency_current_target_integration_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/marketplace_recency_current_target_integration_v1.md
  - financial-engine_v2/backend/app/services/marketplace_mission_service.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_marketplace_mission_service.py
  - financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py
  - cockpit-ui/lib/marketplace-api.ts
  - cockpit-ui/components/cockpit/marketplace/match-recency.ts
  - cockpit-ui/components/cockpit/marketplace/matches-screen.tsx
  - cockpit-ui/components/cockpit/marketplace/matches-screen.test.tsx
  - cockpit-ui/components/cockpit/marketplace/match-detail-screen.tsx
  - cockpit-ui/components/cockpit/marketplace/match-detail-screen.test.tsx
  - reports/agent_jobs/marketplace_recency_current_target_integration_v1/README.md
  - reports/agent_jobs/marketplace_recency_current_target_integration_v1/status.json
  - reports/agent_jobs/marketplace_recency_current_target_integration_v1/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/marketplace_recency_current_target_integration_v1
mutation_mode: safe_extension
production_data_access: false
---
