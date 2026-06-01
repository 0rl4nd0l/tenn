---
job_id: cockpit_accessible_controls_news_history_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_accessible_controls_news_history_v1_20260602
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_news_history_v1_20260602.md
  - cockpit-ui/components/cockpit/news/news-screen.tsx
  - cockpit-ui/components/cockpit/news/news-screen.test.tsx
  - cockpit-ui/components/cockpit/history/history-screen.tsx
  - cockpit-ui/components/cockpit/history/history-screen.test.tsx
  - reports/agent_jobs/cockpit_accessible_controls_news_history_v1_20260602/README.md
  - reports/agent_jobs/cockpit_accessible_controls_news_history_v1_20260602/status.json
  - reports/agent_jobs/cockpit_accessible_controls_news_history_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_news_history_v1_20260602/diff-check.json
github_comment_targets:
  - 53
---

# Task

Implement a narrow #53 accessible-control remediation slice for Cockpit News and History only.

# Scope

- Add durable accessible names to News query, ticker, and lookback controls.
- Add durable accessible names to History expand/collapse icon buttons and the details column.
- Add focused component tests that query controls by role/name.
- Keep #53 open because this is only a route slice.

# Boundaries

- Do not edit Chat, Holdings, Watchlist, Marketplace, Thesis, Verification, Memory, Operations, backend, runtime, data, parser, prompt, source, gold-label, model, GPU, or service-config files.
- Do not redesign the News or History screens.
- Do not change request payloads, backend API routes, retrieval behavior, canonical financial truth, DB, Qdrant, news, or memory stores.
- Do not close #53.

# Validation

Run:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_news_history_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_news_history_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_news_history_v1_20260602.md`
- focused Vitest for News and History component tests
- targeted ESLint for touched files
- TypeScript check for Cockpit UI
- JSON parse checks for report artifacts
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_controls_news_history_v1_20260602.md`
- `git diff --check`
- `git diff --cached --check`
- `python3 scripts/agent_job_registry.py release cockpit_accessible_controls_news_history_v1_20260602`

# Definition Of Done

- News query, ticker, and lookback controls are discoverable by role/name.
- History expand/collapse buttons are discoverable by action-specific names.
- #53 receives a status comment linking the PR and noting that broader route coverage remains open.
- No forbidden surfaces are changed.
