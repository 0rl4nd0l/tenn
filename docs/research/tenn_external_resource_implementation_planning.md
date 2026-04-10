# Tenn External Resource Implementation Planning

**Date:** 2026-04-09  
**Status:** Complete  
**Scope:** Second-pass Tenn-specific implementation-planning investigation for shortlisted external resources.

---

## 1. Executive Summary

- Top immediate safe additions:
  - `mlflow/mlflow` as local file-backed eval tracking only
  - `duckdb/duckdb` as read-only eval/review analytics only
  - a minimal cockpit review package built from existing Tenn data:
    - evidence drawer over `/sources`
    - per-session scratchpad/event trace
    - unified staged review view for transcript and extraction review artifacts
- Top items to defer until after measurement:
  - `datalab-to/chandra`
  - `stanfordnlp/dspy`
  - `pola-rs/polars`
  - `scikit-learn/scikit-learn`
  - targeted `Financial Modeling Prep` adapter
- Top pattern-source-only items:
  - `TraderAlice/OpenAlice`
  - `virattt/dexter`
  - `ItzCrazyKns/Vane` as the verified live successor to `Perplexica`
  - `TauricResearch/TradingAgents`
- Top things to reject or sharply narrow:
  - `OpenBB` as a first narrow adapter
  - `defeat-beta/defeatbeta-api` as a first adapter
  - `Chandra` as a production fallback now
  - `DSPy` as a core architecture
  - any new agent/runtime platform adoption

### Main Conclusion

- Tenn should improve measurement, traceability, and review ergonomics first.
- The best near-term external-resource work is eval-side and UI-side.
- External data adapters should wait until after Tenn has measured real extraction quality and audited signal usefulness.

---

## 2. Verified Ambiguity Resolution

### `ItzCrazyKns/Perplexica`

- Exact verified artifact: `ItzCrazyKns/Vane`
- Evidence: GitHub repository search for `Perplexica` under `ItzCrazyKns` returns `ItzCrazyKns/Vane`, and the repo topics still include `perplexica`.
- Conclusion: treat `Vane` as the live canonical repo.

### `jxnl/pi-autoresearch`

- `DATA_MISSING`
- Closest verified artifact: `davebcn87/pi-autoresearch`
- Tenn already references this exact repo in `docs/research/autoresearch_evaluation.md:14`, so the first-pass `pi-autoresearch` conclusions remain directionally valid, but not under the `jxnl` slug.

### `anthropics/claude-scientific-skills`

- `DATA_MISSING`
- Closest verified artifact: `anthropics/skills`
- No repo with the exact requested name was verified.

### `disler/last30days-skill`

- `DATA_MISSING`
- No exact repo verified under `disler`.

### `e2b-dev/500-AI-Agents-Projects`

- `DATA_MISSING`
- No exact repo verified under `e2b-dev`.

---

## 3. Shortlist Deep Assessment

### DuckDB

- What it is:
  - Embedded analytical SQL engine with strong Python/file/DataFrame interop.
- Tenn lane:
  - `Evaluation`
- Exact Tenn touchpoints:
  - `scripts/run_real_extraction_eval.py`
  - `financial-engine_v2/scripts/extraction_eval_scorecard.py`
  - `financial-engine_v2/scripts/extraction_gold_eval_scorecard.py`
  - `financial-engine_v2/backend/tests/eval_results/`
  - `reports/extraction_real_eval_results.json`
  - `reports/extraction_real_eval_summary.md`
  - Optional later read-only inputs:
    - `financial-engine_v2/backend/app/services/extraction_review.py`
    - `reports/extraction_review/`
- Collision by touchpoint:
  - `scripts/run_real_extraction_eval.py`: `LOW`
  - `financial-engine_v2/scripts/extraction_eval_scorecard.py`: `LOW`
  - `financial-engine_v2/scripts/extraction_gold_eval_scorecard.py`: `LOW`
  - `backend/tests/eval_results/`: `LOW`
  - `backend/app/api/context.py`: `HIGH`
  - `backend/app/services/query_orchestrator.py`: `HIGH`
