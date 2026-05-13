# Cockpit Route Validation Pass v1

## 1. Executive summary

Validated Cockpit page existence, route ownership, read-only BFF/API health, route-handler methods, selected provenance/source-label contracts, and focused UI/route tests on `preserve/dirty-work-20260430T065748Z` at `8beb6bf11f10a401b8a5fbde0be0d54cedc22641`.

Passed: 19 page files and 52 Next route handlers are present; 18 static/page GET probes returned HTTP 200; 162 backend route decorators are present; backend `/api/health`, llama.cpp `/health`, Cockpit health/config/models/queue/docs, Home, Watchlist, Holdings, Marketplace read-only routes, Memory index/company dump, Intel Pulse, and matrix GET probes returned HTTP 200 when called with safe parameters. A focused route/contract Vitest subset passed 35/35 tests.

Not run: chat POST, RAG `/rag/query` POST, extraction eval POST/background jobs, action execute/preview, model load, restart, marketplace scan/sync/calibration/refresh, memory writes, thesis proposal mutations, feedback deploy/investigation spawn, and browser automation. Those routes are mutating, runtime-heavy, or require explicit operator gates.

Top risks: a first 8s GET pass timed out on Home and Holdings before a 12s retry returned 200; one broader focused Vitest command failed 3/66 assertions due apparent UI/test drift; extraction runtime 8001/8002 ambiguity remains a separate Evaluation/Financial Truth follow-up; unrelated dirty application/test files appeared after preflight and block commit/check-diff closeout.

Next safe step: preserve this report, release the registry claim, and run a separate no-code hygiene/coordination step for the unrelated Memory page/UI/test dirty files before committing this task's artifacts.

## 2. Preflight

| item | result |
| --- | --- |
| Date | `2026-05-13T12:41:00+10:00` |
| Logical pwd | `/home/l4nd0/tenn` |
| Git root | `/mnt/hdd-data/home/l4nd0/tenn` |
| Branch / HEAD | `preserve/dirty-work-20260430T065748Z`, `8beb6bf11f10a401b8a5fbde0be0d54cedc22641`, short `8beb6bf11f10` |
| Initial git status | only `?? docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md` after creating the task card |
| Worktrees | large multi-worktree estate present; current worktree `/mnt/hdd-data/home/l4nd0/tenn` at `8beb6bf` |
| Recent log | `8beb6bf milestone(reporting): record task-card hygiene docs state`; previous `4ac0da7 docs(reporting): preserve task-card hygiene audit artifacts` |
| Task-card validation | `ok: true` |
| Registry list-active | `ok: true`, `active_jobs: []` before claim |
| Registry overlap | `ok: true`, no issues before claim |
| Registry claim | acquired for `cockpit_route_validation_pass_v1_20260513` |
| Chorus | Not used. Tool discovery only exposed `wait_for_chat`, which is not useful for read-only route/report inspection without a Chorus chat id. |

Contract check: target layer is Client/Analysis reporting only. Relevant contract rules are backend authority, Cockpit as client/orchestration only, retrieval boundary, no fabricated source-backed evidence, and no memory/financial-truth mutation. This pass is safe because it writes only task/report artifacts, uses GET probes and mocked tests, and does not spawn GPU/model jobs. GPU guard was not required because no llama-server start/restart/load was requested or performed.

## 3. Validation scope

Included pages/routes: Overview/Home, Chat, Watchlist, Holdings, Marketplace Missions, Marketplace Matches, Marketplace Alerts, News, Memory, Thesis Audit, Verification, Operations, Settings, Boot, Intel Pulse, History, plus Updater and Marketplace Capture page existence.

Excluded runtime behaviors: all mutating POST/PATCH/DELETE probes, broad Playwright, full backend pytest, extraction eval runs, action jobs, model load/reload, restart, marketplace scans/syncs, memory writes, thesis proposal apply/confirm/reject, and feedback deploy/investigation.

Excluded reason: this task is SAFE EXTENSION validation/report-only and production_data_access is false.

## 4. Route health summary

