# State

- Branch: `safe/issue246-tradingview-webhook-env-token-current-base-v2-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base HEAD: `e16267e7079acfc9b680b89e331a46795d135acc`
- Issue: #246
- Supersedes: PR #449 by replacement branch only; PR #433 remains stale prior work.

## Safety

- No production/runtime data mutation.
- No services started.
- No dependency installation.
- No stale branch/worktree mutation.
- No branch/worktree deletion.

## Changes

- Added `settings.tv_webhook_token`.
- Made `POST /api/cockpit/tv/alert` fail closed with `503` when no token is
  configured.
- Accepted either JSON `webhook_token` or `X-TradingView-Webhook-Token` when it
  matches the configured token.
- Rejected missing/wrong tokens before persistence.
- Excluded `webhook_token` from stored alert history.
- Guarded `GET /api/cockpit/tv/alerts` with `require_api_key`.
- Added focused route-auth/token-source regressions.
- Updated backend API-surface docs.

## Current Gate

Local validation passed. The next step is commit, push, open a replacement PR,
request review, and wait for GitHub checks before any merge/issue closeout.
