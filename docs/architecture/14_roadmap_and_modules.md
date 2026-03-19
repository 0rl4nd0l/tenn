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
