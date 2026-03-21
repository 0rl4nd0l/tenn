# 14 — Roadmap and modules

This document defines the target **“Analyse Company”** pipeline as a set of modular phases, a proposed directory structure for future modules, and the invariant that all modules remain **deterministic** and **artifact-producing**.

---

## Target pipeline: Analyse Company

The pipeline is composed of phases that run in sequence. Each phase consumes inputs from prior phases and produces well-defined outputs (artifacts). No phase may introduce non-deterministic behavior or skip writing artifacts when it runs.

| Phase | Description | Key outputs |
|-------|-------------|-------------|
| **1. Data acquisition** | Ingest and normalize all inputs required for analysis: price data, fundamentals, regulatory filings, and news. | Canonical datasets, document store, staging tables/snapshots. |
| **2. Retrieval (RAG)** | Single entrypoint for semantic search over ingested documents. Query with optional ticker filter; return ranked hits. | RAG query results (hits), optional debug payloads. |
| **3. Analysis modules** | Domain-specific analysis run over acquired data and RAG context. Each module is independent and produces one or more artifacts. | Risk, valuation, moat, catalysts, ROIC, balance sheet, and other module-specific artifacts. |
| **4. Portfolio module** | Portfolio-level view: exposure, correlation, position sizing. Consumes analysis artifacts and optional portfolio definition. | Exposure/correlation/sizing reports. |
| **5. Outputs** | All artifacts are written under a single reports tree. Timestamped or versioned where appropriate. | Artifacts under `reports/` (see below). |

---

## Phase details

### 1. Data acquisition

- **Price:** Market data (e.g. OpenBB, EODHD) — time series, adjusted where applicable.
- **Fundamentals:** Normalized fundamentals from providers or extracted from filings.
- **Filings:** ASX announcements, annual/quarterly reports; PDF discovery, download, extract, chunk (see [04_ingestion_pipeline.md](04_ingestion_pipeline.md)).
- **News:** News items with source, date, ticker mapping; stored for retrieval and qualitative context.

Outputs feed the document store, vector index (for RAG), and any staging/snapshot tables used by analysis modules.

### 2. Retrieval (RAG)

- Single API: `POST /rag/query` (see [07_rag_contract.md](07_rag_contract.md)).
- Inputs: query text, optional ticker, top_k.
- Outputs: ordered list of hits (score, document_id, ticker, title, chunk_index, etc.). No side effects; deterministic for same query and index state.
- All embedding and vector store rules from [backend_architecture](../../.cursor/rules/backend_architecture.md) apply (Ollama, Qdrant, deterministic vector IDs).

### 3. Analysis modules

Each analysis module:

- Takes defined inputs (e.g. ticker, date range, RAG context, fundamentals, prices).
- Runs deterministic logic (no unsupported randomness; same inputs → same outputs).
- Writes one or more **artifacts** (e.g. JSON, CSV, or entries in a report bundle).

Proposed modules (non-exhaustive):

| Module | Purpose | Example artifacts |
|--------|---------|-------------------|
| Risk | Financial and operational risk signals from filings/metrics. | `reports/analysis/{ticker}/risk_signals.json` |
| Valuation | Valuation metrics and peer comparison. | `reports/analysis/{ticker}/valuation.json` |
| Moat | Qualitative/quantitative moat assessment. | `reports/analysis/{ticker}/moat.json` |
| Catalysts | Upcoming events, milestones, narrative drivers. | `reports/analysis/{ticker}/catalysts.json` |
| ROIC | Return on invested capital and trend. | `reports/analysis/{ticker}/roic.json` |
| Balance sheet | Leverage, liquidity, structure. | `reports/analysis/{ticker}/balance_sheet.json` |

Additional modules (sentiment, quality score, etc.) follow the same contract: deterministic, artifact-producing.

### 4. Portfolio module

- **Inputs:** Portfolio definition (positions or watchlist), analysis artifacts, correlation/exposure inputs.
- **Outputs:** Exposure by sector/region, correlation matrix or summary, position sizing suggestions. All written as artifacts under `reports/portfolio/` or similar.