- Why any high collision exists:
  - If DuckDB moves into request-serving or retrieval paths, it becomes a second query substrate and pressures Tenn toward a second truth/read path.
- Smallest safe implementation slice:
  - Add a local, read-only DuckDB analysis script or notebook over existing eval JSON, scorecards, and extraction-review wrong-queue artifacts only.
- Sequencing:
  - `NOW`
- Expected value:
  - Faster analysis of which metrics fail by document type, ticker, trust outcome, or provenance status.
  - Makes repeated review findings and failure-taxonomy clustering easy.
  - Reduces manual JSON inspection during extraction hardening.
- Risks:
  - Truth-boundary risk: only if it starts writing or serving authoritative data.
  - Provenance risk: low if it only reads stored artifacts.
  - Cloud/API dependency risk: none.
  - Hardware/performance risk: low.
  - Maintenance risk: low if script-only.
  - Architectural drift risk: medium if it escapes dev/eval.
- Boundary that must not be crossed:
  - No DuckDB-backed API endpoints.
  - No DuckDB writes to canonical backend tables.
  - No DuckDB use inside `query_orchestrator.py`, `context.py`, or financial-truth services.
- Final verdict:
  - `SAFE TO EXTEND NOW`

### Polars

- What it is:
  - High-performance DataFrame engine for explicit batch transforms.
- Tenn lane:
  - `Evaluation`
- Exact Tenn touchpoints:
  - Likely first-slice sources only:
    - `scripts/run_real_extraction_eval.py`
    - `financial-engine_v2/backend/tests/eval_results/`
    - `financial-engine_v2/backend/app/services/commentary_memo_extractor.py`
    - `financial-engine_v2/backend/app/services/news_memo_extractor.py`
    - `financial-engine_v2/backend/app/services/memory_signal_router.py`
  - Likely first-slice output targets:
    - `reports/`
    - derived CSV/Parquet audit artifacts
- Collision by touchpoint:
  - `scripts/run_real_extraction_eval.py`: `LOW`
  - `commentary_memo_extractor.py` as data source only: `LOW`
  - `news_memo_extractor.py` as data source only: `LOW`
  - `memory_signal_router.py` as data source only: `LOW`
  - backend runtime adoption in service code: `MEDIUM`
  - replacing existing tabular/runtime patterns broadly: `HIGH`
- Why high collision exists:
  - If Polars becomes a backend runtime dependency instead of a local batch helper, Tenn now carries a second tabular-processing mental model beside plain Python/pandas/DuckDB-style SQL analytics.
- Smallest safe implementation slice:
  - One script that flattens memo/signal JSON into a Parquet or CSV table for signal-audit review.
- Sequencing:
  - `AFTER REAL-GOLD EXTRACTION EVAL`
- Expected value:
  - Faster audit-table preparation once real extraction results and signal-review datasets exist.
  - Cleaner schema normalization for large review batches.
- Risks:
  - Truth-boundary risk: low if script-only.
  - Provenance risk: low.
  - Cloud/API dependency risk: none.
  - Hardware/performance risk: low.
  - Maintenance risk: medium from ecosystem split.
  - Architectural drift risk: medium-high if moved into runtime services.
- Final verdict:
  - `INVESTIGATE AFTER MEASUREMENT`

### MLflow

- What it is:
  - Run/metric/artifact tracking platform.
- Tenn lane:
  - `Evaluation`
- Exact Tenn touchpoints:
  - `scripts/run_real_extraction_eval.py`
  - `financial-engine_v2/scripts/extraction_eval_scorecard.py`
  - `financial-engine_v2/scripts/extraction_gold_eval_scorecard.py`
  - `reports/extraction_real_eval_results.json`
  - `reports/extraction_real_eval_summary.md`
  - Future later extension targets:
    - router benchmark scripts
    - signal audit scripts