| surface | frontend page | BFF/API path | backend target | validation method | result | evidence | risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Overview/Home | `/` | `/api/cockpit/home` | `/api/health`, `/api/cockpit/home/*`, `/api/commentary/recent` | page GET, BFF GET retry, Home tests | PASS with perf note | page 200; BFF 8s timeout then 12s retry 200; Home contract tests passed | retry-sensitive aggregator |
| Chat | `/full-chat` | `/api/cockpit/chat`, `/chat`, `/api/chat` | `cockpit_api.py`, `chat.py`, `tenn_chat.py` | page GET, code/test scan | PARTIAL | page 200; `chat-routing.test.ts` passed; no POST run | runtime answer quality DATA_MISSING |
| Watchlist | `/watchlist` | `/api/cockpit/watchlist` | `/api/cockpit/watchlist*` | page GET, list GET, tests | PASS | page 200; GET 200; route tests passed | add/delete gated |
| Holdings | `/holdings` | `/api/cockpit/holdings` | `/api/cockpit/holdings*` | page GET, list GET retry, tests | PARTIAL | page 200; BFF 8s timeout then 12s retry 200; screen test label assertion failed | local_personal_data must not imply financial truth |
| Marketplace Missions | `/marketplace` | `/api/cockpit/marketplace/missions` | marketplace mission routes | page GET, list GET, tests | PARTIAL | page 200; GET 200; route tests passed; mission screen test button text assertion failed | scans/sync are gated |
| Marketplace Matches | `/marketplace/matches` | `/api/cockpit/marketplace/matches` | marketplace match routes | page GET, list GET, tests | PASS | page 200; GET 200; route tests passed | PATCH/feedback gated |
| Marketplace Alerts | `/marketplace/alerts` | `/api/cockpit/marketplace/alerts` | marketplace alert routes | page GET, list GET, tests | PASS | page 200; GET 200; route tests passed | alert PATCH gated |
| News/RAG | `/news` | `/rag/query` | backend `/rag/query` | page GET, code scan | DATA_MISSING runtime | page 200; code posts to `/rag/query`; POST not run | response provenance not runtime-probed |
| Memory | `/memory` | `/api/cockpit/memory*` | `/api/context/*` | page GET, read-only GETs, code scan | PASS with coordination risk | page 200; tickered memory GETs 200; no writes | unrelated dirty Memory UI/test files appeared |
| Thesis Audit | `/thesis-audit` | `/api/cockpit/thesis-audit*`, proposal routes | `thesis_audit.py`, context proposal routes | page GET, code scan | DATA_MISSING runtime | page 200; POST audit/proposal routes not run | confirmation gates required |
| Verification | `/verification` | `/api/context/verification*`, `/api/extraction-eval/*` | context/extraction eval endpoints | page GET, code scan | PARTIAL | page 200; extraction POSTs deferred | extraction 8001/8002 ambiguity |
| Operations | `/operations` | health/config/action/restart/model routes | `/api/cockpit/*`, ops/action routes | page GET, safe GETs | PARTIAL | page 200; health/config/queue GET 200 | restart/action/model gates |
| Settings | `/settings` | `/api/health`, `/api/cockpit/config`, `/api/cockpit/models` | health/config/model routes | page GET, safe GETs, tests | PARTIAL | page 200; GETs 200; settings test ambiguous text failure | model load gated |
| Boot | `/boot` | `/api/cockpit/health`, llama `/health` | Cockpit health and llama.cpp health | page GET, health GETs | PASS | page 200; backend 200; llama 200; Cockpit health 200 | direct llama health is runtime-bound |
| Intel Pulse | `/intel-ops` | `/api/cockpit/pulse`, `/api/cockpit/matrix` | Cockpit pulse/matrix | page GET, GETs | PASS | page 200; pulse 200; matrix 200 | unavailable tabs remain partial |
| History | `/history` | `/api/cockpit/docs`, `/api/cockpit/queue` | docs/queue/action helpers | page GET, safe GETs | PARTIAL | page 200; docs 200; queue 200 | rerun action gated |

## 5. Page-by-page findings

### Overview/Home

Route ownership: `cockpit-ui/app/page.tsx`, `components/cockpit/home/home-page.tsx`, `app/api/cockpit/home/route.ts`, `lib/cockpit-home-api.ts`, backend `/api/cockpit/home/market-session`, `/home/portfolio`, `/home/attention-queue`, and `/api/commentary/recent`.

Live/mock/static/DATA_MISSING: live BFF aggregator with deterministic DATA_MISSING/degraded handling. Tests assert mock/demo fixtures are not silently source-backed.

Safe GET result: `/` returned 200; `/api/cockpit/home` timed out at 8s once, then returned 200 in 0.015908s with a 12s cap.

Tests found/run: `lib/cockpit-home-api.test.ts` and `lib/cockpit-home-contract.test.ts` ran and passed in the focused 35-test subset.

