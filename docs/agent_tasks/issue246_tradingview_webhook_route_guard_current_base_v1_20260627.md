---
job_id: issue246_tradingview_webhook_route_guard_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Runtime
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue246_tradingview_webhook_route_guard_current_base_v1_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
  - reports/agent_jobs/issue246_tradingview_webhook_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue246_tradingview_webhook_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue246_tradingview_webhook_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue246_tradingview_webhook_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue246_tradingview_webhook_route_guard_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue246_tradingview_webhook_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
  - "issue #246"
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Small backend route-auth repair with existing local evidence, current-base adoption, focused tests, review, and PR handling."
worker_model_allowed: false
worker_decision_limit: "No workers used; prior local patch and affected route are narrow enough to inspect directly."
escalation_needed: false
related_issue: 246
supersedes:
  - tradingview_webhook_route_guard_v1_20260626
---

# Issue 246 TradingView Webhook Route Guard Current Base

## Objective

Adopt the previously prepared local issue #246 fix onto current canonical:
make `POST /api/cockpit/tv/alert` fail closed unless `TV_WEBHOOK_TOKEN` is
configured and matched, and guard `GET /api/cockpit/tv/alerts` with the local
API-key dependency.

## Existing Work Classification

- `ADOPT`: `/home/l4nd0/tenn-issue246-tradingview-webhook-route-guard-v1-20260626`
  contains a validated local fix and report bundle, but it is dirty,
  unpublished, and based on older canonical `857e76c3`.
- `PRESERVE`: leave that older worktree untouched; reapply the small source,
  test, and doc patch on this fresh current-base worktree.
- `NO_FOLLOWUP`: no new issue is needed if focused validation passes and a PR
  is opened for #246.

## Scope

- Require configured `TV_WEBHOOK_TOKEN` for TradingView webhook ingestion.
- Reject missing or wrong `X-TradingView-Webhook-Token` before alert
  persistence.
- Add `dependencies=[Depends(require_api_key)]` to the alert-history read route.
- Add focused backend tests using an isolated temporary data root.
- Document the external webhook token contract and local API-key read guard in
  `docs/architecture/19_backend_api_surface.md`.
- Write report artifacts and open a PR if gates pass.

## Hard Stops

- Do not expose webhook secrets through browser code or repo files.
- Do not change alert schema/semantics beyond auth and fail-closed behavior.
- Do not mutate live alert stores, DB, Qdrant, Redis, news, memory, source PDFs,
  extraction outputs, prompts, gold labels, runtime/model/GPU/service config,
  or production data.
- Do not start backend, Cockpit, services, Docker, or live browser smoke.
- Do not merge, rebase, reset, stash, clean, prune, or delete any branches or
  worktrees.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and PR-open entries.
- Focused backend tests:
  `uv run --with pytest --with fastapi==0.115.6 --with httpx==0.27.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with PyYAML --with python-multipart --with celery --with qdrant-client --with pymupdf --with beautifulsoup4 --with pandas --with exchange_calendars pytest -q financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py`
- Ruff touched Python files:
  `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py`
- Py compile touched Python files:
  `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py`
- `git diff --check`.
- Code-reviewer pass.
- Task-card `check-diff`.
- Task-card `check-report-artifacts`.
- Ledger validate.
