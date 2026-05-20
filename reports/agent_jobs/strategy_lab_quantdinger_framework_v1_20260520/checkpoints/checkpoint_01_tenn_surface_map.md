# M1 - Current Tenn Surface Map

Scope: read-only inspection of current repo docs/code sufficient to identify likely future integration surfaces.

## Confirmed Surfaces

### Task Card, Registry, And Report Artifacts

- `scripts/agent_job_contract.py` validates task-card frontmatter and `check-diff` enforces changed files against `allowed_files`.
- `scripts/agent_job_registry.py` supports `list-active`, `check-overlap`, `claim`, `heartbeat`, and `release`.
- The registry treats `reports/agent_jobs/` as internal for overlap/claim checks, but `check-diff` only sees Git-visible changed files. Report files are ignored by default unless force-added.
- Existing report convention is `reports/agent_jobs/<job_id>/README.md`, `status.json`, and `diff-check.json`; newer Evaluation Spine work also uses normalized manifest conventions.

### Evaluation

- `docs/architecture/12_evaluation_and_drift_monitoring.md` documents RAG stability, extraction eval, real-gold eval, and the difference between consistency and correctness.
- `docs/evaluation_spine_manifest_contract.md` defines an additive manifest contract for offline evaluation/reporting, with explicit `production_data_access`, `data_missing`, `source_artifacts`, validation commands, and overclaim guardrails.
- Recent Evaluation Spine reports show the intended offline pattern: DuckDB/report analytics must stay outside backend runtime, Docker, Qdrant, memory, news stores, extraction/parser, Cockpit, and financial truth.

### Cockpit UI / Reporting

- Current web UI routes include `/`, `/full-chat`, `/history`, `/holdings`, `/intel-ops`, `/marketplace`, `/marketplace/alerts`, `/marketplace/matches`, `/memory`, `/news`, `/operations`, `/settings`, `/thesis-audit`, `/updater`, `/verification`, and `/watchlist`.
- Current Next.js BFF routes under `cockpit-ui/app/api/cockpit/` include health, home, chat action jobs, commentary, claims, feedback, holdings, marketplace, memory, metrics, restart, and watchlist routes.
- `docs/architecture/21_cockpit_client_contract.md` states Cockpit is a client and orchestration layer, not a financial truth or retrieval authority.
- The Cockpit client contract states browser routes are presentation-layer pass-throughs and do not prove backend route availability in every environment.
- `cockpit-ui/lib/cockpit-types.ts` includes chat sources, source/evidence metadata, strategies, watchlist, holdings, verification, and operational types.

### Query Orchestration And Tooling

- `financial-engine_v2/backend/app/services/query_orchestrator.py` defines source-plan logic, source labels, missing-evidence semantics, and source budgets for financial fact, strategy, market, risk/catalyst, financial interpretation, and mixed intents.
- `financial-engine_v2/cockpit/core/agent_loop.py` is the structured agent loop and contains evidence-state handling, grounding tool names, and source coverage metadata.
- `financial-engine_v2/cockpit/core/tool_definitions.py` defines read-only tools and mutating tools.
- `financial-engine_v2/cockpit/core/tool_executor.py` executes read-only tools immediately and returns proposals for mutating tools rather than executing them autonomously.
- `financial-engine_v2/cockpit/core/actions.py` has an explicit action registry where mutating actions require confirmation.

### Provenance And Evidence

- `financial-engine_v2/backend/app/services/provenance.py` parses extraction provenance and orchestrator evidence into normalized provenance records.
- `financial-engine_v2/backend/app/routes/cockpit_api.py` defines `source_label_semantics_v1` labels, including `claim_verified`, `context_only`, `no_hit`, `operational_trace`, `local_personal_data`, `memory_context`, `external_web_context`, `local_news_context`, `financial_truth`, `degraded_runtime`, `missing_required_evidence`, and `unknown_unclassified`.
- `financial-engine_v2/backend/app/services/analysis_report_schema.py` validates analysis reports and evidence bundles with citation coverage and required evidence fields.
- `cockpit-ui/lib/cockpit-home-contract.ts` and tests enforce visible `DATA_MISSING`, `local_personal_data`, and non-financial-truth semantics for Home data.

