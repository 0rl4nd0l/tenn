---
job_id: issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Runtime
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/routes/marketplace_price_intelligence.py
  - financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py
  - reports/agent_jobs/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue245_marketplace_price_intelligence_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - docs/architecture/19_backend_api_surface.md
  - "issue #245"
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
related_issue: 245
supersedes:
  - marketplace_price_intelligence_route_guard_v1_20260626
---

# Issue 245 Marketplace Price-Intelligence Route Guard Current Base

## Objective

Adopt the previously prepared local issue #245 fix onto current canonical:
apply the configured local API-key guard to the standalone Marketplace
price-intelligence router mounted at
`/api/cockpit/marketplace/price-intelligence`.

## Existing Work Classification

- `ADOPT`: `/home/l4nd0/tenn-issue245-marketplace-price-intelligence-route-guard-v1-20260626`
  contains a focused local fix, tests, and doc update.
- `PRESERVE`: leave that older worktree untouched because it is dirty,
  unpublished, and based on older canonical `857e76c3`.
- `NO_FOLLOWUP`: no new issue is needed if focused validation passes and a PR
  is opened for #245.

## Scope

- Add `require_api_key` to the standalone Marketplace price-intelligence route
  family.
- Preserve unauthenticated local-dev behavior when `settings.local_api_key` is
  empty.
- Add focused backend tests proving configured-key mode rejects missing or
  wrong keys before tracked-product, observation, benchmark-snapshot, and
  eBay-sync side effects.
- Add focused backend tests proving matching keys preserve the covered mutation
  flows.
- Guard read routes in configured-key mode rather than leaving public reads
  undocumented.
- Document the guarded route family in
  `docs/architecture/19_backend_api_surface.md`.
- Write report artifacts and open a PR if gates pass.

## Hard Stops

- Do not change Marketplace price-intelligence schema, state semantics, eBay
  scanner behavior, benchmark logic, BFF route semantics, or browser code.
- Do not mutate live DB, Qdrant, Redis, news, memory, source PDFs, extraction
  outputs, prompts, gold labels, runtime/model/GPU/service config, or
  production data.
- Do not start backend, Cockpit, services, Docker, or live browser smoke.
- Do not merge, rebase, reset, stash, clean, prune, or delete any branches or
  worktrees.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and PR-open entries.
- Focused backend tests:
  `uv run --with pytest --with fastapi==0.115.6 --with httpx==0.27.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with PyYAML --with python-multipart --with celery --with qdrant-client --with pymupdf --with beautifulsoup4 --with pandas --with exchange_calendars pytest -q financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py -k "standalone_api or price_intelligence_auth"`
- Ruff touched Python files:
  `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py`
- Py compile touched Python files:
  `python3 -m py_compile financial-engine_v2/backend/app/routes/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py`
- `git diff --check`.
- Code-reviewer pass.
- Task-card `check-diff`.
- Task-card `check-report-artifacts`.
- Ledger validate.
