---
job_id: issue241_extraction_review_route_guard_current_base_v1_20260627
lane: Evaluation
supporting_lanes:
  - Provenance
  - Reporting
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
github_mutation_allowed: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/issue241_extraction_review_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
closeout_scope: issue_241_current_base_pr
allowed_files:
  - docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/api/extraction_review.py
  - financial-engine_v2/backend/tests/test_extraction_review_route_auth.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - cockpit-ui/components/cockpit/verification/verification-screen.tsx
  - cockpit-ui/components/cockpit/verification/use-snippet-image.ts
  - cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx
  - reports/agent_jobs/issue241_extraction_review_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue241_extraction_review_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue241_extraction_review_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue241_extraction_review_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue241_extraction_review_route_guard_current_base_v1_20260627/diff-check.json
---

# Issue #241 Extraction Review Read Route Guard

## Objective

Fix GitHub issue #241 on current canonical base by guarding extraction-review
read routes before they expose review sessions, error queues, run diagnostics,
and snippet images. Preserve existing mutation-route protection and snippet path
traversal checks.

## Duplicate-Work Classification

- Old local worktree:
  `/home/l4nd0/tenn-issue241-extraction-review-route-guard-v1-20260626`
- Old branch:
  `safe/issue241-extraction-review-route-guard-v1-20260626`
- Classification: `ADOPT/PRESERVE`
- Reason: useful validated local work exists in a dirty unpublished checkout,
  but current canonical base still has unguarded extraction-review read routes
  and no current-base PR was found for issue #241.

## Scope

- Require the existing local API-key dependency for
  `GET /api/extraction-review/runs`,
  `GET /api/extraction-review/sessions`,
  `GET /api/extraction-review/session/{session_id}`,
  `GET /api/extraction-review/errors`,
  `GET /api/extraction-review/run/{run_id}`, and
  `GET /api/extraction-review/snippets/{image_name}`.
- Add focused backend tests for unauthenticated denial, authenticated success,
  local-dev no-key behavior, and snippet path traversal preservation.
- Route Cockpit extraction-review JSON reads through API-key-aware client calls.
- Add an API-key-aware snippet image fetch helper and wire the verification
  review UI to use a blob URL for guarded snippet PNGs.
- Add focused API-client tests for extraction-review headers and guarded
  snippet blob fetches.
- Update backend API-surface docs for the route auth boundary.

## Hard Boundaries

- Do not mutate production DB, Qdrant, source PDFs, reports, snippets, memory
  stores, canonical financial truth, extraction outputs, parser prompts, gold
  labels, runtime config, model/GPU config, services, or production data.
- Do not weaken snippet path traversal checks or source-PDF allowlists.
- Do not change review item scoring, extraction result semantics, gold labels,
  or human review decision meaning.
- Do not broaden into extraction quality remediation (#96), source-PDF BFF auth
  parity (#155), shared browser API-key architecture (#232), or other route
  families.
- Do not start runtime services, run live browser smoke tests, install project
  dependencies, mutate lockfiles/package manifests, merge, rebase, reset,
  stash, clean, close issues, or delete branches/worktrees.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md`
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "issue #241 extraction review read route guard current base" --json`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_task_ledger.py validate`
- RED backend focused pytest before implementation.
- GREEN backend focused pytest after implementation.
- Frontend focused Vitest for `cockpit-ui/lib/api-client.test.ts`, or record
  the exact dependency/tooling blocker without installing project dependencies.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/extraction_review.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py`
- `python3 -m py_compile financial-engine_v2/backend/app/api/extraction_review.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_task_ledger.py validate`
- `python3 scripts/agent_job_registry.py release issue241_extraction_review_route_guard_current_base_v1_20260627 --repo-root .`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`

## Definition Of Done

- Configured-key unauthenticated calls to extraction-review read routes are
  denied.
- Matching-key calls to extraction-review read routes succeed and preserve
  existing response behavior.
- No-key local-dev mode preserves existing response behavior.
- Existing guarded mutation routes remain guarded.
- Snippet path traversal checks remain effective after auth is added.
- Verification UI can load guarded snippet PNGs through an API-key-aware fetch
  path instead of a plain unauthenticated image URL.
- Focused backend tests pass.
- Frontend header/blob helper tests are either passed or blocked by missing
  local frontend dependencies with exact evidence.
- Report bundle records validation, docs impact, unsafe actions avoided,
  registry/ledger state, and issue #241 closeout status.
