# System / Task / Frontend Wiring Status Audit v1

## 1. Executive summary

### Current repo status

[Confirmed] Git root is `/mnt/hdd-data/home/l4nd0/tenn`; shell `pwd` reported `/home/l4nd0/tenn`, which resolves to the same working tree. Current branch is `preserve/dirty-work-20260430T065748Z` at `5295d5cbd7fcaec626d8a99dd006c4663a682372` (`5295d5cbd7fc`). No upstream was reported by `git rev-parse --abbrev-ref --symbolic-full-name @{u}`.

[Confirmed] `git status --short --untracked-files=all` showed five untracked task-card files before report writing. Four existed before this audit and are outside this task card's allowed files; one is this audit task card.

### Current task/agent status

[Confirmed] `scripts/agent_job_contract.py validate` accepted this task card. `scripts/agent_job_registry.py list-active` returned no active jobs. `check-overlap` and `claim` both failed because the four pre-existing untracked task cards are dirty outside this audit's allowlist. No registry claim was acquired.

### Current frontend wiring status

[Confirmed] Cockpit is a Next.js app under `cockpit-ui/` with 19 page routes and 52 `route.ts` handlers under `cockpit-ui/app`. `next.config.mjs` rewrites `/api/:path*`, `/research/:path*`, and `/rag/:path*` to `NEXT_PUBLIC_API_URL` or `http://localhost:8000`, so frontend calls to backend paths are intentionally proxied when no local BFF handler exists.

[Confirmed] The backend exposes 162 route decorators under `financial-engine_v2/backend/app`. Main Cockpit backend ownership is `financial-engine_v2/backend/app/routes/cockpit_api.py`, mounted at `/api/cockpit`. Source-label semantics are explicitly versioned as `source_label_semantics_v1`.

### Top blockers

1. [Confirmed] Registry claim/check-overlap fail until the four pre-existing untracked task cards are resolved or formally included in a preservation cleanup.
2. [Confirmed] `check-diff` for this task is false because those same four files are outside this audit's allowlist.
3. [Confirmed] Broad Cockpit validation was not run; only lightweight read-only checks and health GETs were run.
4. [Inferred] Several Cockpit controls are live and mutating by design, including restart, model load, action execute, scans, extraction eval runs, marketplace sync, memory writes, and feedback deploy. They were not probed because this was audit-only.

### Recommended next safe step

[Confirmed] Do not start implementation until repo hygiene is settled. The next safe step is a small audit-only or preservation task that decides whether to keep, commit, or remove the four pre-existing untracked task cards, then reruns registry claim/check-overlap and `check-diff`.

## 2. Evidence status legend

- Confirmed: directly observed in command output or current file content.
- Inferred: supported by multiple observations but not directly executed end to end.
- Speculative: plausible but weakly supported.
- DATA_MISSING: not proven or not inspected in this audit.

## 3. Preflight evidence

| Item | Evidence |
| --- | --- |
| Branch / HEAD | [Confirmed] `preserve/dirty-work-20260430T065748Z`, `5295d5cbd7fcaec626d8a99dd006c4663a682372`, short `5295d5cbd7fc`. |
| Worktrees | [Confirmed] `git worktree list` shows a large estate including current `/mnt/hdd-data/home/l4nd0/tenn`, many `/mnt/sdb2/home/l4nd0/tenn-*` worktrees, and several prunable detached worktrees. |
| Git status | [Confirmed] Five untracked task cards before report writing; report files are under an ignored reports area and do not appear in short status. |
| Registry/list-active | [Confirmed] `ok: true`, no active jobs. |
| Task-card validation | [Confirmed] `ok: true`; metadata matched job id, lane, owner, allowed files, output dir, audit-only mode, and `production_data_access: false`. |
| Check-overlap | [Confirmed] `ok: false`; disallowed dirty files are the four pre-existing untracked task cards. |
| Claim | [Confirmed] Claim attempt failed for the same dirty-file reason. |
| Final collision risk | [Confirmed] MEDIUM for report writing only; HIGH would apply to implementation until dirty/task-card state is resolved. |

