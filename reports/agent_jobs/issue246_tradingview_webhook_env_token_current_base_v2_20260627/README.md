# Issue 246 TradingView Webhook Env Token Current-Base V2

Status: `local_validated_pending_push`

This is a fresh current-base replay for issue #246 after PR #450 advanced
canonical to `e16267e7` and made PR #449 `DIRTY` / `CONFLICTING`.

PR #449 is preserved as prior reviewed work. This branch replays the same
bounded behavior on canonical: fail-closed TradingView webhook ingestion,
settings-backed `TV_WEBHOOK_TOKEN`, JSON-body token support for direct
TradingView alerts, no token persistence, and API-key protection on alert
history reads.