- Collision by touchpoint:
  - `scripts/run_real_extraction_eval.py`: `LOW`
  - `financial-engine_v2/scripts/extraction_eval_scorecard.py`: `LOW`
  - `financial-engine_v2/scripts/extraction_gold_eval_scorecard.py`: `LOW`
  - `backend/tests/test_extraction_eval.py`: `MEDIUM`
  - `backend/app/services/*`: `HIGH`
- Why high collision exists:
  - Runtime instrumentation inside backend services would pull experiment tracking into production flow and widen the operational surface unnecessarily.
- Smallest safe implementation slice:
  - Local file-backed MLflow tracking around extraction eval scripts only.
  - Log:
    - run params: dataset dir, tolerance, model label, commit hash, profile
    - metrics: overall score, trusted/abstain/quarantine counts, per-metric accuracy
    - artifacts: JSON results and markdown summary
- Sequencing:
  - `NOW`
- Expected value:
  - Immediate regression traceability across extraction hardening sessions.
  - Easier run-to-run comparison than raw `reports/` files alone.
  - Better foundation for later DSPy/Chandra comparisons.
- Risks:
  - Truth-boundary risk: none if script-only.
  - Provenance risk: low.
  - Cloud/API dependency risk: none in local `mlruns/` mode.
  - Hardware/performance risk: low.
  - Maintenance risk: low if no server.
  - Architectural drift risk: medium if Tenn jumps too quickly to hosted tracking.
- Rollout boundary:
  - No remote tracking server.
  - No DB-backed MLflow store.
  - No runtime-service instrumentation in phase 1.
- Final verdict:
  - `SAFE TO EXTEND NOW`

### DSPy

- What it is:
  - LM programming and optimization framework for modular prompt/program experiments.
- Tenn lane:
  - `Evaluation`
- Exact Tenn touchpoints:
  - Frozen benchmark contracts and data only:
    - `financial-engine_v2/backend/app/services/extraction_eval.py`
    - `financial-engine_v2/backend/app/services/extraction_gold_eval.py`
    - `financial-engine_v2/backend/tests/eval_fixtures/`
    - `financial-engine_v2/backend/tests/fixtures/extraction_gold/`
    - `scripts/run_real_extraction_eval.py`
  - Secondary future benchmark target:
    - `financial-engine_v2/backend/app/services/query_orchestrator.py`
  - Lower-priority future target:
    - `financial-engine_v2/backend/app/services/analysis/report_generator.py`
- Collision by touchpoint:
  - standalone benchmark script using eval fixtures: `LOW`
  - `query_orchestrator.py` as a benchmark target: `MEDIUM`
  - `report_generator.py` experiments: `MEDIUM`
  - `multipass_extraction.py` or `llm.py` runtime integration: `HIGH`
- Why high collision exists:
  - If DSPy enters the production extraction or routing path, Tenn now has a second core LM-programming architecture.
- Smallest safe implementation slice:
  - A standalone DSPy extraction benchmark sandbox using existing real-gold and synthetic scorecard logic only.
- Sequencing:
  - `AFTER REAL-GOLD EXTRACTION EVAL`
- Expected value:
  - Lets Tenn test whether prompt/program optimization improves extraction reliability before touching production code.
  - Gives a disciplined way to compare alternatives against fixed corpora.
- Risks:
  - Truth-boundary risk: low if sandboxed.
  - Provenance risk: medium if outputs are compared without clear run metadata.
  - Cloud/API dependency risk: depends on chosen model backend.
  - Hardware/performance risk: medium.
  - Maintenance risk: medium from new abstraction layer.
  - Architectural drift risk: high if promoted beyond sandbox use.
- Explicit rejection despite promise:
  - Do not use DSPy to re-architect Tenn’s extractor, router, or reporting path now.
- Final verdict:
  - `INVESTIGATE AFTER MEASUREMENT`