## 4. Active / recent task status

| job_id | lane | task card | report dir | status | evidence | reviewed? | next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| system_task_frontend_wiring_status_audit_v1_20260513 | Reporting | Present, untracked | Present | In progress/completed by this report | [Confirmed] validation ok | Yes | Review report; resolve dirty task-card blockers |
| cockpit_upgrade_integration_readiness_20260509 | Reporting | Present, untracked | Present | DATA_MISSING | [Confirmed] untracked task card and status artifacts exist | No | Classify/commit/remove in hygiene pass |
| eval_instrumentation_dirty_worktree_audit_20260509 | Evaluation | Present, untracked | Present | DATA_MISSING | [Confirmed] untracked task card and report artifacts exist | No | Classify/commit/remove in hygiene pass |
| news_memo_signal_routing_candidate_fixture_integration_v1 | Memory | Present, untracked | Present | Blocked | [Confirmed] report status artifacts exist; task is untracked | No | Do not implement until Memory lane owner confirms |
| preserve_dirty_state_classification_20260512 | Reporting | Present, untracked | Present | Audit-only/preservation | [Confirmed] task/report artifacts exist | No | Decide if this supersedes or remains open |
| cockpit_home_news_snapshot_c0549d7_source_integration_20260512 | Reporting | Present | Present | Released/integrated | [Confirmed] recent commit and report status exist | Partial | Treat as current only where code matches |
| marketplace_recency_promote_to_target_v1 | Reporting | Present | Present | Blocked | [Confirmed] status artifacts show blocked/closed_blocked variants nearby | No | Re-audit if marketplace implementation resumes |
| metric_extraction_current_state_audit_v1 | Evaluation | Present | Present | Audit report exists | [Confirmed] report files exist | No | Use only as stale evidence unless rerun |

## 5. Dirty/untracked/deleted work classification

| path | status | likely lane | owner/workstream | generated/intentional/stale/DATA_MISSING | blocks what? | recommended treatment | confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md | `??` | Reporting | Claude | DATA_MISSING | Registry claim/check-diff | Preserve or delete via dedicated hygiene task | High |
| docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md | `??` | Evaluation | Claude | DATA_MISSING | Registry claim/check-diff | Preserve or delete via dedicated hygiene task | High |
| docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md | `??` | Memory | Codex | DATA_MISSING; related report blocked | Registry claim/check-diff | Do not touch without Memory lane decision | High |
| docs/agent_tasks/preserve_dirty_state_classification_20260512.md | `??` | Reporting | Codex | DATA_MISSING | Registry claim/check-diff | Decide if it should be committed as preservation record | High |
| docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md | `??` | Reporting | Codex | Intentional for this audit | None if accepted | Commit with reports or keep as audit artifact | High |

No deleted or modified tracked files were observed before report writing.

## 6. Frontend route/tab inventory

