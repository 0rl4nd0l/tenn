# Tenn External Resource Viability Investigation

**Date:** 2026-04-09  
**Status:** Complete  
**Scope:** Read-only Tenn-specific viability audit of external repos, frameworks, libraries, platforms, and papers.

---

## 1. Executive Summary

- Most promising now: `duckdb/duckdb`, `pola-rs/polars`, `mlflow/mlflow`, `stanfordnlp/dspy`, `datalab-to/chandra`.
- Best pattern-source-only resources: `TraderAlice/OpenAlice`, `NousResearch/hermes-agent`, `TauricResearch/TradingAgents`, `ItzCrazyKns/Perplexica` / `Vane`, `pi-autoresearch`.
- Top reject/defer items: `bytedance/deer-flow`, `SakanaAI/AI-Scientist-v2` as a system, `mariostoev/finviz`, `cheahjs/free-llm-api-resources`, `profitviews/news-droid`.

### What This Means For Tenn Right Now

- Tenn does not need a new agent platform.
- Tenn does need better eval analytics, experiment traceability, and a disciplined way to inspect real extraction failures and signal quality.
- The safest additions are dev/eval-side only.
- The most dangerous additions are new runtimes that duplicate orchestration, memory, or financial truth ownership.

---

## 2. Current Tenn Constraint Reminder

### Contract Framing

- Target layers examined: Financial Truth, Evaluation, Provenance, Query Orchestration, Memory, Reporting, Scheduling.
- Governing rules: backend is sole authority, retrieval stays backend-owned, no parallel systems, fail-fast over hidden fallback, no cockpit-side truth pipeline.
- Must not change: backend-owned financial truth and retrieval, the separate company/market memory model, staged commentary approval, and the existing worker/task contract.
- Why this investigation is safe: this was read-only. No Tenn code, models, DBs, or runtimes were changed.
- GPU process check: not required. No llama-server spawn or restart was proposed.

### Confirmed Tenn Reality From The Repo

- `financial-engine_v2/backend/app/services/multipass_extraction.py:1-12` already implements a 4-pass extraction pipeline.
- `financial-engine_v2/backend/app/services/docling_extract.py:250-305` already runs docling-first extraction with PyMuPDF fallback.
- `financial-engine_v2/backend/app/services/extraction_eval.py:1-9` is a deterministic synthetic eval harness.
- `financial-engine_v2/backend/app/services/extraction_gold_eval.py:1-22` is the real-gold pilot eval surface.
- `financial-engine_v2/backend/app/services/provenance.py:100-259` already parses extraction and orchestrator provenance.
- `financial-engine_v2/backend/app/services/query_orchestrator.py:324-369` and `financial-engine_v2/backend/app/services/query_orchestrator.py:625-696` already enforce a backend query plan with `financial_truth` first for numeric questions.
- `financial-engine_v2/backend/app/services/company_memory.py:14-31` and `financial-engine_v2/backend/app/services/market_memory.py:14-31` explicitly block financial metrics from memory stores.
- `financial-engine_v2/backend/app/services/commentary_ingest.py:199-260` stages transcripts for approval instead of auto-indexing them.
- `financial-engine_v2/backend/app/services/speaker_turn_detector.py:1-154` shows current speaker handling is regex-based, not model-based.
- `financial-engine_v2/backend/app/api/routes.py:193-306` already has price and fundamentals enrichment hooks, including an OpenBB-sidecar wrapper path.
- `financial-engine_v2/backend/app/worker_tasks.py:10-24` keeps Celery as a thin execution wrapper, not a second pipeline.

### Why Many External Resources Are Mistimed

- Tenn already has extraction, eval, provenance, memory, retrieval, reporting, and scheduled execution surfaces.
- The dominant gaps are measurement and audit quality, not framework absence.
- Real next work remains:
  - build and score a small real ASX gold corpus,
  - run semantic signal audits on real documents,
  - avoid rewriting extraction or orchestration before those measurements exist.