### Chandra

- What it is:
  - OCR/layout/document-intelligence model for Markdown/HTML/JSON document conversion.
- Tenn lane:
  - `Evaluation`
- Exact Tenn touchpoints:
  - Baseline comparison surfaces:
    - `financial-engine_v2/backend/app/services/docling_extract.py`
    - `scripts/run_real_extraction_eval.py`
    - `financial-engine_v2/backend/tests/test_docling_extract.py`
  - Manual-review surfaces:
    - `financial-engine_v2/backend/app/services/extraction_review.py`
    - `reports/extraction_review/`
  - Hard-corpus inputs:
    - `financial-engine_v2/data/extraction_gold_real/` once populated
- Collision by touchpoint:
  - offline comparator script: `LOW`
  - `extraction_review.py` as manual-support output consumer: `LOW`
  - `docling_extract.py` fallback integration: `HIGH`
  - `pipeline.py` or `multipass_extraction.py` production wiring: `HIGH`
- Why high collision exists:
  - Wiring Chandra into the live extraction path creates a second production extraction backend before Tenn has measured whether the problem is OCR/layout or downstream extraction.
- Smallest safe implementation slice:
  - A hard-PDF comparator script on a 10-document difficult corpus only.
  - Output: side-by-side Chandra vs docling artifacts plus scorecard-ready extracted fields.
- Sequencing:
  - `AFTER REAL-GOLD EXTRACTION EVAL`
- Expected value:
  - Distinguishes extraction-backend failure from prompt/reconciliation failure.
  - Helps decide whether future rescue/fallback work is even justified.
  - Can support manual gold-label assistance on hard documents.
- Risks:
  - Truth-boundary risk: low if offline.
  - Provenance risk: medium if outputs are manually copied without clear labeling.
  - Cloud/API dependency risk: optional, depends on local HF/vLLM vs hosted API.
  - Hardware/performance risk: medium-high on local hardware.
  - Maintenance risk: medium.
  - Architectural drift risk: high if promoted too quickly into production fallback.
- Explicit rejection despite promise:
  - Do not add Chandra as a new fallback in `docling_extract.py` now.
- Final verdict:
  - `INVESTIGATE AFTER MEASUREMENT`

### Targeted Financial Modeling Prep Adapter

- What it is:
  - Direct vendor API with documented transcript, profile, calendar, and news surfaces.
- Tenn lane:
  - `Memory`
- Exact Tenn touchpoints:
  - likely new provider:
    - `financial-engine_v2/backend/app/providers/` as a new FMP adapter module
  - existing config:
    - `financial-engine_v2/backend/app/core/config.py`
  - existing context bundle:
    - `financial-engine_v2/backend/app/api/context.py`
  - optional explicit endpoints:
    - `financial-engine_v2/backend/app/api/routes.py`
  - cockpit consumers only if surfaced:
    - `financial-engine_v2/cockpit/integrations/backend_api.py`
    - `financial-engine_v2/cockpit/core/chat.py`
    - `financial-engine_v2/cockpit/core/tool_executor.py`
- Collision by touchpoint:
  - new provider module: `LOW`
  - `core/config.py`: `MEDIUM`
  - `api/context.py`: `MEDIUM`
  - `api/routes.py`: `MEDIUM`
  - `backend_api.py` / `chat.py` / `tool_executor.py`: `LOW-MEDIUM`
  - any write into company/market memory stores: `HIGH`
  - any write into `asx_periodic_financials`: `HIGH`
- Why high collision exists:
  - Vendor statements or vendor-derived metrics would violate Tenn’s backend-owned extraction truth model if blended into canonical financials.
  - Auto-routing vendor transcripts/news into memory before signal audit would create hidden external influence over reasoning.
- Smallest safe implementation slice:
  - Read-only external `profile` + `earnings_calendar` block in `company_dump` only.
  - No vendor financial statements.
  - No vendor news ingestion.
  - No transcript ingestion.
  - No persistence.
