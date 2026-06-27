# Issue 246 TradingView Webhook Env Token Guard

Status: `LOCAL_VALIDATED`

## Summary

Created a current-base replacement for stale/conflicting PR #433.

The implementation:

- Adds `settings.tv_webhook_token` so `TV_WEBHOOK_TOKEN` from `.env` /
  `.env.local` is loaded by the backend settings path.
- Keeps support for process-level `TV_WEBHOOK_TOKEN`.
- Makes `POST /api/cockpit/tv/alert` fail closed with `503` when no webhook
  token is configured.
- Rejects missing/wrong `X-TradingView-Webhook-Token` before alert persistence.
- Guards `GET /api/cockpit/tv/alerts` with `require_api_key`.
- Documents the TradingView webhook/read auth contract.

## Prior Work

PR #433 is preserved as prior work and not patched in place. This branch ports
the useful route guard onto canonical `eb4a4291` and fixes the P2 review
blocker about env-file-backed webhook tokens.

## Boundary

No runtime alert store, DB, Qdrant, news store, memory store, source PDF, gold
label, service, model/GPU config, or production data was mutated.

## Runtime Functionality Proof

This is a route/config remediation. No live backend service was started and no
production alert store was exercised.

| Field | Required evidence |
| --- | --- |
| intended output | TradingView route rejects unauthenticated/misconfigured requests and accepts configured token requests. |
| live output location | `POST /api/cockpit/tv/alert`, `GET /api/cockpit/tv/alerts`, tmp test alert file. |
| pre-run max timestamp or count | `DATA_MISSING` |
| post-run max timestamp or count | `DATA_MISSING` |
| rows/files inserted or updated after run start | 0 production rows/files; tmp test alert files only. |
| readiness/gate status | Local focused tests pass; PR not opened yet in this report state. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | `PARTIAL` |
| remaining blocker | GitHub PR/check/review/merge/closeout gates not yet complete. |
