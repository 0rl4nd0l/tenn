---
job_id: issue220_pending_transcripts_auth_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue220_pending_transcripts_auth_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/api/commentary.py
  - financial-engine_v2/cockpit/integrations/backend_api.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - financial-engine_v2/backend/tests/test_backend_api_client_context.py
  - reports/agent_jobs/issue220_pending_transcripts_auth_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue220_pending_transcripts_auth_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue220_pending_transcripts_auth_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue220_pending_transcripts_auth_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue220_pending_transcripts_auth_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue220_pending_transcripts_auth_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: NONE
docs_checked:
  - AGENTS.md
  - docs/README.md
  - "issue #220"
docs_changed: []
docs_followup: NONE
task_tier: small
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Security route-parity fix requires current source/test edits, task-card gates, and GitHub issue closeout if validation passes."
worker_model_allowed: false
worker_decision_limit: "No workers used; the affected route, client method, and tests are narrow and directly inspectable."
escalation_needed: false
related_issue: 220
supersedes: []
---

# Issue 220 Pending Transcripts Auth Current Base

## Objective

Fix GitHub issue #220 on current canonical by protecting
`GET /api/commentary/transcripts/pending` with the existing local API-key
dependency and forwarding `X-API-Key` from `BackendApiClient.get_pending_transcripts()`.

## Existing Work Classification

- `CONTINUE`: issue #220 is open and ready; live open-PR reference scan found no
  active PR explicitly covering #220.
- `PRESERVE`: existing commentary review/approve/reject route guards and tests
  remain the local pattern.
- `NO_FOLLOWUP`: no new issue is needed if focused validation passes and #220 can
  be closed.

## Scope

- Add `dependencies=[Depends(require_api_key)]` to
  `GET /api/commentary/transcripts/pending`.
- Update `BackendApiClient.get_pending_transcripts()` to send the configured
  API-key header when available.
- Add focused route dependency coverage in `test_local_api_key.py`.
- Add focused client header-forwarding coverage in
  `test_backend_api_client_context.py`.
- Write report artifacts and, only if gates pass, open a PR and close issue #220
  through the merge/closeout flow.

## Hard Stops

- Do not change transcript staging, review, approve, reject, purge, recent, or
  takeaways behavior beyond auth/header forwarding for the pending list.
- Do not read or mutate live transcript staging data, Qdrant, DB, Redis, news
  stores, memory stores, source PDFs, extraction outputs, prompts, gold labels,
  runtime/model/GPU/service config, or production data.
- Do not start backend, Cockpit, services, Docker, or live browser smoke.
- Do not broaden into #100, #101, #102, #213, or #221.
- Do not merge, rebase, reset, stash, clean, prune, or delete any branches or
  worktrees.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and done entries.
- Focused backend route-auth test:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_local_api_key.py -q`
- Focused BackendApiClient test:
  `uv run --with pytest --with httpx pytest -q financial-engine_v2/backend/tests/test_backend_api_client_context.py -k pending_transcripts`
- Ruff touched files:
  `uv run --with ruff ruff check financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
- Py compile touched Python files:
  `python3 -m py_compile financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
- `git diff --check`.
- Task-card `check-diff`.
- Task-card `check-report-artifacts`.
- Ledger validate.
