---
job_id: issue242_context_diagnostics_review_fixes_current_base_v1_20260627
owner: Codex
lane: Evaluation
supporting_lanes:
  - Provenance
  - Reporting
  - Financial Truth
status: approved
approval_required: false
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
allow_audit_code_changes: true
issue_refs:
  - 242
pr_refs:
  - 438
base: origin/migration/clean-runtime-baseline-reconstruct-v1
branch: safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627
worktree: /home/l4nd0/tenn-issue242-context-diagnostics-review-fixes-current-base-v1-20260627
output_dir: reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627
allowed_files:
  - docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py
  - financial-engine_v2/backend/tests/test_backend_api_client_context.py
  - financial-engine_v2/cockpit/integrations/backend_api.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - cockpit-ui/components/cockpit/verification/verification-screen.tsx
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/DECISIONS.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/diff-check.json
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/NEXT_GOAL.md
timeout_seconds: 7200
---

# Issue 242 Context Diagnostics Review Fixes

## Objective

Replace stale PR #438 with a current-base implementation for issue #242 and
address the two P1 review findings:

- Python `BackendApiClient.get_verification_context()` must pass configured
  API-key headers when guarded verification reads are enabled.
- `/api/context/company_dump` must preserve full diagnostics for internal
  server-side use instead of accidentally taking the unauthenticated redaction
  path when it calls ticker context helpers.

## Scope

Scope: `safe_extension`

This task may port the useful implementation from stale PR #438 onto current
canonical, then add the two review fixes and focused regression coverage. It
must preserve backend-owned context authority and avoid product/runtime/data
mutation.

## Existing Work Classification

- PR #438: `ACTIVE_LINKED` but stale worktree. Live GitHub state is
  `OPEN`, `CLEAN`, and `MERGEABLE`, with two unresolved P1 review comments.
- `/home/l4nd0/tenn-issue242-context-diagnostics-guard-current-base-v1-20260627`:
  `STALE_PATH` by portable guard because the branch is not based on current
  canonical head `eb4a42910fd71077af4a389bd4a9f4400796921b`.
- This task supersedes the stale branch only after a replacement PR is opened or
  the existing PR is safely updated from this current-base branch. It does not
  authorize branch deletion.

## Allowed GitHub Mutations

- Push this task branch.
- Open one replacement PR or update the existing #438 discussion with a link to
  the replacement PR.
- Request review only after local validation passes.

Issue closeout is not authorized by this task card until merge evidence,
canonical containment, and green GitHub checks are verified. Branch deletion,
remote branch deletion, label changes, milestones, project edits, and cleanup
are not authorized.

## Allowed Control-Plane Mutations

- Append live Agent Task Ledger entries for claimed, implementation-started,
  PR-opened, blocked, or done state for this task.

## Hard Stops

- Do not edit product/runtime/data/extraction/parser/prompt/source-PDF/gold-label
  content outside the files listed in `allowed_files`.
- Do not mutate DB, Qdrant, Redis, news stores, memory stores, production data,
  runtime services, model/GPU config, or source PDFs.
- Do not merge, rebase, cherry-pick, reset, stash, force-push, prune, delete
  branches, or delete worktrees.
- Do not patch stale #438 worktrees in place.
- Do not weaken backend context authority or create a client-side financial
  truth path.
- Do not close issue #242 unless a later closeout gate proves the fix is merged
  into canonical and validation passed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v1_20260627.md`
- Focused backend route auth/redaction tests for context diagnostics.
- Focused Python client tests proving `BackendApiClient` sends API-key headers
  for verification and company-dump calls.
- Focused frontend API-client tests when local toolchain is available; otherwise
  record `DATA_MISSING` with the missing executable.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v1_20260627.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