### 5. Outputs (artifacts in `reports/`)

All pipeline outputs are written under a single tree. Existing and proposed locations:

| Area | Path pattern | Contents |
|------|--------------|----------|
| RAG / ops | `reports/rag_stability/`, `reports/vector_baseline.json`, `reports/runtime_embedding_model.txt` | Stability runs, baseline, model guard. |
| Weekly | `reports/weekly/` | Weekly intelligence pack JSON. |
| Analysis | `reports/analysis/` | Per-ticker or per-run analysis artifacts (risk, valuation, moat, etc.). |
| Portfolio | `reports/portfolio/` | Exposure, correlation, sizing. |
| Snapshots | `reports/snapshots/` | Point-in-time snapshots (e.g. agent context). |
| Qual context | `reports/qual_context/` | Qualitative context DBs and related outputs. |
| Other | `reports/asx/`, `reports/expansion_runs/`, etc. | Domain-specific runs and reports. |

Artifacts should be timestamped or versioned where reruns overwrite or need comparison (e.g. `reports/weekly/YYYYMMDD_HHMMSS.json`).

---

## Proposed directory structure for future modules

The following layout is **proposed** for where new analysis and pipeline code should live. This is a target structure; it is not fully implemented today.

```
financial-engine_v2/
├── backend/
│   ├── app/
│   │   ├── api/           # HTTP routes (existing)
│   │   ├── core/          # Config, shared (existing)
│   │   ├── models/        # DB and DTOs (existing)
│   │   ├── services/      # RAG, pipeline, embeddings (existing)
│   │   ├── providers/     # Data providers (existing)
│   │   │
│   │   └── modules/       # [PROPOSED] Analysis and portfolio modules
│   │       ├── __init__.py
│   │       ├── base.py    # Contract: run(ticker, context) -> ArtifactSet
│   │       ├── risk/
│   │       │   ├── __init__.py
│   │       │   └── module.py
│   │       ├── valuation/
│   │       ├── moat/
│   │       ├── catalysts/
│   │       ├── roic/
│   │       ├── balance_sheet/
│   │       └── portfolio/
│   │           ├── __init__.py
│   │           ├── exposure.py
│   │           ├── correlation.py
│   │           └── sizing.py
│   └── ...
├── reports/               # All artifacts (existing convention)
│   ├── analysis/
│   │   └── {ticker}/
│   ├── portfolio/
│   ├── weekly/
│   ├── rag_stability/
│   └── ...
└── ...
```

- **`modules/base.py`** would define the contract: e.g. `run(ticker, context) -> ArtifactSet`, where `ArtifactSet` lists paths under `reports/` and optional in-memory payloads.
- Each **module** (risk, valuation, moat, etc.) lives in its own package under `modules/`, implements the contract, and writes only under `reports/`.
- **Portfolio** is a separate top-level module under `modules/portfolio/` with sub-components (exposure, correlation, sizing) that produce artifacts under `reports/portfolio/`.

No implementation of this structure is implied here; it is a roadmap for where to place new code as modules are added.

---

## Invariant: deterministic, artifact-producing modules

- **Deterministic:** For the same inputs (ticker, date range, config, and upstream data), a module must produce the same outputs. No reliance on `uuid4()` or other non-deterministic IDs for artifacts; no unsupported randomness in business logic.
- **Artifact-producing:** Every module run must write at least one artifact under `reports/` (or a configured output root). Artifacts are the canonical record of the run and enable audit, comparison, and reuse by downstream phases (e.g. portfolio module consuming analysis artifacts).

These rules align with the existing [backend architecture](../../.cursor/rules/backend_architecture.md) (idempotency, deterministic vector IDs, no silent degradation) and ensure the Analyse Company pipeline remains reproducible and auditable.

---

## Future Capability: Autonomous Dev Optimization Loop