---

## 3. Resource-By-Resource Detailed Assessment

### 3.1 AI / LLM Systems & Agents

| Resource | Assessment | Collision | Safe Path In Tenn | Verdict |
|---|---|---:|---|---|
| `microsoft/VibeVoice` | Lane: `Memory`. Long-form ASR with speaker and timestamp structure. Useful for future management-commentary or interview ingestion. Not useful for current extraction bottlenecks. | Low | Eval-only spike against `youtube_transcript_fetcher.py`, `speaker_turn_detector.py`, `commentary_ingest.py`; no new serving stack in production. | `REFERENCE ONLY` |
| `bytedance/deer-flow` | Lane: `Query Orchestration`. Full LangGraph agent platform with UI, gateway, skills, memory, sandboxing, MCP. Useful only for patterns like per-thread workspace isolation and skill loading. Dangerous because it duplicates Tenn’s cockpit and runtime surfaces. | High | None as a runtime. At most borrow documentation patterns. | `BLOCKED DUE TO COLLISION` |
| `NousResearch/hermes-agent` | Lane: `Query Orchestration`. Full agent runtime with tool registry, MCP, TUI, gateways, memory plugins. Useful patterns: profile-scoped state, SQLite WAL/FTS memory, MCP env hardening. Dangerous as a direct runtime replacement. | High | Borrow only cockpit-tooling patterns around `tool_definitions.py`, `tool_executor.py`, `subagents.py`. | `PATTERN SOURCE ONLY` |
| `SakanaAI/AI-Scientist-v2` | Lane: `Evaluation`. Autonomous code-executing experiment and paper system. Useful only for stage separation, bounded search, and artifact discipline. Dangerous because it normalizes sandboxed autonomous code mutation. | Medium | If anything is borrowed, borrow stage and budget ideas for eval runners only. No runtime adoption. | `PATTERN SOURCE ONLY` |
| `stanfordnlp/dspy` | Lane: `Evaluation`. Strong typed LM-module and prompt-optimizer framework. Useful for extractor, router, and report benchmark sandboxes. Dangerous if it becomes a second LM-programming architecture beside Tenn’s current pipeline. | Medium | Isolated eval lane only around `extraction_eval.py`, `extraction_gold_eval.py`, and routing-classification experiments. | `INVESTIGATE FURTHER` |
| `jxnl/pi-autoresearch` | Lane: `Evaluation`. `DATA_MISSING` on the exact slug; the live verified repo is `davebcn87/pi-autoresearch`, and Tenn already documented it in `docs/research/autoresearch_evaluation.md`. Useful patterns: append-only experiment logs, objective files, backpressure checks. | Low | Dev-only experiment loop patterns; no direct adoption. | `PATTERN SOURCE ONLY` |
| `TraderAlice/OpenAlice` | Lane: `Query Orchestration`. File-driven AI trading runtime. High-value patterns: append-only JSONL event log, staged approval, config-as-files, tool center. Dangerous because it is a full overlapping platform with AGPL and trading-centric architecture. | High | Borrow only review, event-log, and approval-flow patterns near `cockpit/core/actions.py`, `tool_executor.py`, and chat or debug UI. | `PATTERN SOURCE ONLY` |

### 3.2 Local AI / RAG / Inference / Data Tools

