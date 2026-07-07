---
job_id: cockpit_router_import_hardening_v1_20260707
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Runtime
  - Repo Hygiene
owner: Codex
approval_required: true
allow_unapproved_safe_extension: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_router_import_hardening_v1_20260707
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
publish_approval: "USER_APPROVED_AFTER_VALIDATION_2026-07-07"
task_scope: implementation_requires_owner_approval
allowed_files:
  - docs/agent_tasks/cockpit_router_import_hardening_v1_20260707.md
  - financial-engine_v2/backend/app/main.py
  - financial-engine_v2/backend/tests/test_cockpit_router_import_contract.py
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/README.md
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/STATE.md
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/DECISIONS.md
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/VALIDATION.md
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/REVIEW.md
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/PR_BODY.md
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/status.json
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/validation.json
  - reports/agent_jobs/cockpit_router_import_hardening_v1_20260707/diff-check.json
docs_impact: DOCS_FOLLOWUP
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/entrypoints.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
docs_changed: []
docs_followup: "Decide during implementation whether startup/operator docs need to mention required Cockpit route visibility diagnostics."
reason: "The completed stateless-smoke proof found a backend route-visibility failure class: /api/health could be live while /api/cockpit/chat was absent because app.main swallowed a transitive Cockpit router import failure."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend import contract and route-visibility regression with no runtime/data mutation."
worker_model_allowed: false
worker_decision_limit: "No workers needed; this is a narrow backend/test slice."
escalation_needed: false
---

# Cockpit Router Import Hardening

## Objective

Harden backend startup so the required Cockpit API router is not silently omitted
when `app.routes.cockpit_api` has a transitive import failure.

This follows the validated stateless-smoke proof lane:

- `/api/health` was live.
- `/api/cockpit/chat` was initially absent from OpenAPI.
- Direct import of `app.routes.cockpit_api` exposed the missing dependency
  class.
- After the environment included the dependency, `/api/cockpit/chat` and
  `/api/cockpit/chat/readiness` appeared and the stateless SSE proof passed.

Current canonical already lists `exchange_calendars>=4.0` in
`financial-engine_v2/backend/requirements.txt`, so this task is not a dependency
add unless a fresh guard/repro proves another missing dependency is canonical.

## Required Preflight

- Run `python3 scripts/tenn_dev_status.py`.
- Run `git status --short --untracked-files=all`.
- Run Tenn git guard preflight for this exact topic.
- Validate this task card.
- Run active registry read-only check.
- Run task-ledger path resolution and validation.
- Confirm unrelated dirty files, especially other task cards, are preserved and
  not staged or absorbed.
- Stop before source edits until Orlando explicitly approves implementation
  from this task card.

## Allowed Implementation After Approval

- Add a focused backend regression test that proves canonical `app.main.app`
  exposes at least:
  - `/api/cockpit/chat`
  - `/api/cockpit/chat/readiness`
- Add a focused regression for the observed failure class: a transitive import
  error inside `app.routes.cockpit_api` must not make Cockpit routes disappear
  silently.
- Change only `financial-engine_v2/backend/app/main.py` as needed to fail
  closed, log clearly, or otherwise expose required Cockpit router import
  failure without weakening validation.
- Keep optional route behavior for unrelated optional routers unchanged unless
  a failing focused test proves the same required-route contract applies.
- Use an existing repo venv or an approved ephemeral validation venv only for
  tests. Do not update dependency files, lockfiles, production/runtime venvs, or
  host-global packages in this slice.

## Forbidden

- No runtime service starts unless separately approved for validation.
- No DB, Redis, Qdrant, news store, memory store, source PDF, extraction prompt,
  parser, gold-label, backfill, scheduler, Docker volume, model/GPU, or
  production data mutation.
- No Cockpit UI edits.
- No `financial-engine_v2/backend/requirements.txt` or lockfile edits unless a
  fresh canonical dependency-missing repro proves the requirement file itself is
  wrong; if so, stop for owner approval before widening the allowlist.
- No registry claim/release, live task-ledger append, GitHub mutation, commit,
  push, merge, rebase, stash, worktree cleanup, or unrelated dirty-file cleanup
  without explicit approval.

## Validation Required After Implementation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_router_import_hardening_v1_20260707.md`
- Focused backend route/import contract test, preferably:
  `python -m pytest financial-engine_v2/backend/tests/test_cockpit_router_import_contract.py -q`
- Existing Cockpit stream route smoke/unit slice if affordable:
  `python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -q`
- `python -m py_compile financial-engine_v2/backend/app/main.py`
- Targeted Ruff check when available through the repo or `uv`.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_router_import_hardening_v1_20260707.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/cockpit_router_import_hardening_v1_20260707.md`
- Final `git status --short --untracked-files=all`

## Runtime Proof Requirement

If the implementation claims live Cockpit functionality is working, complete the
Runtime Functionality Proof table from `AGENTS.md`. Unit tests alone are not
runtime proof. If no approved runtime smoke is run, close as a source/test
hardening result only.

## Definition Of Done

- The task card validates.
- Guard, registry, and ledger checks are current and recorded.
- A failing or route-visibility regression is added before or with the fix.
- The smallest safe change prevents silent omission of the required Cockpit API
  router.
- Validation commands, exit statuses, and raw-log paths are recorded in the
  report bundle.
- Unrelated dirty work remains untouched.
