---
job_id: issue246_tradingview_webhook_env_token_current_base_v1_20260627
owner: Codex
lane: Reporting
supporting_lanes:
  - Runtime
  - Control Plane
status: approved
approval_required: false
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
allow_audit_code_changes: true
issue_refs:
  - 246
pr_refs:
  - 433
base: origin/migration/clean-runtime-baseline-reconstruct-v1
branch: safe/issue246-tradingview-webhook-env-token-current-base-v1-20260627
worktree: /home/l4nd0/tenn-issue246-tradingview-webhook-env-token-current-base-v1-20260627
output_dir: reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v1_20260627
allowed_files:
  - docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/core/config.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v1_20260627/diff-check.json
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v1_20260627/NEXT_GOAL.md
timeout_seconds: 7200
---

# Issue 246 TradingView Webhook Env Token Guard

## Objective

Replace stale/conflicting PR #433 with a current-base implementation for issue
#246, preserving the useful TradingView webhook route guard and fixing the P2
review blocker: webhook tokens configured through the backend `.env` /
`.env.local` settings path must be honored.

## Scope

Scope: `safe_extension`

This task may port the existing bounded route guard from PR #433 onto current
canonical, add `settings.tv_webhook_token` support for env-file-backed tokens,
and add focused route/config regression tests. It must not mutate runtime alert
stores, production data, services, DBs, Qdrant, news, memory stores, source
PDFs, gold labels, extraction prompts, or model/GPU configuration.

## Existing Work Classification

- PR #433: `ACTIVE_LINKED` but `DIRTY` / `CONFLICTING` against current
  canonical, with green checks on stale head and one unresolved P2 review
  finding about env-file webhook tokens.
- Branch `safe/issue246-tradingview-webhook-route-guard-current-base-v1-20260627`:
  preserve as prior work. Do not patch it in place.
- This task supersedes the stale branch only by opening a replacement PR or
  safely updating PR #433 from this current-base branch.

## Allowed GitHub Mutations

- Push this task branch.
- Open one replacement PR or update PR #433 discussion with a link to the
  replacement PR.
- Request review after local validation passes.
- Merge the replacement PR and close issue #246 only after live GitHub checks
  are green, no unresolved review blockers remain, canonical containment is
  verified after merge, and a closeout comment records the evidence.

Branch deletion, remote branch deletion, label changes, milestones, project
edits, and cleanup are not authorized.

## Allowed Control-Plane Mutations

- Append live Agent Task Ledger entries for claimed, implementation-started,
  PR-opened, waiting, merged, closed, blocked, or done state for this task.

## Hard Stops

- Do not mutate production runtime alert stores or seed local `tv_alerts.json`
  outside tmp/test paths.
- Do not patch stale #433 worktrees in place.
- Do not weaken the fail-closed webhook contract or store webhook secrets in
  repo or browser-exposed code.
- Do not merge or close issue #246 unless the closeout gates in this task card
  are satisfied.
- Do not delete branches or worktrees.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v1_20260627.md`
- Focused backend route auth tests for TradingView alert routes.
- Focused config regression proving `settings.tv_webhook_token` is honored.
- `ruff` on touched backend files/tests.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v1_20260627.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py validate`
