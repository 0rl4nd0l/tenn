---
job_id: marketplace_capture_missing_token_disabled_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/marketplace_capture_missing_token_disabled_v1_20260602.md
  - cockpit-ui/app/marketplace-capture/page.tsx
  - cockpit-ui/tests/marketplace-capture-helper.spec.ts
  - reports/agent_jobs/marketplace_capture_missing_token_disabled_v1_20260602/README.md
  - reports/agent_jobs/marketplace_capture_missing_token_disabled_v1_20260602/status.json
  - reports/agent_jobs/marketplace_capture_missing_token_disabled_v1_20260602/validation.json
  - reports/agent_jobs/marketplace_capture_missing_token_disabled_v1_20260602/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/marketplace_capture_missing_token_disabled_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_issue: 52
---

# Marketplace Capture Missing Token Disabled State

## Objective

Fix issue #52 by preventing the Marketplace capture helper from rendering a
dead `href="#"` capture action when the helper route is opened without a capture
token.

## Scope

Primary lane: Reporting.

Mode: safe extension.

This task may edit only the Marketplace capture helper page, a focused
Playwright regression, this task card, and the report bundle.

## Acceptance Criteria

- `/marketplace-capture` without `token` renders an explicit missing-token or
  expired-helper state.
- The missing-token route does not expose a usable `href="#"` capture link.
- The missing-token route shows a return-to-Cockpit action.
- `/marketplace-capture?token=<valid>&url=<listing>` still renders a
  `javascript:` bookmarklet for `Capture Marketplace Listing`.

## Hard Boundaries

- Do not edit backend routes.
- Do not edit token issuance or token validation storage.
- Do not add dependencies.
- Do not mutate runtime, services, DB, Qdrant, news, memory, financial truth,
  parser routing, extraction prompts, gold labels, model config, or GPU config.
- Do not touch shared-checkout dirty files.
- Do not close issue #52 until the covering PR merges and the close gate is
  accepted.

## Required Preflight

1. Validate this task card.
2. Run registry list-active and check-overlap.
3. Claim this task only if there is no HIGH overlap.
4. Re-check issue #52 and duplicate PR coverage before implementation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/marketplace_capture_missing_token_disabled_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/marketplace_capture_missing_token_disabled_v1_20260602.md`
- registry claim/release
- focused Cockpit UI lint for touched files
- focused Playwright regression for missing-token and valid-token routes
- `jq empty reports/agent_jobs/marketplace_capture_missing_token_disabled_v1_20260602/*.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/marketplace_capture_missing_token_disabled_v1_20260602.md`

## Closeout Policy

This job may open a PR and comment on #52, but must leave #52 open until the
covering PR merges.
