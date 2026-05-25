---
job_id: reporting_ui_safe_issue_fixes_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/reporting_ui_safe_issue_fixes_v1_20260525.md
  - reports/agent_jobs/reporting_ui_safe_issue_fixes_v1_20260525/**
  - cockpit-ui/app/layout.tsx
  - cockpit-ui/app/marketplace-capture/page.tsx
  - cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx
  - cockpit-ui/components/cockpit/verification/verification-sidebar.tsx
  - cockpit-ui/components/cockpit/home/home-page.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/reporting_ui_safe_issue_fixes_v1_20260525
mutation_mode: safe_extension
production_data_access: false
---

# Task

Fix bounded, low-risk Cockpit Reporting UI issues that are safe to complete without runtime, data-store, query, extraction, memory, or Strategy Lab surface changes.

# Issues In Scope

- GitHub #45: Disable Vercel Analytics script in local Cockpit runtime to avoid 404 console noise.
- GitHub #47: Verification page emits controlled/uncontrolled Select warning in production UI.
- GitHub #48: Verification sidebar clips saved review content on desktop due long document titles.
- GitHub #52: Marketplace capture helper enables a dead bookmarklet when opened without a token.
- GitHub #44: Cockpit Home PARTIAL banner truncates missing signals without showing remaining gaps.

# Hard Boundaries

- Do not change backend route behavior, data contracts, financial truth, extraction, parser routing, query routing, memory stores, DB, Qdrant, news stores, Docker, env files, runtime services, or Strategy Lab components.
- Do not touch active registry job files.
- Do not implement issue #55, #51, #49, #46, #53, #42, #43, #40, or #41 in this task.
- Do not run mutating browser flows or backend restart/backfill actions.

# Required Outputs

- Focused UI code changes only in the exact allowlist.
- `reports/agent_jobs/reporting_ui_safe_issue_fixes_v1_20260525/README.md`
- `reports/agent_jobs/reporting_ui_safe_issue_fixes_v1_20260525/status.json`
- `reports/agent_jobs/reporting_ui_safe_issue_fixes_v1_20260525/diff-check.json`

# Validation

Run and report:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/reporting_ui_safe_issue_fixes_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/reporting_ui_safe_issue_fixes_v1_20260525.md`
- claim/release registry job if overlap check is safe
- focused Cockpit UI lint/type/test commands available locally
- `python3 -m json.tool reports/agent_jobs/reporting_ui_safe_issue_fixes_v1_20260525/status.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_ui_safe_issue_fixes_v1_20260525.md`
