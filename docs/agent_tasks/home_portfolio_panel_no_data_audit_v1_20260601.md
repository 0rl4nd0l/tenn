---
job_id: home_portfolio_panel_no_data_audit_v1_20260601
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/home_portfolio_panel_no_data_audit_v1_20260601.md
  - reports/agent_jobs/home_portfolio_panel_no_data_audit_v1_20260601/README.md
  - reports/agent_jobs/home_portfolio_panel_no_data_audit_v1_20260601/status.json
  - reports/agent_jobs/home_portfolio_panel_no_data_audit_v1_20260601/validation.json
  - reports/agent_jobs/home_portfolio_panel_no_data_audit_v1_20260601/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/home_portfolio_panel_no_data_audit_v1_20260601
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: branch_push_pr_and_issue_comment
related_issue: 86
---

# Home Portfolio Panel No-Data Audit

## Objective

Capture enough current evidence for issue #86 to decide whether the Cockpit
Home portfolio panel is failing to render available data, honestly showing a
partial portfolio state, or blocked behind backend/local holdings conditions.

## Scope

This is a report-only job. It may inspect current repo state, GitHub issue/PR
state, and read-only local runtime endpoints. It must not edit Cockpit Home
product files because open PRs already touch the likely frontend/backend
surfaces.

## Contract Safety

- Target layer: Client/Reporting evidence capture.
- Relevant contract: Cockpit remains a client/orchestration layer; backend is
  the authority for portfolio data served through backend APIs.
- Must not change: financial truth, portfolio holdings, prices, DB/Qdrant,
  memory, extraction, retrieval, Cockpit route ownership, or backend schema.
- Runtime evidence: read-only HTTP GETs only, with report summaries redacting
  holding rows and local paths.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/home_portfolio_panel_no_data_audit_v1_20260601.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/home_portfolio_panel_no_data_audit_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/home_portfolio_panel_no_data_audit_v1_20260601.md --repo-root .`
- redacted backend portfolio endpoint summary
- open PR overlap check for likely Home/frontend/backend surfaces
- JSON validation
- path-redaction scan
- `git diff --check`
- task-card `check-diff`
- registry release before final report

## Hard Stops

- Any required mutation to Cockpit Home product files while PR #134 or PR #159
  own overlapping files.
- Any raw holding-row, local path, credential, or personal portfolio detail in
  committed artifacts.
- Any DB/Qdrant/news/memory/canonical financial truth mutation.