- Sequencing:
  - `AFTER SIGNAL AUDIT`
- Expected value:
  - Fills low-risk context gaps without touching financial truth.
  - Gives the cockpit stable issuer metadata and upcoming event context.
- Risks:
  - Truth-boundary risk: high if scope creeps into statements.
  - Provenance risk: medium unless externally sourced fields are clearly separated and labeled.
  - Cloud/API dependency risk: high.
  - Hardware/performance risk: low.
  - Maintenance risk: medium from vendor auth/quotas.
  - Architectural drift risk: medium-high if it becomes a broad enrichment substrate too early.
- Explicit narrowing:
  - First slice should not include news.
  - First slice should not include transcripts.
- Final verdict:
  - `INVESTIGATE AFTER MEASUREMENT`

### OpenAlice UI Patterns

- What it is:
  - Source of event-log, staged approval, and trace-view patterns.
- Tenn lane:
  - `Reporting`
- Exact Tenn touchpoints:
  - `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - `financial-engine_v2/cockpit/core/tool_call_debug.py`
  - `financial-engine_v2/cockpit/storage/state.py`
  - `financial-engine_v2/cockpit/integrations/transcript_review.py`
  - `financial-engine_v2/cockpit/ui/app.py`
  - `financial-engine_v2/cockpit/ui/screens.py`
- Collision by touchpoint:
  - tool/status event persistence: `LOW`
  - staged review panel: `MEDIUM`
  - full file-driven runtime ideas: `HIGH`
- Smallest safe implementation slice:
  - Persist cockpit status/tool events to a local filterable event log and expose a read-only review panel.
- Sequencing:
  - `NOW`
- Expected value:
  - Better debugging across sessions.
  - Better operator review of approvals and actions.
- Risks:
  - Local log sprawl and sensitive content retention.
- Final verdict:
  - `PATTERN SOURCE ONLY`

### Dexter UI Patterns

- What it is:
  - Source of per-run scratchpad and debug-tail patterns.
- Tenn lane:
  - `Reporting`
- Exact Tenn touchpoints:
  - `financial-engine_v2/cockpit/core/tool_call_debug.py`
  - `financial-engine_v2/cockpit/core/chat.py`
  - `financial-engine_v2/cockpit/storage/artifacts.py`
  - `financial-engine_v2/cockpit/storage/state.py`
  - `financial-engine_v2/backend/app/routes/cockpit_api.py`
- Collision by touchpoint:
  - scratchpad JSONL: `LOW`
  - in-chat debug surfacing: `LOW`
  - autonomous research runtime ideas: `HIGH`
- Smallest safe implementation slice:
  - One append-only per-session scratchpad artifact containing status stages, tool traces, and final evidence metadata.
- Sequencing:
  - `NOW`
- Expected value:
  - Makes post-mortem review of cockpit answers dramatically easier.
- Risks:
  - More artifact volume; potential sensitive context logging.
- Final verdict:
  - `PATTERN SOURCE ONLY`

### Vane UI Patterns

- What it is:
  - Source of citation chips, evidence cards, and source-modal patterns.
- Tenn lane:
  - `Reporting`
- Exact Tenn touchpoints:
  - `financial-engine_v2/cockpit/core/sources.py`
  - `financial-engine_v2/cockpit/core/chat.py`
  - `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - `financial-engine_v2/cockpit/ui/app.py`
  - `financial-engine_v2/cockpit/ui/screens.py`
- Collision by touchpoint:
  - visual source drawer over existing payloads: `LOW`
  - replacing Tenn retrieval/chat model: `HIGH`
- Smallest safe implementation slice:
  - Add a visual evidence drawer over existing `sources` payloads and `/sources show` data.
- Sequencing:
  - `NOW`
- Expected value:
  - Faster operator review of grounded evidence.
  - Lower friction than command-only source inspection.
- Risks:
  - Mostly UI complexity.