| Resource | Assessment | Collision | Safe Path In Tenn | Verdict |
|---|---|---:|---|---|
| `ItzCrazyKns/Perplexica` / current `Vane` | Lane: `Reporting`. Search-answer product with citations, search modes, file upload, model modes, and responsive UI. Useful for cited answer display and retrieval-debug UX. Dangerous if treated as a retrieval architecture replacement. | Medium | UI-only borrowing into `cockpit/ui/web.py` and chat or debug panels. | `PATTERN SOURCE ONLY` |
| `lyogavin/airllm` | Lane: `Query Orchestration`. Low-VRAM HF loading and runtime trickery. Useful only if Tenn’s current llama.cpp path becomes a proven bottleneck. Wrong fit for the current hardening phase. | Medium | Benchmark-only. Do not replace llama.cpp or OpenClaw serving. | `REFERENCE ONLY` |
| `pandas-dev/pandas` | Lane: `Evaluation`. Already a selective Tenn dependency in scripts and `backend/app/utils/trading_calendar.py`. Good for ad hoc wrangling; not a reason to redesign current batch surfaces. | Low | Keep selective usage; do not force migration in either direction. | `REFERENCE ONLY` |
| `pola-rs/polars` | Lane: `Evaluation`. Strong fit for local batch transforms, fixture prep, reconciliation, and signal-audit data prep. Main risk is ecosystem split if used too broadly. | Low-Med | Dev or eval-only utilities in `scripts/` or isolated analysis helpers; not backend truth path. | `SAFE TO EXTEND` |
| `scikit-learn/scikit-learn` | Lane: `Evaluation`. Strong for baseline classifiers, TF-IDF text baselines, duplicate detection, clustering, and trust heuristics. Complements LLMs instead of colliding with them. | Low | Eval-only baselines for extraction, routing, or signal-quality experiments. | `SAFE TO EXTEND` |
| `duckdb/duckdb` | Lane: `Evaluation`. Best immediate fit for local analytics over fixtures, reports, JSON, and Parquet. Main risk is accidentally turning it into a second truth store. Its VSS extension is too experimental for production. | Low-Med | Dev or eval-only analytics sidecar reading Tenn artifacts; never authoritative storage. | `SAFE TO EXTEND` |
| `sqlalchemy/sqlalchemy` | Lane: `Financial Truth`. Tenn already uses SQLAlchemy widely. No evidence a new abstraction push is urgent. | Medium | No new adoption work; just continue current usage. | `REFERENCE ONLY` |

### 3.3 Financial Data Sources

| Resource | Assessment | Collision | Safe Path In Tenn | Verdict |
|---|---|---:|---|---|
| `ranaroussi/yfinance` | Lane: `Memory`. Already effectively present in Tenn as a narrow price fallback in `context_loader.py` and a dependency in `backend/requirements.txt`. Useful for prototyping and rough enrichment only. Legal and source-stability limits make it unfit as canonical truth. | Low | Keep it non-canonical and clearly labeled as external enrichment only. | `REFERENCE ONLY` |
| `Financial Modeling Prep` | Lane: `Memory`. Strongest external API candidate for transcripts, profiles, calendars, and news. Dangerous if it starts filling financial-truth gaps or introduces broad cloud dependence into core flows. | Medium | One narrow adapter for transcripts, profile, and calendar only, likely under `app/providers/` plus `api/context.py` or `routes.py`, with explicit external provenance labels. | `INVESTIGATE FURTHER` |
| `mariostoev/finviz` | Lane: `Reporting`. Unofficial scraper with ToS and breakage risk. Useful only as screener inspiration, not as a reliable Tenn data substrate. | Med | None. | `REJECT` |
| `defeat-beta/defeatbeta-api` | Lane: `Memory`. Interesting because it uses DuckDB plus a hosted dataset and exposes transcripts, news, and profile-like surfaces. Safer than HTML scraping, but coverage, licensing, and freshness are less proven than FMP. | Medium | Isolated adapter comparison against FMP and yfinance for transcripts, news, and profile only. | `INVESTIGATE FURTHER` |

### 3.4 Backtesting / Trading / Execution / Modeling / Orchestration

