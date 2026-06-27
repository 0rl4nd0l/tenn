---
job_id: issue242_context_diagnostics_review_fixes_current_base_v2_20260627
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
  - 448
base: origin/migration/clean-runtime-baseline-reconstruct-v1
branch: safe/issue242-context-diagnostics-review-fixes-current-base-v2-20260627
worktree: /home/l4nd0/tenn-issue242-context-diagnostics-review-fixes-current-base-v2-20260627
output_dir: reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627
allowed_files:
  - docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v2_20260627.md
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py
  - financial-engine_v2/backend/tests/test_backend_api_client_context.py
  - financial-engine_v2/cockpit/integrations/backend_api.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - cockpit-ui/components/cockpit/verification/verification-screen.tsx
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627/README.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627/STATE.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627/DECISIONS.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627/VALIDATION.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627/REVIEW.md
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627/status.json
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627/diff-check.json
  - reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v2_20260627/NEXT_GOAL.md
timeout_seconds: 7200
---

# Issue 242 Context Diagnostics Review Fixes V2

## Objective

Replace stale/conflicting PR #448 with a current-base implementation for issue
#242. Preserve the reviewed context diagnostics guard/redaction work from PR
#448, including the two prior review fixes, while replaying onto canonical head
`c84ad58911ee7d68143396d9545913fa7eb54b98`.

## Scope

Scope: `safe_extension`

This task may port the useful implementation from PR #448 onto current
canonical, preserve its review-fix behavior, validate it, and open one
replacement PR. It must preserve backend-owned context authority and avoid
product/runtime/data mutation.

## Existing Work Classification

- PR #448: `ACTIVE_LINKED` but stale after later canonical merges. Historical
  checks passed on head `59eed0582831cf5de229772c1b8a273c7e2715cb`, and a
  fresh Codex review on that head found no major issues after the two review
  fixes were applied.
- Branch `safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627`:
  preserve as prior validated work. Do not patch it in place.
- This task supersedes PR #448 only by opening a replacement PR from this fresh
  current-base branch. It does not authorize branch deletion.

## Allowed GitHub Mutations

- Push this task branch.
- Open one replacement PR or update PR #448 discussion with a link to the
  replacement PR.
- Request review after local validation passes.
- Merge the replacement PR and close issue #242 only after live GitHub checks
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
- Do not patch stale #448 worktrees in place.
- Do not weaken backend context authority or create a client-side financial
  truth path.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v2_20260627.md`
- Focused backend route auth/redaction tests for context diagnostics.
- Focused Python client tests proving `BackendApiClient` sends API-key headers
  for verification, ticker-context, and company-dump calls.
- Focused frontend API-client tests when local toolchain is available;
  otherwise record `DATA_MISSING` with the missing executable.
- `ruff` on touched backend route/client/tests.
- `python3 -m py_compile` on touched backend route/client/tests.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v2_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v2_20260627.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