User-facing risk: transient slow aggregation could make Home look unavailable if a short client timeout is used.

Next safe step: repeat Home BFF timing under a no-code route smoke task and preserve status-code/body-shape only.

### Chat

Route ownership: page `/full-chat`; local legacy `app/chat/route.ts`; backend `financial-engine_v2/backend/app/routes/chat.py`; Cockpit backend `financial-engine_v2/backend/app/routes/cockpit_api.py` `/chat` under `/api/cockpit`; client functions in `lib/api-client.ts`.

Live/mock/static/DATA_MISSING: live/proxied for sessions and chat; runtime answer quality not validated because chat POST was not run.

Safe GET result: page 200. Chat session GETs were discovered but not separately probed.

Tests found/run: `lib/chat-routing.test.ts` and `components/cockpit/chat/sources-drawer.test.tsx` passed in the focused subset; multiple chat component tests were discovered.

User-facing risk: `/api/cockpit/chat`, `/chat`, and `/api/chat` coexist and need ownership mapping to avoid legacy route confusion.

Next safe step: run a separate read-only chat GET/session route pass; POST smoke requires explicit Query Orchestration approval.

### Watchlist/Holdings

Route ownership: `watchlist-screen.tsx`, `holdings-screen.tsx`, Next BFF handlers under `app/api/cockpit/watchlist*` and `holdings*`, backend `cockpit_api.py` watchlist/holdings decorators.

Live/mock/static/DATA_MISSING: live local personal state. Holdings source label is `local_personal_data` in backend/Home contract evidence.

Safe GET result: Watchlist page and GET returned 200. Holdings page returned 200; Holdings BFF timed out once under 8s, then returned 200 under 12s.

Tests found/run: route tests passed for Watchlist. The broader Vitest command failed one Holdings screen assertion because `Cost Basis Known` was not found.

User-facing risk: personal holdings are not canonical financial truth and should remain labeled as local personal data.

Next safe step: fix or update Holdings screen test under a separate Reporting implementation task after ownership is clear.

### Marketplace

Route ownership: pages under `/marketplace`, `/marketplace/matches`, `/marketplace/matches/[matchId]`, `/marketplace/alerts`; BFF handlers under `app/api/cockpit/marketplace/**`; backend marketplace decorators in `cockpit_api.py` and `marketplace_price_intelligence.py`.

Live/mock/static/DATA_MISSING: live/proxied read routes; mutating mission create/update/delete, scan, stop job, benchmark refresh, calibration, eBay sync, match update, benchmark review, alert update are gated.

Safe GET result: Missions, matches, alerts, and browser-health GETs returned 200.

Tests found/run: `lib/marketplace-routes.test.ts` passed; broader command failed one mission screen assertion because the expected `Create Mission` button was not accessible and `Save recurring search` was present.

User-facing risk: browser/eBay/scan routes can touch runtime or external state if clicked.

Next safe step: split marketplace test drift from marketplace route health; only validate scan/sync with explicit operator approval.

### News/RAG

Route ownership: `news-screen.tsx` posts to `/rag/query`; Next rewrite forwards `/rag/:path*` to backend; backend `main.py` owns `/rag/query`.

Live/mock/static/DATA_MISSING: live/proxied by code, but runtime quality is DATA_MISSING because POST query was not run.

Safe GET result: `/news` page 200. No `/rag/query` POST run.

Tests found/run: no focused News test was run.

User-facing risk: source/provenance quality depends on backend response labels and was not validated at runtime.

Next safe step: design a read-only or fixture-backed News provenance test before any live RAG POST probe.

### Memory/Thesis Audit

Route ownership: Memory page and BFF routes under `app/api/cockpit/memory/**` proxy to `/api/context/**`; Thesis Audit uses `lib/api-client.ts` `/api/cockpit/thesis-audit*` and proposal routes.

Live/mock/static/DATA_MISSING: Memory read routes are live with ticker parameters; thesis audit runtime is DATA_MISSING because POST audit/proposal actions were not run.

Safe GET result: `/memory` and `/thesis-audit` pages 200. Untickered `/api/cockpit/memory` and `company-dump` returned 422; tickered `?ticker=BHP` calls returned 200. `/api/cockpit/memory/index` returned 200.

Tests found/run: Playwright memory tests discovered but not run. Unrelated dirty edits appeared in `app/memory/page.tsx`, `memory-screen.tsx`, and `tests/memory.spec.ts`.

User-facing risk: memory writes and thesis proposal apply/confirm/reject need confirmation gates and separate Memory lane ownership.

