---
job_id: registry_readonly_no_lock_integration_review_v1_20260526
title: Registry read-only no-lock list-active integration review
owner: Codex
lane: Reporting
primary_lane: Repo Hygiene
supporting_lanes:
  - Reporting
  - Evaluation
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526
allowed_files:
  - docs/agent_tasks/registry_readonly_no_lock_integration_review_v1_20260526.md
  - docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md
  - scripts/agent_job_registry.py
  - scripts/test_agent_job_registry.py
  - reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/README.md
  - reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/status.json
  - reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/validation.json
  - reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/diff-check.json
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/README.md
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/status.json
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/validation.json
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/source_inspection.json
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/read_only_probe.json
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/diff-check.json
  - reports/agent_jobs/registry_readonly_no_lock_integration_review_v1_20260526/github_closeout.md
---

# Registry Read-only No-lock List-active Integration Review

Issue: #85

## Objective

Review and integrate the exact registry read-only/no-lock `list-active` fix from
source commit `af69c6fef20070f06d3b57594c9847d2ba98448a` into the active
`migration/clean-runtime-baseline-reconstruct-v1` baseline if it remains safe.

## Scope

- Confirm the source branch and source commit still exist.
- Inspect the exact changed files from the source commit.
- Confirm the active baseline lacks `list-active --read-only` before integration.
- Confirm no active same-lane registry job blocks this work.
- Cherry-pick only the exact source commit when the scope is safe.
- Write this integration review report and GitHub closeout evidence.

## Forbidden

- Product/backend/frontend/runtime code changes beyond registry tooling.
- DB, Qdrant, news, memory, or canonical financial truth mutation.
- Parser routing, extraction prompts, gold labels, model/runtime/GPU/service
  config changes.
- Broad merge, branch cleanup, delete, prune, reset, stash, or rebase.
- Unrelated dirty-work cleanup or absorption.

## Validation

- `python3 scripts/agent_job_registry.py --help`
- `python3 scripts/agent_job_registry.py list-active --help`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Live registry file snapshot before and after read-only mode to prove no
  `.lock` creation and no registry-file mutation.
- Default `python3 scripts/agent_job_registry.py list-active --repo-root .`
  remains lock-backed and backward compatible.
- Focused registry pytest.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/registry_readonly_no_lock_integration_review_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/registry_readonly_no_lock_integration_review_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/registry_readonly_no_lock_integration_review_v1_20260526.md --repo-root .`
- `git diff --check`
- JSON parse report artifacts.

## Done Criteria

- The source commit is integrated into the active migration baseline only after
  the source scope and validation pass.
- Issue #85 is commented and closed only if the migration baseline contains the
  integrated fix and validation passes.
- Otherwise issue #85 remains open with explicit blocker evidence.