| Resource | Assessment | Collision | Safe Path In Tenn | Verdict |
|---|---|---:|---|---|
| `quantopian/zipline` | Lane: `Evaluation`. Historical event-driven backtesting reference. Old ecosystem assumptions make it a poor near-term adoption target. | Low | Historical reference only. | `REFERENCE ONLY` |
| `polakowo/vectorbt` | Lane: `Evaluation`. Strong later-stage offline research tool for factor or signal validation. Not a current hardening priority. | Low | Notebook-only or isolated research sandbox later. | `REFERENCE ONLY` |
| `QuantConnect/Lean` | Lane: `Evaluation`. Huge quant platform with large runtime and cloud or platform gravity. Valuable as a future reference, not as a near-term Tenn addition. | Med-High | Reference only; no platform adoption. | `REFERENCE ONLY` |
| `tensortrade-org/tensortrade` | Lane: `Evaluation`. RL trading framework. Some experiment-discipline ideas, but RL trading is out of scope for Tenn right now. | Medium | Reference only. | `REFERENCE ONLY` |
| `Interactive Brokers docs` | Lane: `Query Orchestration`. Useful only as future broker-reference material. No near-term relevance to Tenn’s current bottlenecks. | Medium | Explicitly defer. | `REFERENCE ONLY` |
| `erdewit/ib_insync` | Lane: `Query Orchestration`. Only useful if Tenn ever adds IB-linked data or execution later. Not a hardening-phase candidate. | Medium | Explicitly defer. | `REFERENCE ONLY` |
| `google-research/timesfm` | Lane: `Evaluation`. Potential later forecasting benchmark for market-memory time series. Not relevant to current extraction or signal audit bottlenecks. | Medium | Research-only later. | `REFERENCE ONLY` |
| `datalab-to/chandra` | Lane: `Financial Truth`. The most relevant external extraction-adjacent resource. Useful as OCR or layout rescue, table-heavy comparator, or manual gold-label helper. Dangerous if promoted to production before Tenn has real-document measurement. | Medium | Offline comparator on hard PDFs alongside `docling_extract.py` and eval scripts; no production fallback yet. | `INVESTIGATE FURTHER` |
| `PrefectHQ/prefect` | Lane: `Query Orchestration`. Tenn already has Celery, action scripts, and scheduled batch surfaces. Prefect only matters if orchestration pain becomes first-order and measurable. | Med-High | Optional ops pilot outside core production path; not now. | `REFERENCE ONLY` |
| `mlflow/mlflow` | Lane: `Evaluation`. Strong immediate fit for run, metric, and artifact lineage on extraction and routing experiments. Biggest risk is over-serverizing too early. | Low | Start with local file-backed `mlruns/` only; no remote server initially. | `SAFE TO EXTEND` |

### 3.5 Quant Platforms / Data

| Resource | Assessment | Collision | Safe Path In Tenn | Verdict |
|---|---|---:|---|---|
| `microsoft/qlib` | Lane: `Evaluation`. Large quant research platform with strong local data handling and factor workflows. Useful later for market-memory research, not current hardening. | Medium | Separate research sandbox later, not product path. | `REFERENCE ONLY` |
| `OpenBB-finance/OpenBB` | Lane: `Memory`. Broad multi-provider financial platform. Tenn already has wrapper and staging code for an OpenBB sidecar, but the repo does not currently vendor a real sidecar implementation; `financial-engine_v2/openbb_sidecar/` is effectively empty. Useful only as an optional enrichment sidecar, not as a platform migration. | Med-High | If pursued, revive only as an optional sidecar behind existing `OpenBBSidecarProvider` and staging models; do not widen it into a second platform. | `INVESTIGATE FURTHER` |

### 3.6 Research / Skills / Lists

| Resource | Assessment | Collision | Safe Path In Tenn | Verdict |
|---|---|---:|---|---|
| `disler/last30days-skill` | Lane: `Memory`. `DATA_MISSING`: exact repo not verified. Even if found, recency filtering is simple and not worth chasing as a dependency. | Low | None. Build internally if ever needed. | `REJECT` |
| `anthropics/claude-scientific-skills` | Lane: `Evaluation`. `DATA_MISSING` on the exact repo. Closest verified surface is `anthropics/skills`, which is useful only as workflow and skill-structure inspiration. | Low | Pattern borrowing into internal docs or skills only. | `PATTERN SOURCE ONLY` |
| `e2b-dev/500-AI-Agents-Projects` | Lane: `Query Orchestration`. `DATA_MISSING` on the exact repo. Even if found, this is likely inspiration inventory rather than a reusable subsystem. | Low | None. | `REJECT` |

