# Review

## Findings

- No blocking issues found in the local diff.

## Scope Check

- The webhook write route keeps the external
  `X-TradingView-Webhook-Token` contract and now fails closed when the token is
  not configured.
- The alert-history read route uses the existing `require_api_key` dependency
  rather than exposing the webhook token to browser code.
- Tests cover unset token, missing/wrong token, matching token persistence,
  read-route dependency registration, missing/wrong local API key, and matching
  local API key.
- The API surface doc records the external webhook token contract.

## Residual Risk

- Live runtime behavior is not proven because no backend or Cockpit service was
  started.
- No live alert store was inspected.
