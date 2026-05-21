# Route Parity Home / News Status Audit

## Verdict

`/api/cockpit/home`: frontend BFF route intentionally owns this path. The direct backend aggregate route is intentionally absent in this branch/profile.

`/api/news/status`: intentionally absent in this branch/profile. Current inspected news retrieval uses `/rag/query`; no current frontend/backend call site requires `/api/news/status`.

This is not a storage migration blocker. The current gap is stale route expectation/docs-smoke drift unless a new product contract explicitly asks for compatibility endpoints.

## Preflight

- Worktree used: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `/home/l4nd0/tenn` is currently a dangling symlink to `/mnt/hdd-data/home/l4nd0/tenn`; `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- HEAD: `8e38d26725e3`.
- `git status --short` after card creation: `?? docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`.
- `git worktree list`: many sibling worktrees exist. Relevant entries include current `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` at `8e38d267` and old preserve `/mnt/sdb2/home/l4nd0/tenn` at `c102f3f2`.
- Recent commits: current HEAD `8e38d267 feat(financial-truth): add asx document type sidecar artifacts`; route-parity contract guard exists in history at `03d1fa42 test(evaluation): lock nvme2 route parity expectations`.

## Task Card / Registry

- Created `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`.
- Task card mode: `audit_only`; production data access: `false`; allowed files limited to the task card and this report directory.
- Added `allow_audit_code_changes: true` because this repo's `check-diff` gate otherwise rejects even allowed audit/report artifacts.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`: PASS.
- `.tenn/active_agent_task`: absent.
- `python3 scripts/agent_job_registry.py list-active`: PASS, `active_jobs=[]`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md --repo-root /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`: PASS, no issues.
- Collision risk: LOW for this audit/report. MEDIUM only if a later task implements backend compatibility routes.

## Confirmed

- Backend route registration mounts `cockpit_api_router` under `/api/cockpit` in `financial-engine_v2/backend/app/main.py`.
- Backend `financial-engine_v2/backend/app/routes/cockpit_api.py` registers these Home section subroutes:
  - `/api/cockpit/home/market-session`
  - `/api/cockpit/home/attention-queue`
  - `/api/cockpit/home/market-movers`
  - `/api/cockpit/home/narrative`
  - `/api/cockpit/home/portfolio`
- Backend does not register direct `/api/cockpit/home` or `/api/news/status` in current route inventory.
- `financial-engine_v2/backend/tests/test_route_parity_contract.py` asserts `/api/cockpit/home` and `/api/news/status` are absent and return 404, while the five Home backend subroutes are present.
- Next.js owns same-origin `/api/cockpit/home` via `cockpit-ui/app/api/cockpit/home/route.ts`.
- `cockpit-ui/lib/cockpit-home-api.ts` builds the BFF response by calling backend `/api/health`, `/api/cockpit/home/*` subroutes, and `/api/commentary/recent?limit=5`.
- `cockpit-ui/components/cockpit/home/home-page.tsx` fetches `/api/cockpit/home` from the browser.
- Current code search found no frontend/backend call site for `/api/news/status`.
- Cockpit News UI searches news with `POST /rag/query` and `source: "news"`.
- Project venv TestClient route inventory returned `/api/cockpit/home status=404` and `/api/news/status status=404`.
- Focused backend route parity test passed: `2 passed, 5 warnings`.

## Inferred

- A backend-direct `/api/cockpit/home` expectation is stale if it treats the public same-origin BFF path as a FastAPI aggregate route.
- `/api/news/status` is not required by current branch/profile behavior; route checks expecting it are stale unless a product owner defines a new status payload.
- Home `PARTIAL` / `DATA_MISSING` remains the intended honesty model for missing/deferred producers; removing that would be a regression.

## Speculative

- A backend aggregate `/api/cockpit/home` compatibility endpoint could be built later, but it would duplicate BFF aggregation and needs an explicit compatibility contract.
- `/api/news/status` could be useful as an operator health endpoint, but no inspected current caller requires it and semantics are undefined.

## DATA_MISSING

- Current live listener smoke is DATA_MISSING: `ss -ltnp | rg ':(8000|8081|3000|3001)\b'` found no listeners, and passive curls to `127.0.0.1:8000` and `127.0.0.1:8081` returned connection refused. I did not start services because code/TestClient evidence was sufficient and no runtime mutation was needed.
- Current frontend Vitest validation is DATA_MISSING: `pnpm --dir cockpit-ui exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts` was blocked by `/bin/bash: pnpm: command not found`. `corepack`, `npm`, and `node v22.22.0` are present, but I did not activate/install package tooling.
- I did not inspect DBs, Qdrant, news stores, Docker volumes, systemd services, model config, CUDA/M40 runtime, parser/extraction surfaces, generated sidecars, canonical truth, or production data.

## Route Ownership Map

| Route | Owner | Evidence | Classification | Gap verdict |
| --- | --- | --- | --- | --- |
| `/api/cockpit/home` | Next.js BFF in `cockpit-ui/app/api/cockpit/home/route.ts` | BFF route exists; Home page fetches it; backend TestClient 404 | frontend BFF route intentionally owns this path | No issue for current contract; stale expectation if checked as backend route |
| `/api/cockpit/home/market-session` | Backend `cockpit_api.py` | Registered under `/api/cockpit` | backend section subroute | Required BFF upstream |
| `/api/cockpit/home/attention-queue` | Backend `cockpit_api.py` | Registered under `/api/cockpit` | backend section subroute | Required BFF upstream |
| `/api/cockpit/home/market-movers` | Backend `cockpit_api.py` | Registered under `/api/cockpit` | backend section subroute | Required BFF upstream |
| `/api/cockpit/home/narrative` | Backend `cockpit_api.py` | Registered under `/api/cockpit` | backend section subroute | Required BFF upstream |
| `/api/cockpit/home/portfolio` | Backend `cockpit_api.py` | Registered under `/api/cockpit` | backend section subroute | Required BFF upstream |
| `/api/news/status` | None in current branch/profile | No code call site; backend TestClient 404; route parity test asserts absent | intentionally absent in this branch/profile | No issue unless a new product/status contract is approved |
| `/rag/query` | Backend `app.main` | Registered POST route; News UI uses `source: "news"` | current news retrieval surface | Existing route, not a status route |
| `/api/commentary/recent` | Backend commentary route consumed by BFF | Home BFF calls it for Home news/commentary panel | current Home news input | Existing route |

## Route Classifications

`/api/cockpit/home`: **frontend BFF route intentionally owns this path**.
Gap type: stale expectation if backend route discovery expects a direct FastAPI aggregate endpoint. Not a blocker.

`/api/news/status`: **intentionally absent in this branch/profile**.
Gap type: stale expectation/docs-smoke drift if any smoke still expects the route. Not a blocker.

## Blocker / Completeness Assessment

- Storage migration blocker: NO.
- Product completeness issue: NO for current inspected route contract.
- Stale expectation: YES for direct backend `/api/cockpit/home` checks and `/api/news/status` checks.
- No issue: YES for current normal route ownership, provided callers keep using BFF Home and `/rag/query` for news retrieval.

## Implementation Risk

- Recommended docs/tests/smoke expectation cleanup: LOW.
- Implementing backend `/api/cockpit/home`: MEDIUM. It touches contested backend route surfaces and risks duplicating BFF aggregation semantics.
- Implementing `/api/news/status`: MEDIUM. It requires new status semantics and may overlap Query Orchestration/news health surfaces.

## Files / Reports Inspected

- `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260519.md`
- `docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_route_parity_contract.py`
- `cockpit-ui/app/api/cockpit/home/route.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/components/cockpit/news/news-screen.tsx`
- `reports/agent_jobs/nvme2_route_contract_frontend_smoke_final_v1_20260518/README.md`
- `reports/agent_jobs/nvme2_route_parity_followup_audit_v1_20260518/README.md`
- `reports/agent_jobs/nvme2_route_parity_followup_audit_v1_20260518/followup_plan.md`
- `reports/agent_jobs/route_parity_home_news_status_audit_v1_20260519/README.md`
- `reports/agent_jobs/nvme_runtime_audit_artifact_checkpoint_v1_20260519/README.md`

## Commands / Results

- `pwd`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- `git branch --show-current`: `migration/clean-runtime-baseline-reconstruct-v1`.
- `git rev-parse --short=12 HEAD`: `8e38d26725e3`.
- `git log --oneline -20`: current HEAD plus route history including `03d1fa42 test(evaluation): lock nvme2 route parity expectations`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`: PASS.
- `python3 scripts/agent_job_registry.py list-active`: PASS, no active jobs.
- `python3 scripts/agent_job_registry.py check-overlap ...`: PASS, no issues.
- `rg -n "api/cockpit/home|/api/cockpit/home|cockpit/home|CockpitHome|buildCockpitHomeBffResponse|api/news/status|/api/news/status|news/status" ...`: found Home BFF/backend subroute/tests/reports; only current `/api/news/status` code hits were in route parity test assertions.
- `PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 financial-engine_v2/.venv/bin/python - <<'PY' ...`: listed registered interesting routes as the five backend Home subroutes, `/api/health`, and `/rag/query`; TestClient returned 404 for `/api/cockpit/home` and `/api/news/status`.
- `PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 financial-engine_v2/.venv/bin/pytest -q financial-engine_v2/backend/tests/test_route_parity_contract.py`: PASS, `2 passed, 5 warnings`.
- `ss -ltnp | rg ':(8000|8081|3000|3001)\b' || true`: no usual backend/frontend listeners found.
- Passive curl probes to `http://127.0.0.1:8000/api/cockpit/home`, `http://127.0.0.1:8000/api/news/status`, and `http://127.0.0.1:8081/api/cockpit/home`: connection refused / HTTP `000`; no services were started.
- `pnpm --dir cockpit-ui exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`: BLOCKED, `pnpm: command not found`.

## Recommended Next Safe Step

Do not implement either route. Open a small docs/tests/smoke-expectation cleanup only if a current smoke or doc still treats backend `/api/cockpit/home` or `/api/news/status` as required. Scope that follow-up to route-contract docs/tests only, preserving:

- frontend `/api/cockpit/home` as BFF-owned;
- backend `/api/cockpit/home/*` section subroutes;
- `/api/news/status` absent unless a new product status contract is approved;
- `PARTIAL` / `DATA_MISSING` honesty.

If product wants compatibility endpoints, create a separate safe-extension task card with explicit allowed source files and payload semantics before implementation.

## Final Git Status

- Final `python3 scripts/agent_job_contract.py validate docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`: PASS.
- Final `python3 scripts/agent_job_registry.py list-active`: PASS, `active_jobs=[]`.
- Final `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md --repo-root /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`: PASS, no issues.
- Final `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`: PASS, no disallowed files.
- Final `git diff --check`: PASS.
- Final `git status --short`: `?? docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md`.
- Final `git status --short --ignored docs/agent_tasks/route_parity_home_news_status_audit_v1_20260521.md reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521`: task card untracked; report directory ignored as `!! reports/agent_jobs/route_parity_home_news_status_audit_v1_20260521/`.
- Report directory files: `README.md`, `diff-check.json`.

## Project Memory Save Recommendation

SAVE_RECOMMENDED: persist that at `migration/clean-runtime-baseline-reconstruct-v1` HEAD `8e38d26725e3`, route parity remains resolved as BFF-owned `/api/cockpit/home`, backend-owned Home section subroutes, and intentionally absent `/api/news/status`; this audit did not start runtime services and did not touch source/data/runtime surfaces.