### 3.7 TradingAgents Repo + Paper

| Resource | Assessment | Collision | Safe Path In Tenn | Verdict |
|---|---|---:|---|---|
| `TauricResearch/TradingAgents` | Lane: `Reporting`. Useful only for structured bull, bear, and risk report stages, explicit counter-case sections, and packaged report outputs. Dangerous as a runtime because it embeds its own data tools, fallback behavior, memory, and trade-decision loop. | High | Borrow report structure only into `report_generator.py` or cockpit research views. | `PATTERN SOURCE ONLY` |
| `TradingAgents` paper `arXiv:2412.20138` | Lane: `Reporting`. The paper supports structured role decomposition and debate as a reporting pattern. It does not justify replacing Tenn’s runtime. | Medium | Reporting and template inspiration only. | `PATTERN SOURCE ONLY` |

### 3.8 Previously Discussed Resources

| Resource | Assessment | Collision | Safe Path In Tenn | Verdict |
|---|---|---:|---|---|
| Karpathy-style `LLM Wiki` concept | Lane: `Reporting`. Useful as a developer-facing repo map or explorable code wiki concept. Not product architecture. | Low | Dev or docs tooling only. | `PATTERN SOURCE ONLY` |
| AutoResearch-style systems / autonomous research agents | Lane: `Evaluation`. Tenn already documented this in `docs/research/autoresearch_evaluation.md`: borrow patterns only, never self-modify production financial paths. | Medium | Dev-only experiment logging or checkpointing patterns. | `PATTERN SOURCE ONLY` |
| `virattt/dexter` | Lane: `Query Orchestration`. Useful patterns: per-run scratchpad logs and self-validation traces. Dangerous as a second research-agent shell. | High | Pattern borrowing for cockpit research traces only. | `PATTERN SOURCE ONLY` |
| `wangzhe3224/awesome-systematic-trading` | Lane: `Evaluation`. Mostly a taxonomy or list repo. Useful only as a curated map of later research categories. | Low | Reference list only. | `REFERENCE ONLY` |
| `akurgat/automating-technical-analysis` | Lane: `Evaluation`. Small technical-analysis prediction app; low evidence of reusable rigor. | Low | None. | `REJECT` |
| `rolling-panda-san/notebooks` | Lane: `Evaluation`. Useful as a paper-to-notebook research artifact pattern. Limited direct reusable system value. | Low | Reference only. | `REFERENCE ONLY` |
| `gbeced/basana` | Lane: `Query Orchestration`. Async event-driven trading framework. Useful only for order-book or event patterns, not current Tenn scope. | Medium | Reference only. | `REFERENCE ONLY` |
| `Ashwin3919/gemini-cli-exp` | Lane: `Reporting`. Useful graph-index or code-wiki pattern for code navigation or project memory tooling. | Low | Dev-only code-intelligence helper if ever needed. | `PATTERN SOURCE ONLY` |
| `nextlevelbuilder/ui-ux-pro-max-skill` | Lane: `Reporting`. Useful design-system and page-override workflow patterns for cockpit UI. | Low | Design guidance only. | `PATTERN SOURCE ONLY` |
| `theDakshJaitly/mex` | Lane: `Memory`. Useful structured project-memory scaffold and drift checks. Dangerous only if it becomes a parallel truth store. | Low-Med | Internal docs or memory scaffold only. | `PATTERN SOURCE ONLY` |
| `nyldn/claude-octopus` | Lane: `Query Orchestration`. Useful consensus or disagreement gating pattern. Dangerous as a full multi-provider orchestration runtime. | High | Pattern borrowing only for human-review or debate gating. | `PATTERN SOURCE ONLY` |
| `AlgoTraders/stock-analysis-engine` | Lane: `Memory`. Legacy distributed data or backtest engine. Useful only for cache or raw-dataset separation patterns. | Medium | Reference only. | `REFERENCE ONLY` |
| `dragon1086/prism-insight` | Lane: `Reporting`. Large AI trading platform with broad claims. Only the journal or feedback loop idea looks reusable; the rest is mistimed. | High | None. | `REJECT` |
| `gruquilla/FinAPy` | Lane: `Reporting`. Small notebook project. Useful only as an example of keeping AI commentary downstream of explicit metrics. | Low | Reference only. | `REFERENCE ONLY` |
| `BloopAI/vibe-kanban` | Lane: `Reporting`. Useful for reviewable agent workspaces, diffs, and feedback UX. | Low | Internal dev or review UX only. | `PATTERN SOURCE ONLY` |
| `braedonsaunders/sloppy` | Lane: `Evaluation`. Useful rescan-after-fix and surfaced-new-issues pattern for dev quality loops. | Low | Dev-only quality automation ideas. | `PATTERN SOURCE ONLY` |
| `cheahjs/free-llm-api-resources` | Lane: `Query Orchestration`. List repo only. Opposite of Tenn’s audit-first or local-first preference. | Low | None. | `REJECT` |
| `profitviews/news-droid` | Lane: `Evaluation`. Tiny news-sentiment trading bot. Very low reusable signal. | Low | None. | `REJECT` |

