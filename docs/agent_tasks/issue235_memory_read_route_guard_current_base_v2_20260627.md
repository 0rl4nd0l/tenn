---
job_id: issue235_memory_read_route_guard_current_base_v2_20260627
owner: Codex
lane: Memory
supporting_lanes:
  - Provenance
  - Reporting
status: approved
approval_required: false
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
allow_audit_code_changes: true
issue_refs:
  - 235
pr_refs:
  - 439
base: origin/migration/clean-runtime-baseline-reconstruct-v1
branch: safe/issue235-memory-read-route-guard-current-base-v2-20260627
worktree: /home/l4nd0/tenn-issue235-memory-read-route-guard-current-base-v2-20260627
output_dir: reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627
allowed_files:
  - docs/agent_tasks/issue235_memory_read_route_guard_current_base_v2_20260627.md
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_memory_read_route_auth.py
  - financial-engine_v2/backend/tests/test_backend_api_client_context.py
  - financial-engine_v2/cockpit/integrations/backend_api.py
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627/README.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627/STATE.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627/DECISIONS.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627/VALIDATION.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627/REVIEW.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627/status.json
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627/diff-check.json
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v2_20260627/NEXT_GOAL.md
timeout_seconds: 7200
---

# Issue 235 Memory Read Route Guard V2

## Objective

Replace stale/conflicting PR #439 with a current-base implementation for issue
#235. Preserve the reviewed memory read-route guard work from PR #439, add the
automated review fix for Python `BackendApiClient.get_company_dump()` API-key
forwarding, validate on canonical head
`38e74ca717197e82102d0554aa031ab09233378f`, and open one replacement PR.

## Scope

Scope: `safe_extension`

This task may guard backend memory read routes, add focused tests, update the
Python client to forward configured API-key headers for company-dump reads, and
document the backend API policy. It must not mutate durable memory stores or
make Cockpit the authoritative memory source.

## Existing Work Classification

- PR #439: `ACTIVE_LINKED` but stale/conflicting after later canonical merges.
  Historical GitHub checks passed on head
  `cbbadbd4081fa6a1ff612883498fbba125c94ae8`.
- PR #439 review blocker: P2 finding that `BackendApiClient.get_company_dump()`
  did not forward `_api_key_headers()` after `/api/context/company_dump` became
  API-key guarded.
- Branch `safe/issue235-memory-read-route-guard-current-base-v1-20260627`:
  preserve as prior validated work. Do not patch it in place.

## Allowed GitHub Mutations

- Push this task branch.
- Open one replacement PR or update PR #439 discussion with a link to the
  replacement PR.
- Request review after local validation passes.
- Merge the replacement PR and close issue #235 only after live GitHub checks
  are green, no unresolved review blockers remain, canonical containment is
  verified after merge, and a closeout comment records the evidence.

Branch deletion, remote branch deletion, label changes, milestones, project
edits, stale-branch mutation, and cleanup are not authorized.

## Allowed Control-Plane Mutations

- Append live Agent Task Ledger entries for claimed, implementation-started,
  PR-opened, merged, blocked, or done state for this task.

## Hard Stops

- Do not edit product/runtime/data/extraction/parser/prompt/source-PDF/gold-label
  content outside the files listed in `allowed_files`.
- Do not mutate DB, Qdrant, Redis, news stores, memory stores, production data,
  runtime services, model/GPU config, or source PDFs.
- Do not merge, rebase, cherry-pick, reset, stash, force-push, prune, delete
  branches, or delete worktrees.
- Do not patch stale #439 worktrees in place.
- Do not weaken memory write confirmation gates or create a frontend memory
  authority path.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue235_memory_read_route_guard_current_base_v2_20260627.md`
- Focused backend auth tests for memory read routes.
- Focused Python client test proving `BackendApiClient.get_company_dump()` sends
  configured API-key headers.
- `ruff` on touched backend route/client/tests.
- `python3 -m py_compile` on touched backend route/client/tests.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue235_memory_read_route_guard_current_base_v2_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue235_memory_read_route_guard_current_base_v2_20260627.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