| frontend route/tab | primary files | components | BFF/API calls | backend owner route | data mode | tests | risks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/` Overview | `app/page.tsx` | `CockpitHomePage`, home panels/source drawer | `/api/cockpit/home` BFF | `/api/health`, `/api/cockpit/home/*`, `/api/commentary/recent` | Live with explicit DATA_MISSING/demo guard | `cockpit-home-api.test.ts` | Home narrative endpoint missing by design |
| `/full-chat` Chat | `app/full-chat/page.tsx` | `ChatScreen`, source drawer, claim verification | `/api/cockpit/chat`, sessions, config, commentary, feedback | `/api/cockpit/chat`, `/api/cockpit/chat/sessions`, `/api/commentary/*` | Live/proxied | chat component tests exist | Mutating feedback/deploy controls present |
| `/operations` Operations | `operations-screen.tsx` | Job list/detail, GPU card | health/config/action/jobs/restart/model load | `/api/cockpit/*`, `/api/process/ticker/*` | Live and mutating | DATA_MISSING | High operational blast radius; not probed |
| `/updater` Updater | `app/updater/page.tsx` | `UpdaterScreen` | DATA_MISSING from bounded scan | DATA_MISSING | DATA_MISSING | DATA_MISSING | Needs focused route audit |
| `/verification` Verification | `verification-screen.tsx` plus tab panels | review, metric coverage, progress log | `/api/context/verification/*`, `/api/extraction-eval/*`, `/api/cockpit/config` | `context.py`, `main.py` extraction eval | Live/proxied, mutating for eval run | several component tests | Extraction eval POST not run in audit |
| `/history` History | `history-screen.tsx` | document/job history | `listDocuments`, `getQueueStatus`, `rerunJob` | `/api/docs`, `/api/queue/status`, rerun path DATA_MISSING | Live/inferred | DATA_MISSING | Rerun can mutate |
| `/settings` Settings | `settings-screen.tsx` | model/config controls | `/api/health`, `/api/cockpit/config`, models/load | `/api/health`, `/api/cockpit/config`, `/api/cockpit/models/load` | Live/proxied | `settings-screen.test.tsx` | Model load mutates runtime |
| `/news` News | `news-screen.tsx` | news/RAG panel | `/rag/query` | `main.py` `/rag/query` | Live via rewrite | DATA_MISSING | RAG source truth depends on backend response labels |
| `/intel-ops` Intel Pulse | `app/intel-ops/page.tsx` | scope terminal, pipeline ribbon, diagnostic matrix, failure registry | DATA_MISSING from bounded scan | likely `/api/cockpit/pulse`, `/api/cockpit/matrix` | Partial/static/degraded tabs visible | DATA_MISSING | Signals and memory tabs render unavailable states |
| `/holdings` Holdings | `holdings-screen.tsx` | portfolio table/forms | `/api/cockpit/holdings` | `/api/cockpit/holdings` | Live local personal data | `holdings-screen.test.tsx` | Must not be treated as financial truth |
| `/memory` Memory | `memory-screen.tsx` | seven tabs: Company, Sector, Macro, Strategy, Financial Truth, Session, Operational | `/api/cockpit/memory/*` BFF | `/api/context/*` | Live/proxied, mutating add/expire | DATA_MISSING | Memory writes require lane discipline |
| `/thesis-audit` Thesis Audit | `thesis-audit-screen.tsx` | Claims, Contrarian, Proposals, Diligence tabs | api-client thesis audit/proposals | `/api/cockpit/thesis-audit`, `/api/context/thesis/proposals` | Live/proxied | DATA_MISSING | User-thesis memory contamination risk if misused |
| `/watchlist` Watchlist | `watchlist-screen.tsx` | list/add/delete | `/api/cockpit/watchlist` | `/api/cockpit/watchlist` | Live/proxied | watchlist tests | Mutates local watchlist state |
| `/marketplace` Marketplace | `mission-screen.tsx` | mission, price intelligence, scans | marketplace BFF routes | `/api/cockpit/marketplace/*` | Live/proxied | marketplace route/screen tests | Browser/eBay sync are runtime mutating |
| `/marketplace/matches` Matches | `matches-screen.tsx` | match cards/detail controls | `/api/cockpit/marketplace/matches*` | `/api/cockpit/marketplace/matches*` | Live/proxied | matches tests | Feedback call relies on backend rewrite, no local BFF wrapper |
| `/marketplace/matches/[matchId]` Match detail | `match-detail-screen.tsx` | match detail | match detail/update/benchmark-review | `/api/cockpit/marketplace/matches/{id}` | Live/proxied | DATA_MISSING | Same marketplace mutation risk |
| `/marketplace/alerts` Alerts | `alerts-screen.tsx` | alert list/actions | `/api/cockpit/marketplace/alerts*` | `/api/cockpit/marketplace/alerts*` | Live/proxied | alerts test | PATCH mutates alert status |
| `/marketplace-capture` Capture helper | `app/marketplace-capture/page.tsx` | bookmarklet/helper | submit/token BFF | `/api/commentary/ingest-marketplace-snapshot` | Live for submit; local token | helper tests | Captures external marketplace pages |
| `/boot` Boot | `boot-screen.tsx` | startup checks | `/api/cockpit/health`, `http://localhost:8001/health` | backend health, llama.cpp direct | Live/direct runtime probe | DATA_MISSING | Direct LLM health is a frontend boundary exception |

## 7. BFF/API wiring inventory

| BFF/frontend API route | backend endpoint | request/response contract evidence | status | mismatch risk |
| --- | --- | --- | --- | --- |
| `/api/cockpit/home` | aggregates `/api/health`, `/api/cockpit/home/market-session`, `/home/portfolio`, `/home/attention-queue`, `/api/commentary/recent` | `lib/cockpit-home-api.ts`, tests | Live | Low |
| `/api/cockpit/watchlist*` | `/api/cockpit/watchlist*` | route files and backend decorators | Live | Low |
| `/api/cockpit/holdings*` | `/api/cockpit/holdings*` | route files and backend decorators | Live | Low |
| `/api/cockpit/memory*` | `/api/context/*` memory/thesis/company dump | route files and `context.py` | Live | Medium due memory lane |
| `/api/cockpit/commentary/recent`, `/takeaways`, `/marketplace-capture/submit` | `/api/commentary/*` | route files and `commentary.py` | Live | Low |
| `/api/cockpit/commentary/ephemeral-index*` | none | local route returns unavailable | Not live | Medium if UI exposes it as capability |
| `/api/cockpit/action/*` | `/api/cockpit/action/*` | route files and backend decorators | Live/mutating | High |
| `/api/cockpit/claims/verify` | `/api/cockpit/claims/verify` | route file and `cockpit_claims.py` | Live | Medium |
| `/api/cockpit/feedback/*` | `/api/cockpit/feedback*` plus local Codex deploy/investigation | route files and tests | Mixed live/local | High for deploy |
| `/api/cockpit/marketplace/*` | `/api/cockpit/marketplace/*` | route files and backend decorators | Live/mutating | High for scans/sync |
| `/api/cockpit/metrics/gpu`, `/metrics/host` | local Next probes/backend health overlap | route files | Live/local | Medium |
| `/api/cockpit/restart` | local process restart script | route file | Live/mutating | High |
| `/chat` | backend `/chat` | `app/chat/route.ts`, backend duplicate chat include | Legacy live | Medium |
| `/cockpit-local/feedback/flags/*` | reexports local deploy/investigation handlers | alias route files | Local/mutating | High |

## 8. Backend route inventory relevant to Cockpit

| backend route | service owner | frontend consumers | tests | provenance/source-label behavior | status |
| --- | --- | --- | --- | --- | --- |
| `/api/cockpit/health`, `/config`, `/models`, `/queue`, `/docs` | Cockpit API/service/runtime | Settings, Boot, Operations, Chat, Verification | partial screen tests | health includes runtime dependencies | Live |
| `/api/cockpit/chat`, `/chat`, `/api/chat` | `CockpitService`, legacy chat router | Chat and legacy route | chat tests present | source labels and routing metadata in `cockpit_api.py` and `tenn_chat.py` | Live with duplicate route surface |
| `/api/cockpit/chat/attachments/upload` | Cockpit API | Chat upload | DATA_MISSING | attachment metadata only | Live |
| `/api/cockpit/watchlist`, `/holdings` | Cockpit state store | Watchlist/Holdings/Home portfolio | component/route tests | holdings marked `local_personal_data` | Live |
| `/api/context/*` | context/memory services | Memory, Verification, Thesis | DATA_MISSING | memory and verification records | Live/proxied |
| `/api/commentary/*` | commentary services | Home, Chat, News/source drawer, Capture helper | DATA_MISSING | local news/commentary context labels where consumed | Live/proxied |
| `/rag/query` | RAG service | News | DATA_MISSING | backend response DATA_MISSING unless inspected deeper | Live/proxied |
| `/api/extraction-eval/*` | extraction eval services | Verification | DATA_MISSING | financial truth boundary | Live, not run |
| `/api/cockpit/marketplace/*` | marketplace mission/price services | Marketplace pages | route/screen tests | operational/marketplace data, not financial truth | Live/mutating |
| `/api/cockpit/feedback/*` | Cockpit feedback service | Chat feedback and flagged reports | codex investigation route tests | feedback is evaluation artifact, not truth | Live/mutating |
| `/api/ops/*` | ops API | Operations job panels | DATA_MISSING | operational artifacts only | Live |

## 9. Page-by-page Cockpit UX/wiring notes

### Overview

[Confirmed] Intended purpose is an analyst home surface. Actual path is `GET /api/cockpit/home` to a BFF aggregator. Live sections are market session, portfolio, recent commentary/news snapshot, and attention queue. Mock/demo fixtures exist but are explicitly labeled dev/demo and not source-backed. Loading/error/DATA_MISSING states are visible in code and tests. Missing backend narrative endpoint is surfaced as `NO_HOME_NARRATIVE_ENDPOINT`.

### Chat

[Confirmed] Intended purpose is source-aware chat with sessions, attachments, source drawer, verification, feedback, and marketplace capture helpers. Actual data path is mostly `/api/cockpit/chat*` through rewrite or BFF. Live parts include sessions, chat stream, commentary takeaways, URL ingest, marketplace inspect, feedback flag, local investigation/deploy. Risk is user-facing controls that can write feedback artifacts or spawn local Codex investigations.

### Operations

[Confirmed] Intended purpose is operational job execution and runtime control. It calls health, action preview/execute/jobs, restart, and model load paths. Loading/error states are local stateful UI. Risk is high if clicked; no mutating controls were probed.

### Verification

[Confirmed] Intended purpose is extraction verification and metric coverage. It calls context verification runs and extraction eval endpoints. Some controls POST background eval jobs. Empty/loading/degraded states are present in tab panels. Risk is financial truth and extraction workload mutation.

### History

[Confirmed] Intended purpose is document/job history from `listDocuments` and queue status. Re-run action exists. Risk is mutation through rerun.

### Settings

[Confirmed] Intended purpose is backend/model/runtime preferences. It reads `/api/health`, `/api/cockpit/config`, and model list; it can load a Cockpit model. Risk is runtime mutation through model load.

### News

[Confirmed] Intended purpose is RAG-backed news query. It calls `/rag/query`, which Next rewrites to backend `/rag/query`. Risk is source/provenance clarity depending on backend response labels; no POST probe was run.

### Intel Pulse

[Confirmed] UI tabs include overview, extraction, evaluation, signals, memory, failures. Signals and memory tabs explicitly render unavailable messages. Runtime data paths were not fully traced in this audit.

### Holdings and Watchlist

[Confirmed] Holdings and watchlist use `/api/cockpit/holdings*` and `/api/cockpit/watchlist*`. Holdings source label is `local_personal_data` in backend models and Home BFF tests. Risk is overstating personal portfolio records as financial truth.

### Memory and Thesis Audit

[Confirmed] Memory has Company, Sector, Macro, Strategy, Financial Truth, Session, and Operational tabs. Thesis Audit has Claims, Contrarian, Proposals, and Diligence tabs. Data paths are `/api/context/*` and `/api/cockpit/thesis-audit*`. Risk is memory writes or thesis proposals without confirmation discipline.

### Marketplace

[Confirmed] Marketplace pages are live-wired to missions, scans, matches, alerts, browser health, price intelligence, benchmark refresh, eBay sync, and feedback. Some operations are explicitly mutating and runtime/browser dependent. Match feedback uses backend `/api/cockpit/marketplace/matches/{match_id}/feedback`; there is no local BFF wrapper, but the Next rewrite makes it reachable.

### Boot and Capture Helper

[Confirmed] Boot directly probes llama.cpp at `http://localhost:8001/health` plus Cockpit health. Marketplace capture creates a helper URL to `/api/cockpit/commentary/marketplace-capture/submit`. Risk is frontend direct runtime visibility and external page capture semantics.

## 10. Source/provenance/evidence behavior

[Confirmed] `cockpit_api.py` defines `SOURCE_LABEL_TAXONOMY_VERSION = "source_label_semantics_v1"` and labels including `claim_verified`, `context_only`, `no_hit`, `operational_trace`, `local_personal_data`, `local_news_context`, `degraded_runtime`, `missing_required_evidence`, and `unknown_unclassified`.

[Confirmed] Home contract code maps DATA_MISSING and degraded labels to non-verified trust levels. Tests assert no mock fallback source-backing and local personal data handling.

[Confirmed] Chat backend normalizes evidence labels, records source label counts, and avoids treating no-hit/degraded sources as verified. DATA_MISSING remains for deeper runtime behavior because no chat POST was run.

## 11. Runtime/dependency/port map

| surface | evidence | verified vs inferred |
| --- | --- | --- |
| Frontend Cockpit | [Confirmed] `cockpit-ui/package.json`; `ss` shows `*:8081` Next server | GET health verified through frontend |
| Backend | [Confirmed] README and `run_local_backend.sh`; `ss` shows `:8000`; `/api/health` returned `{"status":"ok"}` | Verified |
| LLM runtime | [Confirmed] Boot/settings code use `:8001`; `ss` shows llama-server; `/health` returned ok | Verified |
| Extraction runtime | [Confirmed] docs/scripts mention separate/deprecated `:8002`; no `:8002` listener found | DATA_MISSING/current contract conflicting |
| Qdrant | [Confirmed] `ss` shows `:6333`; Cockpit health reported healthy | Verified by Cockpit health only |
| Redis | [Confirmed] `ss` shows `:6379`; Cockpit health reported healthy | Verified by Cockpit health only |
| Chorus | [Confirmed] `ss` shows `127.0.0.1:5050`; GET returned HTML | Verified |

## 12. Validation matrix summary

### Checks run with exact outputs

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md`: [Confirmed] `ok: true`.
- `python3 scripts/agent_job_registry.py list-active`: [Confirmed] `ok: true`, active jobs empty.
- `python3 scripts/agent_job_registry.py check-overlap ...`: [Confirmed] `ok: false`, blocked by four pre-existing untracked task cards.
- `python3 scripts/agent_job_registry.py claim ...`: [Confirmed] failed for the same dirty files; no claim acquired.
- `git diff --check`: [Confirmed] no output, exit 0.
- `python3 scripts/agent_job_contract.py check-diff ...`: [Confirmed] `ok: false`, disallowed files are the same four pre-existing untracked task cards.
- `curl http://127.0.0.1:8000/api/health`: [Confirmed] `{"status":"ok"}`.
- `curl http://127.0.0.1:8001/health`: [Confirmed] `{"status":"ok"}`.
- `curl http://127.0.0.1:8081/api/cockpit/health`: [Confirmed] returned healthy services including backend, llama.cpp, ollama, qdrant, redis, cockpit_service.
- `curl http://127.0.0.1:5050`: [Confirmed] returned Chorus/Next HTML.

### Checks not run and why

[Confirmed] Vitest, Playwright, pytest suites, typecheck, migrations, ingestion, extraction jobs, Qdrant syncs, and POST probes were not run because the task is audit-only and the registry/check-diff state is already blocked by unrelated dirty task cards.

### Stale validation evidence

[Confirmed] Many report directories contain prior status artifacts. [Inferred] They are useful as history but not current truth unless rerun against this HEAD.

### Recommended next validation pass

After dirty task-card cleanup: `check-overlap`, `claim`, `check-diff`, `pnpm -C cockpit-ui test -- --runInBand` if supported or selected Vitest files, `pnpm -C cockpit-ui lint`, selected backend pytest collection, then targeted route contract tests.

## 13. Risks and blockers

| severity | risk | evidence | impacted lane/surface | likely root cause or DATA_MISSING | next safe step | hard stop |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | Registry/check-diff blocked | Four untracked task cards outside allowlist | All implementation lanes | Stale or unpreserved task-card state | Resolve dirty task cards | Yes for implementation |
| P1 | Mutating Cockpit controls are visible and live | Operations, Verification, Marketplace, Memory, Settings routes | Reporting/Evaluation/Memory | Product capability exists; audit did not click | Gate future tests carefully | Yes for audit-only |
| P1 | Extraction runtime contract ambiguous | Docs/scripts mention 8002 but current health uses 8001 and no 8002 listener | Financial Truth/Evaluation | Runtime migration in progress | Run dedicated extraction runtime audit | No for report |
| P1 | Feedback deploy/investigation can spawn local processes | BFF deploy/investigation route files and tests | Evaluation/Reporting | Local debug tooling exposed to UI | Require explicit operator gate | No |
| P2 | Legacy and Cockpit chat routes coexist | `main.py` mounts `chat_router` at `/chat` and `/api/chat`, plus `/api/cockpit/chat` | Query Orchestration | Backward compatibility | Contract audit before removal | No |
| P2 | Direct/proxy mixed API style can obscure ownership | Next rewrites plus local BFF routes | Reporting | Hybrid BFF/proxy architecture | Document route ownership in generated map | No |
| P2 | Personal holdings can be mistaken for financial truth | `local_personal_data` labels and holdings UI | Financial Truth/Reporting | UI combines portfolio and market surfaces | Preserve source labels in all views | No |
| P3 | Many stale reports/task cards remain | 52 task cards and 27 status files found | Repo hygiene | Multi-agent history | Consolidate task matrix | No |

## 14. Recommended next safe steps

1. [Confirmed] Audit-only follow-up: classify the four pre-existing untracked task cards and decide keep/commit/remove.
2. [Confirmed] Safe-extension candidate after cleanup: add or refresh a machine-readable route ownership manifest generated from current routes.
3. [Inferred] Implementation candidate after validation: align Marketplace match feedback with either an explicit local BFF wrapper or documented rewrite-only ownership.
4. [Inferred] Cleanup/hygiene candidate: consolidate stale report/task card status and mark superseded prompts.
5. [Inferred] Validation candidate: run selected Cockpit route tests, Home tests, Marketplace tests, Watchlist/Holdings tests, and backend route import collection.

## 15. Project Memory save recommendation

SAVE_RECOMMENDED.

Target categories:

- Active Tasks / Todos: registry/check-diff blocked by four untracked task cards.
- Open Risks / Blockers: extraction runtime 8001/8002 ambiguity; mutating Cockpit controls.
- Repo / GitHub / Codex Audit Notes: branch, HEAD, route counts, BFF/proxy ownership.
- Validation Baselines: lightweight checks and health probe results from 2026-05-13.
- Milestones: not applicable.

## 16. Final state

| Item | State |
| --- | --- |
| Final git status | [Confirmed] expected to include the five untracked task cards; report dir is ignored by git status. |
| Files written by this audit | `docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md`; report files under `reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/`. |
| Registry claim released | DATA_MISSING/not applicable: claim was never acquired because claim failed. |
| Task-card check-diff result | [Confirmed] `ok: false`, blocked by four pre-existing untracked task cards outside allowlist. |
| DATA_MISSING list | Full semantic contract tests, full endpoint response schemas, actual UI screenshots, all stale report reviews, extraction runtime migration status, current ownership intent for four untracked task cards. |
