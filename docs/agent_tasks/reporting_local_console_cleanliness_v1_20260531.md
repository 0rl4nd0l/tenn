---
job_id: reporting_local_console_cleanliness_v1_20260531
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/reporting_local_console_cleanliness_v1_20260531.md
  - reports/agent_jobs/reporting_local_console_cleanliness_v1_20260531/README.md
  - reports/agent_jobs/reporting_local_console_cleanliness_v1_20260531/status.json
  - reports/agent_jobs/reporting_local_console_cleanliness_v1_20260531/diff-check.json
  - cockpit-ui/app/layout.tsx
  - cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx
  - cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.test.tsx
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/reporting_local_console_cleanliness_v1_20260531
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Safely remediate low-collision Cockpit Reporting console-cleanliness issues from GitHub:

- #45: Disable Vercel Analytics script in local Cockpit runtime to avoid local 404 console noise.
- #47: Keep Verification review Select controls consistently controlled so `/verification` does not emit controlled/uncontrolled Select warnings.

# Scope

This is a Cockpit UI client-only Reporting change. It must not change backend APIs, RAG behavior, financial truth, memory, source labels, production data, runtime services, or GPU/LLM configuration.

# Validation

- Validate task card and claim the job before writes.
- Run focused Cockpit UI tests/type checks covering touched files where available.
- Run `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_local_console_cleanliness_v1_20260531.md` before closeout.
