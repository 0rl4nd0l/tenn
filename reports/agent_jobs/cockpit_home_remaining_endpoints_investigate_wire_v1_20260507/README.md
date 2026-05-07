# Cockpit Home Remaining Endpoints

## Branch / HEAD

- Branch: `preserve/dirty-work-20260430T065748Z`
- Preflight HEAD: `4883e38b69c6e24105f82b9dc6813defc57afb9c`
- Final milestone commit: this report is included in the milestone commit; the exact post-amend hash is recorded in the assistant closeout.
- Worktree: `/mnt/sdb2/home/l4nd0/tenn`
- Agent: Codex
- Lane: Reporting
- Execution mode: AUDIT -> SAFE EXTENSION
- Contested surfaces touched: `financial-engine_v2/backend/app/routes/cockpit_api.py`
- Collision risk: controlled MEDIUM

## Task Card Path

- `docs/agent_tasks/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507.md`
- Validation: `python3 scripts/agent_job_contract.py validate ...` returned `ok: true`.
- Note: the task card was amended with `allow_unapproved_safe_extension: true` because this repo requires that metadata for `safe_extension` jobs with `approval_required: false`.
- Note: explicit `cockpit_home.py` and `test_cockpit_home_market_session.py` paths were added because the repo diff checker did not treat `cockpit_home*.py` as a matching glob.

## Registry / Lock Status

- Initial `list-active`: no active jobs.
- Initial `check-overlap`: `ok: true`.
- Claim: `ok: true`, active record `.git/tenn-agent-registry/active/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507.json`.
- Final `check-overlap`: `ok: true`. Registry also showed an unrelated `Evaluation` job in a separate MCP worktree with no file/lane overlap.
- Release: `python3 scripts/agent_job_registry.py release cockpit_home_remaining_endpoints_investigate_wire_v1_20260507 --repo-root /mnt/sdb2/home/l4nd0/tenn` returned `ok: true`.
- Post-release `list-active`: only unrelated `tenn_agent_mcp_oauth_local_v1_20260507` in lane `Evaluation` remained active.
- Production data access: `false`.

## Preflight Summary

- Initial `git status --short --untracked-files=all`: clean.
- `git worktree list`: current worktree plus many sibling integration/audit worktrees; no active registry overlap.
- Recent relevant commits included `feat(reporting): wire cockpit home to bff route`, `feat(reporting): add cockpit home bff route`, and `milestone(reporting): cockpit home contract scaffold`.
- `python` was unavailable on PATH for task-card scripts; repo scripts were run with `python3`.
- System contract read before implementation; target layer was backend Reporting API + Next BFF client/presentation. No GPU process was spawned or restarted.

## Subagent Reports Summary

- Subagent A: Home BFF already read `/api/health`, `/api/cockpit/holdings`, and `/api/commentary/recent?limit=5`; market session, movers, attention queue, and narrative were explicit `DATA_MISSING`.
- Subagent B: market session was the safest deterministic backend candidate because existing XASX calendar utility exists; attention queue is feasible but operational; source handoff remains ambiguous.
- Subagent C: direct Home collision was low. A transient dirty-worktree snapshot showed unrelated news/runtime files outside this task, but final registry overlap and check-diff were clean after those files were gone.

## Endpoint-by-Endpoint Decision Table

| Area | Decision | Result |
|---|---|---|
| Market session / next event | Wired | New backend `/api/cockpit/home/market-session`; BFF marks market session `READY` when endpoint succeeds. |
| Portfolio total / coverage | Kept existing | Still uses holdings with currency guard; local personal data only. |
| Portfolio day change | Kept `DATA_MISSING` | No deterministic holdings day-change fields. |
| Market movers | Kept `DATA_MISSING` | No deterministic Home endpoint; no TradingView/tool synthesis added. |
| Recent commentary | Kept existing | Context-only `/api/commentary/recent`; no narrative synthesis. |
| Attention queue | Deferred | Existing local followup state needs separate operational contract. |
| Source detail / chat handoff | Not expanded | Approved commentary source resolvability is not proven. |
| Narrative | Kept `DATA_MISSING` | No backend narrative endpoint; no LLM synthesis. |

## Files Changed

