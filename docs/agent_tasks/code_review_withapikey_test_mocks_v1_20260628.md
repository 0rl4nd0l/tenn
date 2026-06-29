---
job_id: code_review_withapikey_test_mocks_v1_20260628
title: Restore component-test API client mocks after withApiKey import
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/code_review_withapikey_test_mocks_v1_20260628
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
allowed_files:
  - docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md
  - cockpit-ui/components/cockpit/chat/chat-screen.test.tsx
  - cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx
  - reports/agent_jobs/code_review_withapikey_test_mocks_v1_20260628/README.md
  - reports/agent_jobs/code_review_withapikey_test_mocks_v1_20260628/VALIDATION.md
  - reports/agent_jobs/code_review_withapikey_test_mocks_v1_20260628/REVIEW.md
  - reports/agent_jobs/code_review_withapikey_test_mocks_v1_20260628/PR_BODY.md
  - reports/agent_jobs/code_review_withapikey_test_mocks_v1_20260628/status.json
  - reports/agent_jobs/code_review_withapikey_test_mocks_v1_20260628/diff-check.json
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
docs_changed: []
docs_followup: NONE
reason: "Code-review follow-up: component tests that mock @/lib/api-client must export withApiKey after Cockpit components import the helper for guarded config reads."
task_tier: small
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The fix is a two-test-file mock update plus focused validation."
worker_model_allowed: false
worker_decision_limit: "no worker; main orchestrator only"
escalation_needed: false
---

# Code Review WithApiKey Test Mock Follow-Up

## Objective

Restore the `@/lib/api-client` mock surface in focused Cockpit component tests
after `ChatScreen` and `CockpitSidebar` started importing `withApiKey`.

## Scope

Allowed:

- Add a `withApiKey` mock export to `chat-screen.test.tsx`.
- Add a `withApiKey` mock export to `cockpit-sidebar.test.tsx`.
- Record focused validation and review evidence under the report directory.

Forbidden:

- No product/runtime/backend/extraction/data changes.
- No package, lockfile, CI, service, DB, Qdrant, Redis, memory, source PDF,
  prompt, model, GPU, or host-global mutation.
- No broad frontend refactor or unrelated test cleanup.
- No merge, rebase, reset, stash, clean, branch deletion, or issue closeout.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md`
- `git diff --check`
- `pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/chat-screen.test.tsx components/cockpit/cockpit-sidebar.test.tsx`
- If local Vitest is unavailable, record the exact missing-tool blocker and run
  available static checks.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/code_review_withapikey_test_mocks_v1_20260628.md --repo-root .`

## Done Criteria

- Both focused test mocks export `withApiKey`.
- Diff remains inside `allowed_files`.
- Local commit and PR are prepared/opened if validation gates allow it.