Next safe step: coordinate or preserve the unrelated Memory dirty work before committing this report.

### Verification/Extraction Eval

Route ownership: `/verification` page; `verification-screen.tsx`; backend `/api/context/verification*`, `/api/extraction-eval/real-gold`, `/api/extraction-eval/confirmed-metric-coverage/*`.

Live/mock/static/DATA_MISSING: page live; eval runtime is DATA_MISSING because POST/background jobs were not run.

Safe GET result: `/verification` page 200. Coverage GETs were not probed in this pass.

Tests found/run: metric coverage component tests discovered but not run.

User-facing risk: extraction eval POST/background jobs can mutate artifacts and consume resources.

Next safe step: separate Evaluation/Financial Truth audit for 8001/8002 ambiguity and extraction eval route safety.

### Settings/Operations/Boot

Route ownership: Settings and Operations pages use `lib/api-client.ts` health/config/models/queue/action/restart routes. Boot probes Cockpit health and direct llama.cpp health.

Live/mock/static/DATA_MISSING: live runtime status; model load, restart, action execute/preview/stop are gated.

Safe GET result: `/settings`, `/operations`, `/boot`, backend `/api/health`, llama `/health`, `/api/cockpit/health`, `/api/cockpit/config`, `/api/cockpit/models`, and `/api/cockpit/queue` returned 200.

Tests found/run: settings screen test was run in the broader command and failed due multiple `Marketplace preferences` text matches.

User-facing risk: settings and operations can mutate runtime through load/restart/action controls.

Next safe step: fix test selector drift separately; keep runtime controls behind operator approval.

### Intel Pulse/History

Route ownership: Intel Pulse page uses `/api/cockpit/pulse` and `/api/cockpit/matrix`; History uses docs/queue and rerun helpers.

Live/mock/static/DATA_MISSING: Pulse/matrix GETs live; some Intel tabs are known unavailable/static from prior and current code scan. History listing live, rerun mutating.

Safe GET result: `/intel-ops`, `/history`, `/api/cockpit/pulse`, `/api/cockpit/matrix?stage=overview`, `/api/cockpit/docs`, and `/api/cockpit/queue` returned 200.

Tests found/run: no focused Intel/History tests were run.

User-facing risk: Intel unavailable tabs can look incomplete; History rerun can mutate jobs.

Next safe step: add a no-code body-shape probe for Pulse/matrix and docs/queue under a future route smoke task.

## 6. Mutating route gate list

See `mutating_route_gate_list.md`. No mutating route was probed.

## 7. Source/provenance findings

Source label semantics are present in backend `cockpit_api.py` as `source_label_semantics_v1`, with labels including `claim_verified`, `context_only`, `no_hit`, `operational_trace`, `local_personal_data`, `local_news_context`, `degraded_runtime`, `missing_required_evidence`, and `unknown_unclassified`.

Home contract code maps DATA_MISSING/degraded/no-hit labels away from verified trust, requires DATA_MISSING reasons, and tests assert degraded/mock fallback is not upgraded to source-backed evidence.

Chat service code normalizes evidence labels and returns degraded/no-hit labels on insufficient context or runtime degradation. Runtime chat source behavior remains DATA_MISSING because no chat POST was run.

Holdings are explicitly local personal data. They must not be presented as canonical financial truth.

Feedback/flags are evaluation artifacts, not truth or training data. Deploy/investigation routes remain gated.

## 8. Validation commands

