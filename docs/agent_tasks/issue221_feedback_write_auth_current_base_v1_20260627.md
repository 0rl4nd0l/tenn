---
job_id: issue221_feedback_write_auth_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Runtime
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue221_feedback_write_auth_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/routes/cockpit_feedback.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_response_feedback.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - cockpit-ui/components/cockpit/cockpit-issue-capture.tsx
  - reports/agent_jobs/issue221_feedback_write_auth_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue221_feedback_write_auth_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue221_feedback_write_auth_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue221_feedback_write_auth_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue221_feedback_write_auth_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue221_feedback_write_auth_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: NONE
docs_checked:
  - AGENTS.md
  - docs/README.md
  - "issue #221"
docs_changed: []
docs_followup: NONE
task_tier: small
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "High-risk feedback write-route guard fix requires source/test edits, frontend header propagation, review, and GitHub PR handling."
worker_model_allowed: false
worker_decision_limit: "No workers used; affected routes and callers are narrow enough to inspect directly."
escalation_needed: false
related_issue: 221
supersedes: []
---

# Issue 221 Feedback Write Auth Current Base

## Objective

Fix GitHub issue #221 on current canonical by guarding feedback write/resolve
routes with the existing local API-key dependency and keeping existing Cockpit
frontend callers authenticated when an API key is configured.

## Existing Work Classification

- `CONTINUE`: issue #221 is open and ready; open-PR search found no direct #221
  PR.
- `PRESERVE`: issue #215 deploy-route closeout is separate and remains
  untouched.
- `NO_FOLLOWUP`: no new issue is needed if focused validation passes and a PR is
  opened for #221.

## Scope

- Add `dependencies=[Depends(require_api_key)]` to:
  - `POST /api/cockpit/feedback`
  - `POST /api/cockpit/feedback/flag`
  - `POST /api/cockpit/feedback/flags/{report_id}/resolve`
- Preserve current read/list behavior for flagged feedback routes.
- Update direct Cockpit frontend feedback callers to forward `X-API-Key` when a
  browser/local API key is configured.
- Add focused backend tests proving missing/wrong keys are rejected before store
  or service side effects, and matching keys preserve existing behavior.
- Write report artifacts and open a PR if gates pass.

## Hard Stops

- Do not change feedback artifact schemas, analysis generation, response
  feedback storage semantics, list/read routes, Codex deploy routes, or
  investigation routes.
- Do not mutate live feedback stores, reports outside this job bundle, DB,
  Qdrant, Redis, news, memory, source PDFs, extraction outputs, prompts, gold
  labels, runtime/model/GPU/service config, or production data.
- Do not start backend, Cockpit, services, Docker, or live browser smoke.
- Do not broaden into #108, #215, #218, #223, or #230.
- Do not merge, rebase, reset, stash, clean, prune, or delete any branches or
  worktrees.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and PR-open entries.
- Focused backend tests:
  `uv run --with pytest --with fastapi==0.115.6 --with httpx==0.27.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with PyYAML --with python-multipart pytest -q financial-engine_v2/backend/tests/test_response_feedback.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -k "feedback"`
- Frontend TypeScript/Vitest check for touched route/client surfaces if local
  dependencies are available:
  `corepack pnpm --dir cockpit-ui exec vitest run lib/claim-verification-route.test.ts components/cockpit/chat/chat-screen.test.tsx`
- Ruff touched Python files:
  `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_feedback.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_response_feedback.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- Py compile touched Python files:
  `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_feedback.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_response_feedback.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `git diff --check`.
- Code-reviewer pass.
- Task-card `check-diff`.
- Task-card `check-report-artifacts`.
- Ledger validate.