- `docs/agent_tasks/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507.md`
- `reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/INVESTIGATION.md`
- `reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/README.md`
- `reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/diff-check.json`
- `financial-engine_v2/backend/app/services/cockpit_home.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_cockpit_home_market_session.py`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`

## Tests / Lint / Type / Browser Validation

- `pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`: passed, 2 files / 13 tests.
- `npx tsc --noEmit --pretty false`: passed, no output.
- `pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-contract.ts types/cockpit-home.ts components/cockpit/home --max-warnings=0`: passed, no output.
- `.venv/bin/python -m pytest backend/tests/test_cockpit_home*.py -q`: passed, 3 tests.
- `.venv/bin/python -m ruff check backend/app/services/cockpit_home.py backend/app/routes/cockpit_api.py backend/tests/test_cockpit_home_market_session.py`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff ...`: passed after explicit allowed paths were added.
- Browser validation: started validation backend on `:8010` with temporary `DATA_ROOT` and `COCKPIT_STATE_DB`, then Next dev on `:3001` with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8010`.
- Browser `/api/cockpit/home`: HTTP 200, `data_state=PARTIAL`, `market_session.data_state=READY`, session `POST_MARKET`, next event `ASX open`.
- Browser `/`: HTTP 200, rendered Home through BFF, displayed `HOME STATE: PARTIAL`, did not display `NO_MARKET_SESSION_ENDPOINT`, still displayed unsupported missing signals, had no mock fixture text, and had `button button` count `0`.
- Browser network: no `/chat`, `/api/chat`, or `/full-chat` navigation/request observed. The app shell did request `/api/cockpit/chat/sessions?limit=200`, which is not the Home BFF route.
- Known out-of-scope dev warning observed: root HTML hydration warning for `color-scheme`, explicitly not touched.

## What Is Now Live

- Backend-owned deterministic ASX market session endpoint:
  - `GET /api/cockpit/home/market-session`
  - Uses the existing backend XASX calendar utility.
  - Returns `exchange`, `timezone`, `session`, `session_date`, `next_event_label`, `next_event_at`, and `as_of`.
- Home BFF now calls that endpoint and removes `NO_MARKET_SESSION_ENDPOINT` when the endpoint succeeds.
- If the endpoint is unavailable or malformed, Home still exposes `DATA_MISSING` with `MARKET_SESSION_ENDPOINT_UNAVAILABLE` or `MARKET_SESSION_RESPONSE_INVALID`.

## What Remains DATA_MISSING and Why

- `NO_MARKET_MOVERS_ENDPOINT`: no deterministic Home backend endpoint.
- `NO_ATTENTION_QUEUE_ENDPOINT`: local followup state exists, but not wired in this task because it needs a separate operational contract.
- `NO_RECENT_COMMENTARY`: validation temp state had no approved commentary; production behavior remains backed only by `/api/commentary/recent`.
- `PORTFOLIO_DAY_CHANGE_UNAVAILABLE`: holdings endpoint does not expose deterministic day-change fields.
- `NO_SESSION_SUMMARY_ENDPOINT`, `NO_THEME_CANDIDATES_ENDPOINT`, `NO_TOMORROW_PREP_ENDPOINT`: no Home narrative endpoint and no LLM synthesis added.
- Source detail / Home-to-chat resolver: still not expanded because source resolvability is not proven for approved commentary.

## Collision Risks

- Controlled MEDIUM because `cockpit_api.py` is a contested surface.
- No active registry overlap at final check.
- No direct Home dirty-file overlap outside this job at final status.
- No financial truth, extraction, memory, embeddings, Qdrant, news ingestion, query orchestration, or unrelated Cockpit tabs were edited.

## DATA_MISSING

- Current-turn evidence cannot verify any real production holdings, commentary, source-detail, market-mover, or attention-queue data because validation used an isolated temporary backend state.
- The original live backend on `:8000` returned 404 for the new route before the validation backend was started; browser validation therefore used the updated code on `:8010`.

## Final Git Status

Pre-commit changed files before staging:

```text
 M cockpit-ui/lib/cockpit-home-api.test.ts
 M cockpit-ui/lib/cockpit-home-api.ts
 M financial-engine_v2/backend/app/routes/cockpit_api.py
?? docs/agent_tasks/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507.md
?? financial-engine_v2/backend/app/services/cockpit_home.py
?? financial-engine_v2/backend/tests/test_cockpit_home_market_session.py
```

Report artifacts under `reports/agent_jobs/cockpit_home_remaining_endpoints_investigate_wire_v1_20260507/` exist but are ignored by this repo's git status rules.

Post-commit status: clean for this task.

## Project Memory Save Recommendation

Save: Cockpit Home now has deterministic backend-owned market-session wiring via `/api/cockpit/home/market-session`; unsupported movers, attention queue, portfolio day-change, source detail, and narrative remain explicit `DATA_MISSING`/partial rather than synthesized.
