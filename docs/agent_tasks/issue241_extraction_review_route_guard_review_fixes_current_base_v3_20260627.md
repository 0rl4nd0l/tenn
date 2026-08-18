---
job_id: issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627
owner: Codex
lane: Evaluation
supporting_lanes:
  - Provenance
  - Reporting
  - Repo Hygiene
status: approved
approval_required: false
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
allow_audit_code_changes: true
issue_refs:
  - 241
pr_refs:
  - 451
base: origin/migration/clean-runtime-baseline-reconstruct-v1
branch: safe/issue241-extraction-review-route-guard-review-fixes-current-base-v3-20260627
worktree: /home/l4nd0/tenn-issue241-extraction-review-route-guard-review-fixes-current-base-v3-20260627
output_dir: reports/agent_jobs/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627
allowed_files:
  - docs/agent_tasks/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/api/extraction_review.py
  - financial-engine_v2/backend/tests/test_extraction_review_route_auth.py
  - financial-engine_v2/backend/tests/test_backend_api_client_context.py
  - financial-engine_v2/cockpit/integrations/backend_api.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - cockpit-ui/components/cockpit/verification/verification-screen.tsx
  - cockpit-ui/components/cockpit/verification/use-snippet-image.ts
  - cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx
  - reports/agent_jobs/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627/README.md
  - reports/agent_jobs/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627/STATE.md
  - reports/agent_jobs/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627/VALIDATION.md
  - reports/agent_jobs/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627/REVIEW.md
  - reports/agent_jobs/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627/status.json
  - reports/agent_jobs/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627/diff-check.json
  - reports/agent_jobs/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627/NEXT_GOAL.md
timeout_seconds: 7200
---

# Issue 241 Extraction Review Route Guard Review-Fix Replacement V3

## Objective

Replace conflicting PR #451 with a current-base implementation for issue #241.
Preserve the validated extraction-review read-route guards, authenticated
snippet image loading, and review fix that authenticates Python review-client
reads, while replaying onto canonical head
`968a613b24783e1929a893ff1f098d8ff63a8ef5`.

## Existing Work Classification

- PR #451: `ACTIVE_LINKED` but currently `DIRTY` / `CONFLICTING` after later
  canonical merges. Its `lint-and-test` and `scan` checks passed on head
  `c7e88d0f928ce18b6db335760beb1ec6f559a1a3`, and a fresh Codex review found
  no major issues after the Python review-client auth fix.
- Branch
  `safe/issue241-extraction-review-route-guard-review-fixes-current-base-v2-20260627`:
  preserve as prior validated work. Do not patch it in place.
- PR #436: stale/conflicting earlier implementation superseded by #451 and now
  this v3 replacement.
- This task supersedes PR #451 only by opening a replacement PR from this fresh
  current-base branch. No branch cleanup is authorized.

## Scope

- Require the existing local API-key dependency for extraction-review read
  routes: `/runs`, `/sessions`, `/session/{session_id}`, `/errors`,
  `/run/{run_id}`, and `/snippets/{image_name}`.
- Preserve existing guarded mutation routes.
- Preserve snippet path traversal checks.
- Update Cockpit extraction-review JSON reads to send `X-API-Key`.
- Update Python review-client reads to send configured API-key headers.
- Load guarded snippet PNGs through an API-key-aware blob fetch path.
- Preserve the repeated-refetch fix from PR #451 by keeping refresh callbacks
  stable.
- Add focused backend and frontend API-client regressions where local tooling
  permits.
- Update backend API-surface docs and report artifacts.

## Allowed GitHub Mutations

- Push this task branch.
- Open one replacement PR or update PR #451 discussion with a link to the
  replacement PR.
- Request review after local validation passes.
- Merge the replacement PR and close issue #241 only after live GitHub checks
  are green, no unresolved review blockers remain, canonical containment is
  verified after merge, and a closeout comment records the evidence.

Branch deletion, remote branch deletion, label changes, milestones, project
edits, stale-branch mutation, and cleanup are not authorized.

## Hard Stops

- Do not mutate production DB, Qdrant, source PDFs, reports, snippets, memory
  stores, canonical financial truth, extraction outputs, parser prompts, gold
  labels, runtime config, model/GPU config, services, or production data.
- Do not weaken snippet path traversal checks or source-PDF allowlists.
- Do not change review item scoring, extraction result semantics, gold labels,
  or human review decision meaning.
- Do not broaden into extraction quality remediation (#96), source-PDF BFF auth
  parity (#155), shared browser API-key architecture (#232), or other route
  families.
- Do not patch PR #451 or PR #436 branches/worktrees in place.
- Do not delete branches or worktrees.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627.md`
- Focused backend route auth tests for extraction-review read routes and
  snippets.
- Focused backend client-context tests for authenticated Python review-client
  reads.
- Focused frontend API-client tests if Vitest is locally available; otherwise
  record the missing toolchain exactly without installing dependencies.
- `ruff` on touched backend files/tests.
- `python3 -m py_compile` on touched backend files/tests.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py validate`