| command | result | proves | does not prove |
| --- | --- | --- | --- |
| `date -Iseconds` | `2026-05-13T12:41:00+10:00` | run timestamp | later state |
| `pwd` | `/home/l4nd0/tenn` | logical cwd | true git root |
| `git rev-parse --show-toplevel` | `/mnt/hdd-data/home/l4nd0/tenn` | repo root | remote state |
| `git branch --show-current` | `preserve/dirty-work-20260430T065748Z` | branch | remote state |
| `git rev-parse HEAD` | `8beb6bf11f10a401b8a5fbde0be0d54cedc22641` | current HEAD | future drift |
| `git status --short --untracked-files=all` | initially only new task card; later unrelated Memory files modified | dirty state | ownership of unrelated edits |
| `python3 scripts/agent_job_contract.py validate ...` | `ok: true` | task card valid | implementation correctness |
| `python3 scripts/agent_job_registry.py list-active` | initially no active jobs | no registry overlap before claim | unregistered work |
| `python3 scripts/agent_job_registry.py check-overlap ...` | `ok: true` before claim | no registered overlap | unregistered edits |
| `python3 scripts/agent_job_registry.py claim ...` | `ok: true` | claim acquired | future source dirtiness |
| `find cockpit-ui/app -path '*/page.tsx' | wc -l` | `19` | page files exist | page behavior |
| `find cockpit-ui/app -name route.ts | wc -l` | `52` | route handlers exist | route correctness |
| `rg '@(router|app)...' financial-engine_v2/backend/app | wc -l` | `162` | backend decorators exist | mount correctness |
| `ss -ltnp | rg ':(8000|8001|8002|8081|5050|6333|6379)\b'` | 8000, 8001, 8081, 5050, 6333, 6379 listening; no 8002 | local services already running | deep health |
| page GET loop | pages returned 200 | static page reachability | no browser behavior |
| safe BFF/API GET loop | read-only routes mostly 200; first Home/Holdings timed out; untickered memory 422 | route reachability/status | body semantics |
| retry GETs | Home, Holdings, tickered Memory routes returned 200 | retry health | latency under load |
| `pnpm -C cockpit-ui exec vitest run ...` broader focused list | 9 files passed, 3 failed; 63/66 tests passed | current UI test drift exists | production behavior |
| `pnpm -C cockpit-ui exec vitest run lib/... sources-drawer...` | 6 files passed, 35/35 tests passed | selected contracts/routes pass | screens not covered |

## 9. DATA_MISSING

- Chat POST runtime behavior and source envelope.
- News `/rag/query` POST response quality and source labels.
- Thesis Audit POST behavior and proposal mutation behavior.
- Verification extraction eval runtime behavior.
- Dynamic marketplace match detail page for a real match id.
- Browser-based UI behavior; Playwright was not run.
- Extraction runtime 8001/8002 contract reconciliation.
- Current owner of unrelated dirty Memory page/UI/test files.
- Whether broader failed Vitest assertions reflect intentional UI changes or regressions.

## 10. Recommended next steps

Immediate no-code validation:
- Coordinate the unrelated Memory page/UI/test dirty files and rerun `git status`, `check-overlap`, and `check-diff`.
- Repeat status-code-only GET probes with stable timeout and preserve machine-readable output.
- Run selected route/body-shape GET probes for Chat sessions, thesis coverage GET, and extraction coverage GET only if confirmed read-only.

Safe-extension candidates:
- Add a generated route ownership manifest under a report/task artifact path only.
- Add no-code scripts for status-code-only route probes with an explicit mutating denylist.
- Update or split UI tests only after branch/file ownership is clear.

Implementation candidates:
- Fix Holdings screen test drift.
- Fix Marketplace mission screen test drift.
- Fix Settings test selector ambiguity.
- Consider documenting or wrapping rewrite-only Marketplace feedback ownership.

Separate-lane follow-ups:
- Query Orchestration: chat route ownership and POST provenance smoke.
- Provenance: source label contract tests for News/RAG and Chat responses.
- Evaluation/Financial Truth: extraction eval route safety and 8001/8002 runtime ambiguity.
- Memory: thesis proposal confirmation-gate validation and memory deep-link dirty work.

## 11. Project Memory save recommendation

SAVE_RECOMMENDED.

Target categories:
- Validation Baselines: Cockpit route/page GET baseline and focused Vitest results.
- Open Risks / Blockers: unrelated Memory dirty files block commit/check-diff; extraction 8001/8002 ambiguity; UI test drift.
- Repo / GitHub / Codex Audit Notes: Chorus not useful for this route pass; registry claim acquired.
- Active Tasks / Todos: follow-up no-code route smoke, UI test drift fixes, Memory dirty-work coordination.

## 12. Final state

Files written:
- `docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/README.md`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/route_validation_matrix.md`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/mutating_route_gate_list.md`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/status.json`
- `reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/diff-check.json` generated by `check-diff`

Closeout validation:
- `python3 -m json.tool reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/status.json >/dev/null` passed.
- `git diff --check` passed.
- Staged allowlist contained only the task card and this report directory.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md` failed. Part of the failure is the known report-glob limitation for `reports/.../**`, but it also reported unrelated dirty files outside this task: `cockpit-ui/app/memory/page.tsx`, `cockpit-ui/components/cockpit/memory/memory-screen.tsx`, and `cockpit-ui/tests/memory.spec.ts`.
- Commit was not created because the check-diff failure is not only the known report-glob limitation.

Final git status and registry release status are recorded in `status.json`.