---

## 4. Cross-Resource Synthesis

### Best Cross-Cutting Patterns Worth Borrowing

- Append-only logs: `OpenAlice`, `pi-autoresearch`, and `Dexter` all reinforce Tenn’s need for durable experiment or event trails.
- Structured counter-case reporting: `TradingAgents` is the clearest source for bull, bear, and risk sections without adopting a runtime.
- Grounded answer UI: `Perplexica` or `Vane` is the best reference for citations, source modes, and retrieval-debug presentation.
- Tool or runtime hardening: `hermes-agent` shows useful profile-scoped state and MCP isolation patterns.
- Eval discipline: `DSPy`, `MLflow`, `pi-autoresearch`, and even `AI-Scientist-v2` all point toward the same missing Tenn need: disciplined experiment tracking around fixed datasets.
- Local analytics: `DuckDB`, `Polars`, and `scikit-learn` together cover Tenn’s highest-value non-LLM expansion surface.
- Transcript evidence capture: `VibeVoice` is only interesting because Tenn already has transcript staging and only weak speaker handling today.
- Approval flows: `OpenAlice` strongly validates Tenn’s existing instinct to keep review or staging gates before indexing or action.

### Patterns To Avoid

- Full agent-platform adoption.
- Trading or execution runtimes.
- Framework migrations that create a second orchestration stack.
- Cloud-first data layers becoming shadow truth systems.
- Autonomous mutation loops near financial truth or production routing.

---

## 5. Recommended Tenn Roadmap Implications

### Immediate Candidates

- `DuckDB`
- `Polars`
- `MLflow`
- `scikit-learn` baselines
- Reporting or review UI patterns from `Perplexica`, `OpenAlice`, and `TradingAgents`

### Near-Term Investigation Candidates

- `Chandra`
- `DSPy` eval-only sandbox
- targeted `FMP` adapter
- `OpenBB` sidecar re-evaluation through the existing wrapper path
- `defeatbeta-api` as a secondary transcript, news, or profile comparison source

### Later-Stage Research Candidates

- `TimesFM`
- `qlib`
- `vectorbt`
- `Lean`
- `TensorTrade`
- `Interactive Brokers` docs and `ib_insync`

### Do Not Pursue Now

- `deer-flow`
- full `hermes-agent` runtime adoption
- `AI-Scientist-v2` as a system
- `OpenAlice` as a runtime
- `TradingAgents` as a runtime
- `finviz`
- `free-llm-api-resources`
- `news-droid`
- toy TA or trading repos

---

