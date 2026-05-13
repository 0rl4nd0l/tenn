# Risk Register

| severity | risk | evidence | owner lane | next safe step |
| --- | --- | --- | --- | --- |
| P0 | Registry and `check-diff` are blocked by dirty files outside this task's allowlist. | `check-overlap`, `claim`, and `check-diff` all failed on four untracked task cards. | Reporting/Evaluation/Memory | Resolve task-card hygiene before implementation. |
| P1 | Cockpit contains live mutating controls that were not exercised in audit-only mode. | Operations restart/model load/action execute; Verification eval POST; Marketplace scans/sync; Memory add/expire; feedback deploy. | Reporting plus owning backend lanes | Use explicit task card and guarded validation before clicking or testing POST paths. |
| P1 | Extraction runtime contract appears ambiguous. | `ss` shows no `:8002`; Cockpit health reports llama.cpp `:8001`; scripts/docs still mention separate extraction runtime. | Financial Truth/Evaluation | Dedicated extraction runtime reconciliation audit. |
| P1 | Feedback deploy/investigation route can spawn local Codex work from UI. | `app/api/cockpit/feedback/flags/[reportId]/deploy/route.ts` and `cockpit-local` aliases. | Evaluation/Reporting | Require operator confirmation and clear UI state before use. |
| P2 | Chat has duplicate legacy and Cockpit route surfaces. | `main.py` mounts `/chat` and `/api/chat`; Cockpit adds `/api/cockpit/chat`. | Query Orchestration | Keep compatibility map; avoid unplanned removal. |
| P2 | Rewrite-only backend ownership can be confused with missing BFF routes. | `next.config.mjs` rewrites `/api`, `/research`, `/rag`; several pages call backend paths directly. | Reporting | Document route ownership; test representative rewrite paths. |
| P2 | Holdings/local personal data can be visually adjacent to financial truth. | Backend and Home BFF use `local_personal_data`; Holdings and Home portfolio surfaces are live. | Reporting/Financial Truth | Preserve source labels and avoid using holdings as canonical financial truth. |
| P2 | Source labels could be overstated if future code bypasses taxonomy. | Current taxonomy is present, but many surfaces consume sources. | Provenance/Query Orchestration | Add contract tests for new surfaces. |
| P2 | Marketplace browser and eBay sync routes can run external/runtime jobs. | Backend decorators and BFF routes for scans, calibration, eBay sync. | Reporting/Provenance | Audit-only validation should use GET health only unless authorized. |
| P3 | Stale reports/task cards create planning noise. | 52 task cards and 27 status files found. | Reporting/Evaluation | Consolidate stale/superseded status matrix. |
| P3 | Intel Pulse has unavailable tabs. | `SIGNALS_UNAVAILABLE`, `MEMORY_UNAVAILABLE` visible in code. | Reporting | Label as partial until wired or hide behind capability state. |
| P3 | Home still has explicit demo fixtures. | Home UI and tests label mock/demo as not source-backed. | Reporting | Keep tests preventing silent mock fallback. |

