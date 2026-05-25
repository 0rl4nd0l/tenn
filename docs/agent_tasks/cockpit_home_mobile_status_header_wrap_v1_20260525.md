---
job_id: cockpit_home_mobile_status_header_wrap_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_mobile_status_header_wrap_v1_20260525.md
  - reports/agent_jobs/cockpit_home_mobile_status_header_wrap_v1_20260525/README.md
  - reports/agent_jobs/cockpit_home_mobile_status_header_wrap_v1_20260525/status.json
  - reports/agent_jobs/cockpit_home_mobile_status_header_wrap_v1_20260525/diff-check.json
  - cockpit-ui/components/cockpit/home/data-health-strip.tsx
  - cockpit-ui/components/cockpit/home/market-status-header.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_home_mobile_status_header_wrap_v1_20260525
mutation_mode: safe_extension
production_data_access: false
---

# Task

Fix GitHub #43: Cockpit landing page mobile status/header chips overflow off-screen.

# Scope

Make the Home status/header surfaces wrap or stack on narrow viewports so critical Home state, backend/session, and holdings/status chips remain visible without hidden horizontal scrolling.

# Hard Boundaries

- Do not touch Strategy Lab cards, backend routes, data contracts, financial truth, extraction, query routing, memory, stores, runtime services, Docker, env files, or broad Cockpit layout behavior.
- Do not implement broad mobile issue #46 in this task.
- Do not change Home BFF semantics or source-label behavior.

# Required Outputs

- Bounded UI code changes in `data-health-strip.tsx` and `market-status-header.tsx`.
- `reports/agent_jobs/cockpit_home_mobile_status_header_wrap_v1_20260525/README.md`
- `reports/agent_jobs/cockpit_home_mobile_status_header_wrap_v1_20260525/status.json`
- `reports/agent_jobs/cockpit_home_mobile_status_header_wrap_v1_20260525/diff-check.json`

# Validation

Run and report:

- task-card validate
- registry list-active/check-overlap/claim/release
- focused eslint and TypeScript checks
- browser smoke at `390x844` for `/`
- `git diff --check`
- task-card check-diff
