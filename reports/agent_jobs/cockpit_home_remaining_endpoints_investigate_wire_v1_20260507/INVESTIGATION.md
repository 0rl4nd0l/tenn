# Cockpit Home Remaining Endpoints Investigation

## Confirmed Facts

- Branch: `preserve/dirty-work-20260430T065748Z`.
- HEAD at preflight: `4883e38b69c6e24105f82b9dc6813defc57afb9c`.
- Task card: `docs/agent_tasks/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507.md`.
- Task-card validation passed after adding the repo-required `allow_unapproved_safe_extension: true` metadata for `approval_required: false`.
- Registry claim succeeded for `cockpit_home_remaining_endpoints_investigate_wire_v1_20260507`.
- `GET /api/cockpit/home` is currently a Next.js BFF route assembled by `cockpit-ui/lib/cockpit-home-api.ts`.
- Current BFF upstreams are `/api/health`, `/api/cockpit/holdings`, and `/api/commentary/recent?limit=5`.
- Current explicit missing signals include `NO_MARKET_SESSION_ENDPOINT`, `NO_MARKET_MOVERS_ENDPOINT`, `NO_ATTENTION_QUEUE_ENDPOINT`, `PORTFOLIO_DAY_CHANGE_UNAVAILABLE`, and `NO_RECENT_COMMENTARY`.
- Existing backend deterministic ASX calendar utility exists at `financial-engine_v2/backend/app/utils/trading_calendar.py`.
- Existing holdings path can safely support portfolio totals and coverage only with the existing currency guard.
- Existing recent commentary path can safely support context-only Home news, but source handoff remains ambiguous for approved commentary.
- Dirty files appeared during the investigation outside this task card's allowed files, mostly news/runtime/docs surfaces. No direct Home/BFF/backend Home dirty file overlap was observed before Phase B.

## Inferred Facts

- A narrow backend-owned market-session endpoint is a safe extension because it uses a deterministic local XASX calendar utility and does not access Qdrant, Postgres financial truth, memory stores, ingestion, or LLM synthesis.
- Attention queue could be supported by local `market_update_followups`, but wiring it now would add operational-state semantics beyond priority 1 and is not necessary under the current dirty worktree risk.
- Market movers should remain `DATA_MISSING` because existing paths are TradingView/tool-based or stale operational snapshots, not a deterministic Home endpoint.
- Portfolio day-change should remain `DATA_MISSING` because `/api/cockpit/holdings` does not expose deterministic day-change fields.
- Source detail/Home-to-chat handoff should not be expanded because approved commentary source IDs are not proven resolvable through the current attachment path.

## DATA_MISSING

- No backend market-movers endpoint.
- No backend Home narrative/session-summary/theme/tomorrow-prep endpoint.
- No deterministic portfolio day-change fields in the holdings response.
- No deterministic Home source-detail resolver for approved commentary rows.
- No Home-specific Playwright test file within the current allowed file set.
- Repo-supported `check-overlap` currently reports unrelated dirty files outside this task card's allowed files.

## Subagent Summaries

- Subagent A found the Home BFF contract already wires backend liveness, holdings, and recent commentary, and keeps market session, movers, attention, and narrative explicit as `DATA_MISSING`.
- Subagent B found backend market session is the lowest-risk deterministic candidate because `exchange_calendars` XASX support already exists. It also flagged attention queue as feasible but operational, and source handoff as ambiguous.
- Subagent C found direct Home collision risk low, but overall diff hygiene degraded because unrelated dirty files outside `allowed_files` make the registry overlap/check-diff gates fail.

## Endpoint-By-Endpoint Decision Table

| Endpoint / Signal | Existing Source | Decision | Reason |
|---|---|---|---|
| Market session / next event | `financial-engine_v2/backend/app/utils/trading_calendar.py` | Wire in Phase B | Deterministic backend-owned ASX calendar; no data fabrication. |
| Portfolio total / coverage | `/api/cockpit/holdings` | Keep existing wiring | Already deterministic local personal data with mixed-currency guard. |
| Portfolio day change | None in holdings response | Keep `DATA_MISSING` | Avoid deriving or fabricating day-change. |
| Recent commentary | `/api/commentary/recent` | Keep existing context-only wiring | Deterministic approved commentary list, not financial truth. |
| Market movers | No Home endpoint | Keep `DATA_MISSING` | Existing screener/tool paths are not deterministic Home contracts. |
| Attention queue | Local `market_update_followups` state methods | Defer | Feasible but not priority 1; operational semantics need separate focused wiring. |
| Source detail / Home-to-chat | No proven general resolver | Keep current behavior / do not expand | Avoid false resolvability for approved commentary. |
| Narrative | No Home endpoint | Keep `DATA_MISSING` | Would require synthesis or new endpoint. |

## Proposed Wiring Plan

1. Add a backend service under `financial-engine_v2/backend/app/services/cockpit_home.py` that returns deterministic ASX market session fields.
2. Add a narrow read-only backend route at `/api/cockpit/home/market-session`.
3. Update the Home BFF to call `/api/cockpit/home/market-session`.
4. Map a successful market-session response to `READY` market-session state and remove `NO_MARKET_SESSION_ENDPOINT`.
5. Preserve precise `DATA_MISSING` behavior if the market-session endpoint is unavailable.
6. Add focused backend and frontend tests for the new market-session path and fallback.

## Files To Touch

- `financial-engine_v2/backend/app/services/cockpit_home.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_cockpit_home_market_session.py`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- Report files under `reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/`

## Collision Risk

Controlled MEDIUM. The planned route touches `financial-engine_v2/backend/app/routes/cockpit_api.py`, a contested surface, but no active registry overlap was present before claim and current dirty files do not directly touch Home/BFF/backend Home files. The unrelated dirty files mean final check-diff/check-overlap will need to report blocked hygiene rather than silently claim a clean diff.

## Phase B Decision

Proceed with Phase B only for market session / next event. Do not wire market movers, attention queue, source detail, narrative, or portfolio day-change in this task.