- Final verdict:
  - `PATTERN SOURCE ONLY`

### TradingAgents UI Patterns

- What it is:
  - Source of explicit bull/bear/risk presentation patterns.
- Tenn lane:
  - `Reporting`
- Exact Tenn touchpoints:
  - `financial-engine_v2/cockpit/core/research/risk_gate.py`
  - `financial-engine_v2/cockpit/core/research/thesis.py`
  - `financial-engine_v2/cockpit/core/research/reflection.py`
  - `financial-engine_v2/backend/app/services/analysis/report_generator.py`
  - `financial-engine_v2/cockpit/core/plotly_html.py`
  - `financial-engine_v2/cockpit/core/chat.py`
- Collision by touchpoint:
  - presentation-layer bull/bear/risk sections: `LOW-MEDIUM`
  - debate/runtime orchestration adoption: `HIGH`
- Smallest safe implementation slice:
  - Add explicit `Bull Case`, `Bear Case`, and `Risk View` sections to one reporting surface only.
- Sequencing:
  - `AFTER SIGNAL AUDIT`
- Expected value:
  - Makes semantic signal review more legible.
  - Forces visible counter-case reasoning.
- Risks:
  - Presentation scope creep before measurement is finished.
- Final verdict:
  - `PATTERN SOURCE ONLY`

### OpenBB

- What it is:
  - Broad local platform and provider abstraction layer over many external data sources.
- Tenn lane:
  - `Memory`
- Exact Tenn touchpoints:
  - `financial-engine_v2/backend/app/providers/openbb_sidecar_provider.py`
  - `financial-engine_v2/backend/app/api/routes.py`
  - `financial-engine_v2/backend/app/services/openbb_staging.py`
  - `financial-engine_v2/backend/app/models/openbb_snapshots.py`
  - `financial-engine_v2/backend/app/core/config.py`
  - `financial-engine_v2/openbb_sidecar/` which is currently effectively empty in-repo
- Collision by touchpoint:
  - existing provider wrapper: `MEDIUM`
  - staging and snapshot model expansion: `HIGH`
  - reviving a full sidecar runtime: `HIGH`
- Smallest safe implementation slice:
  - None recommended before a narrow use case beats FMP directly.
- Sequencing:
  - `LATER / FUTURE ONLY`
- Expected value:
  - Only useful if Tenn later wants provider abstraction across multiple vendors.
- Risks:
  - Platform complexity, wrapper-of-wrapper behavior, high collision with narrow-adapter needs.
- Why it should not be the first adapter despite looking promising:
  - For transcripts it appears to wrap FMP anyway.
  - Tenn would pay platform complexity before proving surface need.
- Final verdict:
  - `REFERENCE ONLY`

### defeat-beta-api

- What it is:
  - Local DuckDB query layer over a hosted Hugging Face finance dataset, exposing profile/news/transcript-like APIs.
- Tenn lane:
  - `Memory`
- Exact Tenn touchpoints:
  - likely only a future experimental provider under `financial-engine_v2/backend/app/providers/`
  - same existing context surfaces as any external adapter:
    - `backend/app/api/context.py`
    - `backend/app/api/routes.py`
    - `cockpit/integrations/backend_api.py`
- Collision by touchpoint:
  - experimental provider: `LOW-MEDIUM`
  - context bundle integration: `MEDIUM`
  - treating it as a trusted adapter: `HIGH`
- Smallest safe implementation slice:
  - None as a first adapter.
  - At most a dev-only comparison script for transcript/news/profile retrieval quality.
- Sequencing:
  - `LATER / FUTURE ONLY`
- Expected value:
  - Interesting as a local-query exploration source.
- Risks:
  - Still remote-data dependent.
  - Narrower calendar coverage.
  - Less direct and less proven than FMP for Tenn’s first adapter need.
- Direct answer on preference:
  - It should not be preferred over FMP or OpenBB for Tenn’s first narrow transcript/news/profile adapter role.
