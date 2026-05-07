---
job_id: cockpit_p1_home_shell_integration_20260507
lane: Reporting
owner: Claude
allowed_files:
  - docs/agent_tasks/cockpit_p1_home_shell_integration_20260507.md
  - reports/agent_jobs/cockpit_p1_home_shell_integration_20260507/**
  - cockpit-ui/**
approval_required: true
timeout_seconds: 2400
output_dir: reports/agent_jobs/cockpit_p1_home_shell_integration_20260507
mutation_mode: safe_extension
production_data_access: false
---

# Task

Safely integrate the P1 Cockpit Home + shell/sidebar upgrade into the current runtime branch only if registry locks are clear and the branch diff is limited to allowed Cockpit UI surfaces.

# Hard boundaries

- Do not touch scripts/news_pipeline/**.
- Do not touch financial-engine_v2/** unless you first stop and report why P1 requires it.
- Do not merge P2/P3/P4 branches.
- Do not delete, clean, reset, stash, or prune unrelated work.
- Do not commit unrelated task cards, smoke tests, report zips, news files, or ignored artifacts.
- If there is an active overlapping Reporting lock that is not stale/complete, stop and report only.