**Status:** Deferred. Not implemented. Decision record only.
**Full evaluation:** [docs/research/autoresearch_evaluation.md](../research/autoresearch_evaluation.md)

### What it is

A bounded, development-side experiment loop that autonomously sweeps parameters for a single subsystem, measures the effect against a deterministic eval metric, and retains improvements. Conceptually: try → measure → keep/discard → log → repeat.

Inspired by the pattern in `karpathy/autoresearch` and `davebcn87/pi-autoresearch`, but neither repo is suitable for direct adoption. A Tenn-native implementation would be built if and when prerequisites are met.

### Why it is deferred

The primary prerequisite does not yet exist: a fast, stable, deterministic eval harness covering each candidate subsystem (routing weights, retrieval parameters, extraction quality, latency). Without a valid metric to optimize, an experiment loop produces no reliable signal.

Secondary constraint: this capability must never touch the production financial-agent runtime. Financial reasoning must remain auditable and deterministic. Any implementation must operate in development/shadow mode only.

### When to consider implementing

Revisit this decision when ALL of the following are true:

1. At least one candidate subsystem has a deterministic eval harness with a scalar metric (e.g., routing: latency P95 + accuracy on labeled dataset; retrieval: NDCG on canonical eval set).
2. The eval harness runs in under 10 minutes end-to-end.
3. The eval harness is stable across reruns (variance < 5% on same inputs).
4. There is a specific, measurable optimization goal (e.g., "reduce routing P95 by 20% without accuracy regression").
5. A human reviewer is available to approve any experiment result before it is applied.

### Candidate subsystems (priority order)

| Subsystem | Candidate metric | Config surface |
|-----------|-----------------|----------------|
| Model routing thresholds | Latency P95 + accuracy on labeled queries | `model_routing.yaml` score weights |
| Retrieval parameters | NDCG on canonical RAG eval set | `top_k`, score cutoff in RAG config |
| Extraction quality | Precision/recall on labeled financial extraction set | Prompt templates in `services/extraction.py` |
| Latency/cost tradeoffs | Wall-clock time + token cost per pipeline run | Routing config + model selection |

### Safety boundaries (non-negotiable)

- **Dev-only:** Experiment loops run only in isolated dev environments against frozen eval datasets. Never in production runtime.
- **Human-in-the-loop required:** No experiment result is auto-applied. All results require human review and explicit approval before any config change is committed.
- **Append-only logs:** All experiment runs are logged to a JSONL file. Logs are never deleted or modified.
- **Backpressure gate required:** Full validation gate set (`pytest` + ruff + smoke) must pass before any result is marked `keep`.
- **Frozen eval data:** The eval dataset used during an optimization session must not change mid-session.
- **Prohibited targets:** Production prompts for final investment reasoning, DB schema, benchmark definitions, and the optimization loop itself are never mutable targets.

### Rollout phases (if approved)

1. **Phase 0 — Eval harness prerequisite:** Build and validate a fast, deterministic eval harness for one subsystem. Gate: harness runs in <10 min, <5% variance across 3 reruns.
2. **Phase 1 — Manual experiment loop:** A developer manually runs parameter sweeps using the harness and logs results in `reports/optim_sessions/`. No automation. Gate: 3+ successful manual sessions with documented improvements.
3. **Phase 2 — Scripted loop:** Automate the try/measure/log cycle in a CLI script (`scripts/optim_loop.py`). Human reviews results before any config change. Gate: script produces correct JSONL output; backpressure gate passes on all kept results.
4. **Phase 3 — Agent-assisted (optional):** Allow a Claude agent to propose parameter deltas in the scripted loop. Human still approves before commit. Gate: agent proposals are no worse than manual on held-out eval set.

### Kill-switch / disable conditions

- Remove or rename `scripts/optim_loop.py` to disable the scripted loop.
- Delete the session's `autoresearch.md` equivalent to reset loop state.
- Any validation gate failure on a `keep` result immediately halts the session.
- Production deployment never depends on optimization loop state.
