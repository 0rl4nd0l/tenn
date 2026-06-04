---
job_id: cockpit_accessible_controls_news_history_clean_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md
  - docs/claude/STATE.md
  - cockpit-ui/components/cockpit/news/news-screen.tsx
  - cockpit-ui/components/cockpit/news/news-screen.test.tsx
  - cockpit-ui/components/cockpit/history/history-screen.tsx
  - cockpit-ui/components/cockpit/history/history-screen.test.tsx
  - reports/agent_jobs/cockpit_accessible_controls_news_history_clean_v1_20260602/README.md
  - reports/agent_jobs/cockpit_accessible_controls_news_history_clean_v1_20260602/status.json
  - reports/agent_jobs/cockpit_accessible_controls_news_history_clean_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_news_history_clean_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_accessible_controls_news_history_clean_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_and_pr
related_issue: 53
supersedes_pr: 208
operator_approval_source: "User shifted the active goal to UI-focused Reporting work and requested ongoing closeout with isolated worktrees; current live evidence shows PR #208 targets the wrong base branch, so this clean replacement keeps the verified News/History UI slice isolated on the migration baseline."
---

# Cockpit Accessible Controls: News/History Clean Replacement

## Objective

Recreate the narrow issue #53 News and History accessible-control slice from
`origin/migration/clean-runtime-baseline-reconstruct-v1` without inheriting PR
#208's wrong base branch.

This slice is limited to:

- News search query input.
- News ticker filter input.
- News lookback select trigger.
- History job expand/collapse icon buttons.
- History details column header.

## Session Declaration

Agent: Codex

Branch: `safe/cockpit-accessible-controls-news-history-clean-v1-20260602`

Worktree:
`/home/l4nd0/tenn-cockpit-accessible-controls-news-history-clean-v1-20260602`

Lane: Reporting

Execution mode: SAFE EXTENSION MODE

Intended files: this task card, the News and History component/test files,
`docs/claude/STATE.md`, and this report bundle.

Contested surfaces touched: none from AGENTS.md.

Collision risk: LOW. Live duplicate checks found parent issue #53 and wrong-base
PR #208, but no clean replacement PR or remote branch.

Decision: proceed after validation, active-job check, overlap check, and
registry claim.

## Contract Check

Target system layer: Cockpit client UI only.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.2 Cockpit client role, §1.3
retrieval boundary, and §2 mandatory flow. Backend remains authoritative for all
data and retrieval.

What must not change: backend APIs, extraction, retrieval, memory storage,
financial truth, source/evidence labels, Qdrant/Postgres, runtime/model/GPU
configuration, request payloads, handlers, and visible layout.

Why safe: the change only adds durable programmatic names to existing controls
and focused tests prove the names are available through DOM accessibility
queries.

GPU process check required: no. This task does not spawn, restart, or depend on
llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md --repo-root .`
- Focused News and History component tests.
- Targeted ESLint for touched UI files.
- Cockpit UI TypeScript if practical.
- JSON validation for report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md --repo-root .`
- Registry release and final active-job check.

## Hard Stops

- Exact clean duplicate PR found.
- Active registry overlap on News or History component/test files.
- Proposed fix touches adjacent active Cockpit routes.
- Backend/data/runtime/memory/extraction changes are required.
- Validation cannot distinguish visual labels from programmatic names.
