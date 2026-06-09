---
job_id: cockpit_mobile_chrome_compact_v1_20260601
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_mobile_chrome_compact_v1_20260601.md
  - cockpit-ui/components/cockpit/cockpit-layout.tsx
  - cockpit-ui/lib/cockpit-mobile-chrome.ts
  - cockpit-ui/lib/cockpit-mobile-chrome.test.ts
  - reports/agent_jobs/cockpit_mobile_chrome_compact_v1_20260601/README.md
  - reports/agent_jobs/cockpit_mobile_chrome_compact_v1_20260601/status.json
  - reports/agent_jobs/cockpit_mobile_chrome_compact_v1_20260601/validation.json
  - reports/agent_jobs/cockpit_mobile_chrome_compact_v1_20260601/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_mobile_chrome_compact_v1_20260601
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
github_mutation_allowed: branch_push_pr_and_issue_comment
related_issue: 46
---

# Cockpit Mobile Chrome Compact

## Objective

Make Cockpit shell chrome switch to compact behavior automatically on narrow
mobile viewports, without requiring the manual iPhone preview preference.

## Scope

This is a first safe slice for issue #46. It is limited to shared Cockpit shell
chrome and a focused helper/test. It must not edit route-specific files already
owned by open PRs.

## Contract Safety

- Target layer: Client/Reporting only.
- Relevant contract: Cockpit remains a client/orchestration layer and reads
  backend state through existing APIs.
- Must not change: backend, retrieval, extraction, DB, Qdrant, news, memory,
  financial truth, route data contracts, model/runtime/GPU/service config.
- GPU process check: not required; this task does not spawn, restart, or depend
  on llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_mobile_chrome_compact_v1_20260601.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_mobile_chrome_compact_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_mobile_chrome_compact_v1_20260601.md --repo-root .`
- focused Vitest for compact-chrome helper
- focused ESLint on touched frontend files
- Playwright mobile viewport smoke for shell chrome
- JSON validation
- path-redaction scan
- `git diff --check`
- task-card `check-diff`
- registry release before final report

## Hard Stops

- Active overlap on `cockpit-layout.tsx` or the new helper/test paths.
- Any route-specific remediation in News, Verification, Home, Chat, Holdings,
  Memory, Marketplace, or other active PR-owned screens.
- Any backend/runtime/schema/data mutation.