- Final verdict:
  - `REFERENCE ONLY`

### scikit-learn

- What it is:
  - Classical ML baseline toolkit.
- Tenn lane:
  - `Evaluation`
- Exact Tenn touchpoints:
  - future labeled sources only:
    - `financial-engine_v2/backend/app/services/memory_signal_router.py`
    - `financial-engine_v2/backend/app/services/commentary_memo_extractor.py`
    - `financial-engine_v2/backend/app/services/news_memo_extractor.py`
    - `financial-engine_v2/backend/tests/test_memory_signal_router.py`
    - `financial-engine_v2/backend/app/services/query_orchestrator.py`
    - `financial-engine_v2/backend/app/services/hybrid_retriever.py`
- Collision by touchpoint:
  - offline labeled-baseline scripts: `LOW`
  - routing benchmark experiments: `MEDIUM`
  - production retrieval/routing replacement: `HIGH`
- Smallest safe implementation slice:
  - After signal audit, build one offline baseline:
    - signal usefulness classifier
    - or query-intent classifier
  - Not both at once.
- Sequencing:
  - `AFTER SIGNAL AUDIT`
- Expected value:
  - Reveals whether Tenn is solving a problem that a cheap baseline already handles.
  - Helps avoid LLM over-engineering.
- Risks:
  - Little value before labeled audit data exists.
  - Can become a distracting side-track if added too early.
- Recommendation on concrete uses:
  - Duplicate detection: not now; Tenn already has deterministic dedupe in memory/update paths.
  - Signal usefulness classification: yes, after audit labels exist.
  - Routing sanity baselines: yes, but only after a labeled query set exists.
  - Text clustering: maybe later, not first.
  - TF-IDF retrieval sanity checks: lower priority because Tenn already has BM25 in `hybrid_retriever.py`.
- Final verdict:
  - `INVESTIGATE AFTER MEASUREMENT`

---

## 4. Comparative Source Recommendation

| Surface | FMP | OpenBB | defeatbeta-api | Tenn Recommendation |
|---|---|---|---|---|
| Transcripts | Direct, documented | Appears to wrap FMP for this surface | Available, but dataset-backed | FMP if Tenn ever adds this |
| Company profiles | Direct, simple | Wrapped through platform/provider layer | Available | FMP first |
| Calendars | Direct, broad | Wrapped and broader platform | Earnings calendar verified, narrower | FMP first |
| News | Direct | Wrapped through multiple providers | Available | None first; Tenn already has `newspaper4k` |
| Local-vs-cloud | Cloud API | Local runtime over cloud providers | Local DuckDB over hosted dataset | FMP for narrow adapter, DuckDB/defeatbeta only for experiments |

### Narrow First Adapter Recommendation

- `FMP`, but only for `profile` + `earnings_calendar` first.

### Why Not OpenBB First

- Too much platform for a narrow need.
- Transcript surface appears to collapse back to FMP anyway.
- Tenn already has wrapper code but not a real checked-in sidecar implementation.

### Why Not defeatbeta First

- Attractive because of DuckDB/local-query style.
- Not actually more local at the data-source layer.
- Narrower, less direct, less clearly documented for first production-adjacent use.

### Direct Answer To The Explicit Question

- `defeat-beta/defeatbeta-api` should **not** be preferred over FMP or OpenBB for Tenn’s first narrow transcript/news/profile adapter role.
- Its best use is dev-only comparative exploration, not the first adapter.

---

## 5. UI / Review Pattern Recommendation

### Minimal Tenn-Safe UI Package

- visual evidence drawer over existing source payloads
- per-session scratchpad/event trace
- unified staged review page for transcript approvals plus extraction review queue
- optional bull/bear/risk output blocks on one analysis surface

### What To Borrow

- From `Vane`: source cards, citation chips, expandable snippet modal
- From `Dexter`: append-only scratchpad per session
- From `OpenAlice`: filterable event log and staged approval panel
- From `TradingAgents`: explicit bull/bear/risk presentation blocks

