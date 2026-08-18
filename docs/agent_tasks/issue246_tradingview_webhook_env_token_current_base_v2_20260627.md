---
job_id: issue246_tradingview_webhook_env_token_current_base_v2_20260627
owner: Codex
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
status: approved
approval_required: false
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
production_data_access: false
allow_audit_code_changes: true
issue_refs:
  - 246
pr_refs:
  - 449
  - 433
base: origin/migration/clean-runtime-baseline-reconstruct-v1
branch: safe/issue246-tradingview-webhook-env-token-current-base-v2-20260627
worktree: /home/l4nd0/tenn-issue246-tradingview-webhook-env-token-current-base-v2-20260627
output_dir: reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v2_20260627
allowed_files:
  - docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v2_20260627.md
  - financial-engine_v2/backend/app/core/config.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_tv_alert_auth.py
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v2_20260627/README.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v2_20260627/STATE.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v2_20260627/VALIDATION.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v2_20260627/REVIEW.md
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v2_20260627/status.json
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v2_20260627/diff-check.json
  - reports/agent_jobs/issue246_tradingview_webhook_env_token_current_base_v2_20260627/NEXT_GOAL.md
timeout_seconds: 7200
---

# Issue 246 TradingView Webhook Token Current-Base V2

## Objective

Replace PR #449 after canonical moved to `e16267e7` and made #449
`DIRTY` / `CONFLICTING`. Preserve the already reviewed issue #246 behavior:
TradingView webhook ingestion must fail closed without a configured token,
accept a TradingView-sendable JSON `webhook_token`, preserve relay/header
support, avoid persisting secrets, and guard alert-history reads with the
existing local API-key dependency.

## Existing Work Classification

- PR #449: `ACTIVE_LINKED` but now `DIRTY` / `CONFLICTING` after PR #450
  merged into canonical. It had green checks and a fresh Codex no-major-issues
  comment on `e2a1c214ef`, but can no longer merge.
- PR #433: stale/conflicting prior issue #246 implementation, already
  superseded by #449.
- This task supersedes #449 only by opening a fresh current-base replacement
  branch. Do not patch #449 or #433 in place.

## Scope

- Add settings-backed `TV_WEBHOOK_TOKEN` support.
- Make `POST /api/cockpit/tv/alert` fail closed when no webhook token is
  configured.
- Accept either `X-TradingView-Webhook-Token` or JSON `webhook_token`, with
  JSON body support needed for direct TradingView webhooks.
- Reject missing or wrong webhook tokens before persistence.
- Exclude `webhook_token` from persisted alert history.
- Guard `GET /api/cockpit/tv/alerts` with `require_api_key`.
- Add focused backend regressions for token source, token validation,
  persistence sanitization, and alert-history route auth.
- Update backend API-surface docs and report artifacts.

## Allowed GitHub Mutations

- Push this task branch.
- Open one replacement PR or update PR #449 with a link to the replacement PR.
- Request review after local validation passes.
- Merge the replacement PR and close issue #246 only after live GitHub checks
  are green, no unresolved review blockers remain, canonical containment is
  verified after merge, and a closeout comment records the evidence.

Branch deletion, remote branch deletion, label changes, milestones, project
edits, stale-branch mutation, and cleanup are not authorized.

## Hard Stops

- Do not mutate production DB, Qdrant, news stores, memory stores, canonical
  financial truth, extraction outputs, parser prompts, gold labels, runtime
  services, model/GPU config, or production data.
- Do not start services or run live webhook tests.
- Do not weaken API-key route guards or persist webhook secrets.
- Do not broaden into TradingView strategy semantics, alert scoring, or other
  Cockpit route families.
- Do not patch PR #449 or PR #433 branches/worktrees in place.
- Do not delete branches or worktrees.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v2_20260627.md`
- Focused backend route-auth tests for TradingView alert endpoints.
- `ruff` on touched backend config/route/test files.
- `python3 -m py_compile` on touched backend config/route/test files.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue246_tradingview_webhook_env_token_current_base_v2_20260627.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py validate`
