---
job_id: nvme2_route_parity_tests_only_v1_20260518
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/nvme2_route_parity_tests_only_v1_20260518.md
  - reports/agent_jobs/nvme2_route_parity_tests_only_v1_20260518/
  - cockpit-ui/
  - financial-engine_v2/backend/tests
  - financial-engine_v2/backend/tests/test_route_parity_contract.py
approval_required: false
timeout_seconds: 2400
output_dir: reports/agent_jobs/nvme2_route_parity_tests_only_v1_20260518
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Add route parity tests only, based on the audited expected contract:

- frontend BFF /api/cockpit/home is expected and should expose honest partial/data_missing state when dependencies are unavailable;
- backend /api/cockpit/home direct aggregate is not required in this branch/profile;
- backend /api/news/status is expected absent in this branch/profile;
- route 404s for these backend aggregate/status paths are not storage migration blockers.

# Hard boundaries

- Do not edit runtime/storage config.
- Do not edit scripts/start_config.env.
- Do not edit financial-engine_v2/docker-compose.yml.
- Do not edit production data.
- Do not mutate DBs/Qdrant/news/PDF/model stores.
- Do not implement new backend routes.
- Do not change BFF behavior unless needed only for test fixture stability and clearly safe.
- Prefer tests and documentation/report artifacts only.
- If source edits are needed beyond tests, stop and report.
