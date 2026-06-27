# Review

Manual review result: no blocking findings in the local diff.

## Checked

- `settings.tv_webhook_token` is declared on `Settings`, so
  `TV_WEBHOOK_TOKEN` is loaded from the backend env-file path.
- The route helper still honors a process-level `TV_WEBHOOK_TOKEN`, preserving
  direct runtime overrides and test ergonomics.
- `POST /api/cockpit/tv/alert` fails closed before persistence when no token is
  configured and rejects wrong/missing tokens before persistence.
- Direct TradingView alerts can send the shared token as JSON `webhook_token`;
  relay/manual callers can still use `X-TradingView-Webhook-Token`.
- `webhook_token` is excluded from persisted alert history.
- `GET /api/cockpit/tv/alerts` registers `require_api_key`.
- Tests use `tmp_path` for alert persistence and do not touch production data.
- Docs describe both the webhook token and read-history API-key guard.

## Residual Risk

No live backend service was started. GitHub checks and automated review are
still needed after PR publication.