### Financial Truth

- `docs/architecture/SYSTEM_CONTRACT.md` states backend is the sole authority for ingestion, extraction, storage, retrieval, and data correctness.
- The contract forbids Cockpit or external components from duplicating authoritative financial truth or retrieval ranking.
- `docs/architecture/22_memory_ownership_map.md` states canonical financial truth is Postgres `asx_periodic_financials`, written only by deterministic ingestion/extraction/normalization.
- The same ownership map says Qdrant stores are semantic retrieval aids, not truth memory.

### Memory

- `docs/architecture/18_cockpit_memory.md` defines separate classes for canonical financial truth, company memory, market memory, user thesis memory, session memory, and operational/workspace state.
- Backend-owned qualitative memory remains authoritative and Cockpit manages it only through backend APIs.
- User thesis memory writes are proposal -> confirm -> apply.
- Memory read/write events are emitted under `reports/research_memory/`, but this job did not inspect or mutate those stores.

### Portfolio, Risk, And Watchlist

- `financial-engine_v2/backend/app/modules/portfolio/` defines frozen portfolio types and a portfolio analyser that writes `reports/portfolio/<portfolio_id>_summary.json`.
- `financial-engine_v2/backend/app/modules/watchlist_scanner.py` scans existing analysis artifacts and generates alerts without DB dependency.
- `docs/architecture/17_analysis_modules.md` describes deterministic D1 analysis modules, optional D2 narrative, evidence chains, and portfolio-stage analysis.

## Inferred Future Integration Surfaces

- A Strategy Lab can be introduced first as an Evaluation/report artifact family, not as product code.
- The safest adapter boundary is a future Tenn-owned tool-policy client that converts QuantDinger outputs into Tenn-native artifacts and evidence bundles.
- Cockpit Chat can eventually request Strategy Lab jobs only through existing action preview/confirmation patterns.
- Watchlist and Company views can show Strategy Lab summaries as non-canonical opportunity notes if evidence labels and limitations are explicit.
- A dedicated Strategy Lab tab becomes justified only after multiple artifact types and a human review queue exist.

## Speculative Surfaces

- A future `/api/cockpit/strategy-lab/*` BFF/backend surface could exist, but no such route was found now.
- A future `reports/strategy_lab/` or `reports/agent_jobs/<job>/strategy_lab/` durable artifact store could exist, but this report does not create it.
- A future offline evaluator could compare QuantDinger backtests with Tenn analysis-module signals, but no current adapter exists.

## DATA_MISSING

- No live Cockpit route probes were run.
- No current UI screenshot or rendered Strategy Lab UX exists.
- No QuantDinger local installation exists in this repo.
- No Tenn-native Strategy Lab code path was found.
- No current production DB/Qdrant/memory data was inspected.

## Surface Classification

| Surface | Status | Reason |
| --- | --- | --- |
| Task-card registry and report artifacts | Confirmed | Local scripts and existing reports inspected. |
| Evaluation Spine manifest pattern | Confirmed | Local docs/reports inspected. |
| Cockpit web routes and BFF routes | Confirmed | Files under `cockpit-ui/app` inspected. |
| Backend `/api/cockpit` control plane | Confirmed | `main.py`, `cockpit_api.py`, and API-surface docs inspected. |
| Query orchestrator source labels | Confirmed | `query_orchestrator.py` inspected. |
| Provenance normalization | Confirmed | `provenance.py` inspected. |
| Memory ownership separation | Confirmed | Architecture docs inspected. |
| Strategy Lab as report artifact family | Inferred | Matches current Evaluation Spine/report conventions. |
| QuantDinger adapter/client | Speculative | No current code exists; design only. |
| Strategy Lab product tab | Speculative | No current route/component exists; future phase only. |