### Where To Add It

- `financial-engine_v2/cockpit/core/sources.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/cockpit/ui/app.py`
- `financial-engine_v2/cockpit/ui/screens.py`
- `financial-engine_v2/backend/app/services/extraction_review.py`
- `financial-engine_v2/cockpit/integrations/transcript_review.py`
- `financial-engine_v2/backend/app/services/analysis/report_generator.py`
- `financial-engine_v2/cockpit/core/research/risk_gate.py`

### What Not To Copy

- OpenAlice’s file-driven runtime or trading-as-git model
- Dexter’s autonomous agent shell
- Vane’s search/retrieval runtime
- TradingAgents’ full debate runtime or vendor-fallback logic

### Best Immediate UI Addition

- a source/evidence drawer, because Tenn already has the payloads and `/sources` inspection logic in:
  - `cockpit/core/sources.py`
  - `cockpit/core/chat.py`
  - `backend/app/routes/cockpit_api.py`

---

## 6. Implementation Sequence

1. Add local file-backed MLflow logging around current extraction eval scripts only.
   - Why first:
     - it improves traceability immediately without changing Tenn behavior.
2. Add a read-only DuckDB analysis script over existing eval/review artifacts.
   - Why second:
     - it makes current and future measurement outputs easier to inspect.
3. Add the minimal cockpit evidence package:
   - evidence drawer over `/sources`
   - per-session scratchpad/event trace
   - Why third:
     - it makes the coming real-gold and signal-review work faster to inspect.
4. Finish the real-document extraction gold-corpus work.
   - This is the measurement gate for Chandra and DSPy.
5. Run Chandra as a hard-PDF comparator on the real-gold hard subset.
   - Why here:
     - now Tenn can measure whether the bottleneck is layout/OCR or downstream extraction.
6. If the review datasets become awkward to flatten manually, add a Polars audit-prep script.
   - Why here:
     - only after real measurement volume justifies a second local tabular engine.
7. Stand up a DSPy sandbox for extraction benchmarking against the frozen real-gold corpus.
   - Why here:
     - now there is a stable optimization target.
8. Complete the signal-quality audit.
   - This is the gate for external adapter and sklearn choices.
9. If the signal audit still shows supporting-context gaps, add the narrow FMP `profile + earnings_calendar` adapter.
   - Why here:
     - now Tenn has evidence that more external context is actually needed.
10. Add one sklearn baseline after labeled signal or query data exists.
   - First candidate:
     - signal usefulness classification
   - Second candidate:
     - routing sanity baseline

---

## 7. Explicit Do-Not-Do List

- Do not put DuckDB in Tenn’s request path or use it as a second truth store.
- Do not add Polars to backend runtime services by default.
- Do not stand up a remote MLflow server now.
- Do not make DSPy a second Tenn architecture.
- Do not wire Chandra into `docling_extract.py` or `pipeline.py` now.
- Do not use vendor financial statements as canonical truth.
- Do not auto-route FMP/OpenBB/defeatbeta transcripts or news into company/market memory before the signal audit.
- Do not revive OpenBB as a broad sidecar platform for a narrow first adapter use case.
- Do not pick defeatbeta over FMP for the first adapter.
- Do not adopt OpenAlice, Dexter, Vane, TradingAgents, DeerFlow, or Hermes as runtimes.
- Do not let UI work outrun measurement work.

### Most Decision-Ready Conclusion

1. Safe now:
   - local MLflow
   - read-only DuckDB analytics
   - minimal cockpit evidence/review package
2. Wait for real extraction measurement:
   - Chandra
   - DSPy
   - Polars
3. Wait for signal audit:
   - FMP adapter
   - sklearn baselines
4. Keep as references or pattern sources only:
   - OpenBB
   - defeatbeta-api
   - OpenAlice
   - Dexter
   - Vane
   - TradingAgents
