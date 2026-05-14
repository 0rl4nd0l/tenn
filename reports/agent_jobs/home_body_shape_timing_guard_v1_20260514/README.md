# Home Body Shape Timing Guard

## Verdict

passed with caveats

The `/api/cockpit/home` endpoint is reachable, fast, structurally stable, and honest about partial data. Home implementation and polish may proceed only while preserving the current explicit `PARTIAL` / `DATA_MISSING` semantics and local-data trust labels.

## Branch / HEAD / Worktree

- Branch: `fast/dev-storage-v1-20260513-170304`
- Preflight HEAD: `9698520db2c8`
- Closeout commit: this report is included in the milestone commit that contains this file.
- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Lane: Reporting
- Execution mode: SAFE EXTENSION
- Collision risk: MEDIUM

## Runtime Quick Health

- `http://127.0.0.1:8000/api/health`: `{"status":"ok"}`
- `http://127.0.0.1:8001/health`: `{"status":"ok"}`
- `http://127.0.0.1:8081/api/cockpit/health`: `status:"healthy"` with backend, llama.cpp, Ollama, Qdrant, Redis, Cockpit service, GPU, and host reported healthy

## Home Endpoint Timing

- Command: `curl -m 30 -sS -w '\nHTTP %{http_code} time %{time_total}\n' http://127.0.0.1:8081/api/cockpit/home`
- Result: `HTTP 200 time 0.015430`
- Recommended guard threshold: fail live timing only above `1000ms` for this local runtime; keep the hard request timeout at `30000ms`.

## Body Shape Summary

Observed required top-level fields:

- `ok:true`
- `generated_at:"2026-05-14T07:21:00.616Z"`
- `source_label_taxonomy_version:"source_label_semantics_v1"`
- `data_state:"PARTIAL"`
- `degraded:false`
- `data_missing:[...]`
- `market_session:{...}`
- `portfolio:{...}`
- `market_movers:[]`
- `news:[]`
- `attention_queue_state:{...}`
- `attention_queue:[]`
- `data_health:[...]`
- `narrative:{...}`

## Observed State

- `data_state`: `PARTIAL`
- `degraded`: `false`
- `as_of`: `2026-05-14T07:21:00.626483+00:00`
- Contract caveat: `degraded:false` is acceptable here because `data_state:"PARTIAL"` and `data_missing` explicitly enumerate missing sections.

## Missing Sections

- Recent commentary: missing, represented by `NO_RECENT_COMMENTARY` with `source_label:"no_hit"`.
- Market-update signals: missing, represented by `NO_MARKET_UPDATE_SIGNALS` with `source_label:"no_hit"`.
- Narrative producers: missing, represented by:
  - `NO_SESSION_SUMMARY_ENDPOINT`
  - `NO_THEME_CANDIDATES_ENDPOINT`
  - `NO_TOMORROW_PREP_ENDPOINT`
- Attention queue: present and empty as `READY`, `0 queued`, no missing signal.
- Portfolio/holdings: present as `READY`, `source_label:"local_personal_data"`, zero holdings.
- Market session/data health: present as `READY`, ASX `POST_MARKET`, next event `ASX open`.
- Source drawer inputs: no resolvable news/source-bearing rows were present in the live payload; missing/operational rows did not claim `claim_verified` or `financial_truth`.

## Trust / Source-Label Observations

- Local holdings remain labelled `local_personal_data`, not canonical financial truth.
- Missing commentary and market-update data use `no_hit`, not verified source labels.
- Missing narrative producers use `missing_required_evidence`.
- Empty source-bearing arrays are not silently rendered as complete; they are represented through `data_missing` and `data_health`.
- The guard blocks unresolved source-bearing items from looking source-backed by checking `claim_verified` and `financial_truth` are absent when evidence is unresolved or missing.

## Tests Added / Updated

- Added `cockpit-ui/lib/cockpit-home-live-shape.test.ts`.
- The test is live-optional and skipped unless `COCKPIT_HOME_LIVE_SHAPE=1` is set.
- No Home product UI, backend route, BFF behavior, QueryOrchestrator, source-label logic, memory, Qdrant, Postgres, news, extraction, or model data was changed.

## Validation Results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/home_body_shape_timing_guard_v1_20260514.md`: passed
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/home_body_shape_timing_guard_v1_20260514.md`: passed, no overlap issues
- Runtime health on `:8000`, `:8001`, `:8081`: passed
- Live Home curl: passed, `HTTP 200 time 0.015430`
- `pnpm -C cockpit-ui exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`: passed, 2 files / 18 tests
- `COCKPIT_HOME_LIVE_SHAPE=1 pnpm -C cockpit-ui exec vitest run lib/cockpit-home-live-shape.test.ts`: passed, 1 file / 1 test
- `pnpm -C cockpit-ui exec tsc --noEmit`: passed
- `git diff --check` and `git diff --cached --check`: passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/home_body_shape_timing_guard_v1_20260514.md`: passed, no disallowed files
- `python3 scripts/agent_job_registry.py release home_body_shape_timing_guard_v1_20260514`: passed

## Files Changed

- `docs/agent_tasks/home_body_shape_timing_guard_v1_20260514.md`
- `cockpit-ui/lib/cockpit-home-live-shape.test.ts`
- `reports/agent_jobs/home_body_shape_timing_guard_v1_20260514/README.md`
- `reports/agent_jobs/home_body_shape_timing_guard_v1_20260514/status.json`
- `reports/agent_jobs/home_body_shape_timing_guard_v1_20260514/diff-check.json`

## Files Intentionally Not Touched

- Home product/UI implementation files
- Backend route behavior
- BFF implementation behavior
- QueryOrchestrator
- Source-label/provenance implementation
- Memory cleanup and `company_memory.sqlite`
- Qdrant/Postgres/news/extraction/model data
- Docker/runtime startup scripts

## Final Git Status

- After release and before amend: `M reports/agent_jobs/home_body_shape_timing_guard_v1_20260514/status.json`
- This status update was folded into the final commit.
- Final tracked/untracked status after amend is expected to be clean.

## Active Registry State

- This job was released successfully.
- Immediate post-release `list-active` returned `active_jobs: []`.
- Later post-commit shared registry state contained one unrelated Evaluation audit in `/home/l4nd0/tenn-process-document-rag-guardrails-audit-v1-20260514`.
- No active job overlapped this task card's allowed files.

## May Home Implementation Proceed?

Yes, with caveats. Product implementation may proceed only if it keeps `PARTIAL` and missing producer states visible, keeps local portfolio data labelled as local personal data, and does not upgrade missing or operational evidence into source-backed financial truth.

## Recommended Next Task

Create a bounded Reporting/Provenance task to implement or wire the missing Home narrative/commentary/market-update producers, or explicitly decide they remain absent in v1 with persistent UI copy and tests that keep the missing state visible.

## Project Memory Save Recommendation

Save this as the current Home contract guard baseline for `/api/cockpit/home` on the NVMe runtime: HTTP 200 in `0.015430s`, `data_state:"PARTIAL"`, `degraded:false`, with missing commentary, market-update signals, and narrative producers represented explicitly.
