# Cockpit Marketplace State Route Guard

Status: `DONE_WITH_RISK`

Issue: #227

Draft PR: #446
https://github.com/0rl4nd0l/tenn/pull/446

Worktree:
`/home/l4nd0/tenn-issue227-cockpit-marketplace-state-route-guard-current-base-v1-20260627`

Branch:
`safe/issue227-cockpit-marketplace-state-route-guard-current-base-v1-20260627`

Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
at `7d6ab6c184332d5413700eb08e6790f530000942`

## Summary

This lane guards direct backend Cockpit Marketplace operator state routes with
the existing configured local API-key dependency.

Changed:

- `GET /api/cockpit/marketplace/missions`
- `POST /api/cockpit/marketplace/missions`
- `GET /api/cockpit/marketplace/missions/{mission_id}`
- `PATCH /api/cockpit/marketplace/missions/{mission_id}`
- `DELETE /api/cockpit/marketplace/missions/{mission_id}`
- `POST /api/cockpit/marketplace/missions/{mission_id}/link-product`
- `DELETE /api/cockpit/marketplace/missions/{mission_id}/link-product`
- `GET /api/cockpit/marketplace/matches`
- `GET /api/cockpit/marketplace/matches/{match_id}`
- `PATCH /api/cockpit/marketplace/matches/{match_id}`
- `PATCH /api/cockpit/marketplace/matches/{match_id}/feedback`
- `PATCH /api/cockpit/marketplace/matches/{match_id}/benchmark-review`
- `GET /api/cockpit/marketplace/alerts`
- `PATCH /api/cockpit/marketplace/alerts/{alert_id}`

Not changed:

- Marketplace browser health routes.
- Marketplace scan launch/status routes.
- Price-intelligence calibration routes.
- eBay sync routes.
- Marketplace scoring, matching, requirement extraction, prompt, scheduler,
  runtime, DB, or browser-helper behavior.
- Router-wide Cockpit auth.
- Frontend source, because current Marketplace helpers and BFF tests already
  pass `X-API-Key` for the guarded paths.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Direct backend Marketplace state routes deny missing/wrong API keys when configured, and authenticated local calls still execute. |
| live output location | Local FastAPI `TestClient` routes under `/api/cockpit/marketplace/*`; current frontend header path in `cockpit-ui/lib/marketplace-api.ts` and `cockpit-ui/lib/marketplace-routes.test.ts`. |
| pre-run max timestamp or count | `DATA_MISSING`; no live deployed backend or browser runtime was probed. |
| post-run max timestamp or count | `DATA_MISSING`; no live deployed backend or browser runtime was probed. |
| rows/files inserted or updated after run start | Backend tests prove rejected mission create/update, match status/feedback/benchmark-review, and alert update requests do not mutate local state or trigger mission warm-up. Source/report files changed in git worktree only. |
| readiness/gate status | Backend focused tests green; static checks green; task-card and ledger validation green; draft PR #446 open; registry claim released. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | `PARTIAL` |
| remaining blocker | No live deployed backend/browser route probe was performed. |

result: PARTIAL

## Closeout

The root backend auth gap is fixed and locally tested. Draft PR #446 carries
`Closes #227`. Because no live deployed backend/browser route probe was run,
this report uses `DONE_WITH_RISK` with runtime functionality result `PARTIAL`.