## 6. Concrete Implementation Shortlist

| Item | Why Now | Where It Fits | Minimal Implementation Strategy | Expected Value | Risk |
|---|---|---|---|---|---|
| `DuckDB` | Tenn’s immediate need is local analysis of real extraction failures and signal audits. | Dev or eval only around `extraction_eval.py`, `extraction_gold_eval.py`, `reports/`, and analysis scripts. | Add standalone scripts or notebooks that query fixture JSON, eval outputs, and reports in DuckDB. No backend writes. | Fast failure-taxonomy slicing and reproducible local analytics. | Creating a second store if it starts owning canonical data. |
| `Polars` | Tenn needs faster deterministic batch transforms over eval corpora and signal-audit tables. | `scripts/` or isolated eval utilities. | Use only for one-shot transforms feeding reports or audits. Keep it out of the core request path. | Cleaner, faster local batch data prep. | Dependency or style split if it spreads into runtime code. |
| `MLflow` | Tenn has many reports, but weak run lineage across prompt, routing, or extraction experiments. | Eval-only experiment wrappers. | Start with local `mlruns/` and log params, metrics, artifacts from extraction or routing experiments. No shared server yet. | Better experiment comparison and artifact lineage. | Premature serverization or MLOps overhead. |
| `DSPy` | Tenn needs a way to test structured prompt or program variants without touching production code paths. | Eval lane only. | Create a small sandbox runner that compares DSPy modules against current extraction or router behavior on frozen corpora. | More systematic prompt or program benchmarking. | Framework creep into the core pipeline. |
| `Chandra` | Extraction hardening still needs evidence on hard PDFs, tables, and OCR-heavy layouts. | Extraction eval and manual verification only. | Add an offline comparator script on the known hard document set; compare outputs against docling and current multipass results. | Clear evidence whether Chandra actually rescues current misses. | GPU or runtime cost and pressure to add it as an unproven production fallback. |
| Targeted `FMP` adapter | Tenn has real gaps in transcripts, profiles, and calendars for memory and supporting evidence. | Optional enrichment path. | Add one narrow provider for transcript, profile, and calendar retrieval, clearly tagged as external and non-canonical; likely touch `app/providers/`, `api/context.py`, `api/routes.py`, `context_loader.py`. | Better supporting evidence and market-memory context. | Cloud or API dependency and truth-boundary slippage. |
| Review or UI pattern pack | Tenn’s next bottleneck after measurement is human review speed. | `cockpit/ui/web.py`, chat or debug surfaces, research or report views. | Add cited-evidence panels, staged review states, and optional bull, bear, or risk sections without changing backend authority. | Faster semantic signal audits and grounded answer review. | UI scope creep. |
| `scikit-learn` baselines | Tenn needs non-LLM sanity baselines before overfitting prompt work. | Eval-only. | Build TF-IDF or classical baselines for duplicate detection, routing, or signal usefulness checks. | Cheap comparators that reveal when LLM complexity is unnecessary. | Baseline misuse if promoted as a hidden truth layer. |

### Single Recommendation Summary

1. Implement first:
   - `DuckDB`
   - `Polars`
   - `MLflow`
   - `scikit-learn` baselines
   - review or UI pattern borrowing
2. Investigate next:
   - `Chandra`
   - `DSPy`
   - targeted `FMP` adapter
   - `OpenBB` only through the existing sidecar wrapper pattern
3. Do not adopt as systems:
   - `deer-flow`
   - `hermes-agent`
   - `OpenAlice`
   - `TradingAgents`
   - `AI-Scientist-v2`

The highest-confidence answer to the core question is:

> Tenn should extend its eval and audit layer, not replace its architecture. The safest external additions are `DuckDB`, `Polars`, `MLflow`, selective `scikit-learn` baselines, and possibly `Chandra` and `DSPy` in tightly isolated eval sandboxes. Everything that looks like a new agent platform or trading runtime is either a pattern source only or blocked due to collision.
