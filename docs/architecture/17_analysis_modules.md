# 17 — Analysis Modules (Phase 3)

This document is the canonical reference for the Phase 3 analysis module system: architecture, module contracts, data flow, orchestration, and quality assurance. It supersedes the "proposed" section of [14_roadmap_and_modules.md](14_roadmap_and_modules.md) for everything that is now implemented.

---

## 1. Overview

### What Phase 3 Is

Phase 3 ("Analysis modules") is the third stage of the five-phase Analyse Company pipeline defined in [14_roadmap_and_modules.md](14_roadmap_and_modules.md):

| Phase | Role |
|-------|------|
| 1. Data acquisition | Ingest price, fundamentals, filings, news |
| 2. Retrieval (RAG) | Semantic search over ingested documents |
| **3. Analysis modules** | **Domain-specific analysis over acquired data and RAG context** |
| 4. Portfolio module | Portfolio-level exposure, correlation, sizing |
| 5. Outputs | Artifact tree under `reports/` |

Phase 3 consumes structured financial data (from Phase 1 extraction), optional RAG evidence (from Phase 2), and optional market price data. It produces per-ticker analysis artifacts covering balance sheet health, return on capital, valuation, risk, catalysts, and competitive moat.

### What Problem It Solves

Raw financial data and document chunks are not actionable on their own. Phase 3 transforms them into structured analytical judgements: leverage risk classifications, valuation signals, moat assessments, risk scores, catalyst identification. These artifacts are machine-readable (JSON), auditable (evidence chains), and composable (downstream consumers like the portfolio module or report generator can combine them).

### Design Principles

1. **Stateless modules.** All state flows through `TickerContext` (input) and `ArtifactSet` (output). Modules have no side effects beyond logging.
2. **Immutable data.** All dataclasses are `frozen=True`. No mutation of inputs or outputs.
3. **Graceful degradation.** Missing data produces `PARTIAL` results, not crashes. Only total absence of minimum-viability data produces `FAILED`.
4. **Evidence chains.** Every claim traces to a source: financial statement, computed metric, or RAG hit.
5. **LLM synthesis is optional.** Hybrid modules always produce D1 (deterministic) output. D2 (LLM narrative) is additive and structurally validated.

---

## 2. Architecture

### 2.1 The Two-Layer Model (D1 + D2)

Every module has a **D1 (deterministic) layer** that always runs. Three hybrid modules additionally have a **D2 (LLM synthesis) layer** that runs only when an LLM endpoint is configured.

```
                    ┌──────────────────────────────────────────┐
                    │             AnalysisModule                │
                    │                                          │
                    │  ┌──────────────────────────────────┐    │
                    │  │  D1: Deterministic Computation    │    │
                    │  │  - Always runs                    │    │
                    │  │  - Null-safe math (math_utils)    │    │
                    │  │  - Signal classification          │    │
                    │  │  - Trend computation              │    │
                    │  └──────────────┬─────────────────────┘    │
                    │                │                          │
                    │  ┌─────────────▼────────────────────┐    │
                    │  │  D2: LLM Synthesis (optional)     │    │
                    │  │  - Only when llm_base_url set     │    │
                    │  │  - Receives D1 output + RAG       │    │
                    │  │  - Structurally validated          │    │
                    │  │  - Produces Narrative              │    │
                    │  └──────────────────────────────────┘    │
                    └──────────────────────────────────────────┘
```

| Module | D1 | D2 |
|--------|----|----|
| balance_sheet | Yes | No |
| roic | Yes | No |
| valuation | Yes | No |
| risk | Yes | Yes |
| catalysts | Yes | Yes |
| moat | Yes | Yes |

**D1 guarantees:** Same inputs produce same outputs. Testable with unit tests. No network calls. No randomness.

**D2 guarantees:** Structural validation of LLM output (required fields, enum values, score recalculation). Prompt hash recorded for cache/audit. Failure falls back to D1-only output with a warning -- never crashes.

### 2.2 The AnalysisModule Protocol

All modules implement the `AnalysisModule` Protocol (structural subtyping, not inheritance):

```python
@runtime_checkable
class AnalysisModule(Protocol):
    @property
    def name(self) -> str: ...          # e.g. "balance_sheet"

    @property
    def requires(self) -> frozenset[str]: ...  # e.g. {"financials", "price"}

    def run(self, context: TickerContext) -> ArtifactSet: ...
```

**Why Protocol, not ABC:** The codebase is function-oriented. Structural subtyping lets classes satisfy the interface by shape alone, without requiring explicit inheritance. The orchestrator depends only on the Protocol; modules optionally use `ModuleHelpers` as a mixin for convenience methods (`_build_artifact`, `_check_minimum_viability`).

### 2.3 TickerContext: Selective-Fat Frozen Context

`TickerContext` is a fully frozen (`frozen=True`) dataclass assembled by `TickerContextLoader`. It carries all data a module might need, but the loader only fetches what is requested via `ContextRequest`.

```python
@dataclass(frozen=True)
class TickerContext:
    ticker: str
    assembled_at: datetime

    financials: FinancialSummary | None    # Multi-period with trends
    risk_notes: tuple[RiskNote, ...]       # From asx_risk_notes
    documents: tuple[DocumentRef, ...]     # Lightweight doc refs
    price: PriceSnapshot | None            # Latest close price
    rag_results: tuple[RAGResult, ...]     # Labeled RAG hit sets
    warnings: tuple[str, ...]              # Assembly warnings
```

**Selective-fat pattern:** Modules declare their needs via `ContextRequest` (e.g., `needs_price=True`, `rag_queries=(...)`). The orchestrator merges all module requests into a single `ContextRequest` and the loader pre-fetches exactly what is needed. The resulting context is frozen -- modules cannot mutate it.

**Multi-period data:** `FinancialSummary` contains an oldest-first tuple of `PeriodMetrics` with `.latest` and `.prior` accessors, plus pre-computed `TrendMetrics` (YoY deltas) and a composite `financial_health_score`.

**RAG access:** Modules access RAG results by label via `context.rag_by_label("competitive_position")`. RAG queries are declared upfront in `ContextRequest` and executed by the loader, not the module.

### 2.4 ArtifactSet: The Universal Return Type

Every module returns exactly one `ArtifactSet`:

```python
@dataclass(frozen=True)
class ArtifactSet:
    ticker: str
    module_name: str
    completeness: Completeness           # COMPLETE | PARTIAL | FAILED
    structured: dict[str, Any]           # D1 metrics and signals
    evidence: tuple[EvidenceItem, ...]   # Source chain
    narrative: Narrative | None          # D2 output (hybrid modules only)
    warnings: tuple[str, ...]            # Data gaps, D2 failures, etc.
    computed_at: str                     # ISO 8601 UTC timestamp
```

**Evidence chain:** Each `EvidenceItem` carries an `evidence_id`, `source_type` (one of `financial_statement`, `rag_hit`, `news`, `computed`), `content`, `source_id`, and `confidence` score. This enables audit-ready output where every claim can be traced to its source.

**Narrative:** The `Narrative` dataclass (D2 only) carries `summary`, `detail` (structured dict), `model_id`, `prompt_hash` (SHA-256 prefix for cache keying and audit), and `cached` flag.

### 2.5 Dependency Graph

```
            ┌─────────────────┐
            │  balance_sheet   │  Tier 1 (no upstream deps)
            └────────┬────────┘
                     │
     ┌───────┬───────┼───────┬───────┐
     │       │       │       │       │
  ┌──▼──┐ ┌─▼──┐ ┌──▼──┐ ┌─▼──────┐│
  │ roic │ │risk│ │valu-│ │catalyst││
  │      │ │    │ │ation│ │   s    ││
  └──────┘ └────┘ └─────┘ └────────┘│  Tier 2 (independent)
                                     │
            ┌────────────────┐       │
            │      moat      │◄──────┘  Tier 3 (benefits from upstream)
            └────────────────┘
```

The orchestrator executes tiers in order. Modules within a tier are independent and could be parallelized in a future optimization. Currently, they run sequentially within each tier.

---

## 3. Module Reference

### 3.1 Balance Sheet Module

**File:** `balance_sheet.py` (285 lines)
**Type:** D1 only (no LLM)
**Question answered:** "Is the company's balance sheet healthy? What are the leverage, liquidity, and FCF trajectory?"

#### Inputs

- `financials` (required): Multi-period `PeriodMetrics` with `net_debt`, `ebit`, `operating_cf`, `capex`, `cash_end`

#### Metrics Computed

| Metric | Formula | Purpose |
|--------|---------|---------|
| `fcf` | `operating_cf - abs(capex)` | Free cash flow |
| `net_debt_to_ebit` | `net_debt / ebit` (when ebit > 0) | Leverage ratio |
| `debt_to_fcf` | `net_debt / fcf` (when fcf > 0) | Debt serviceability |
| `cash_runway_quarters` | `cash_end / abs(operating_cf)` (when OCF < 0) | Burn rate survival |
| `net_cash_position` | `net_debt < 0` | Boolean flag |

Period-over-period deltas are computed for `net_debt`, `fcf`, and `net_debt_to_ebit`.

#### Trajectory

- `net_debt_direction`: improving / stable / deteriorating (inverted: decreasing debt = improving)
- `net_debt_slope_per_period`: Linear regression slope across periods
- `fcf_direction`: improving / stable / deteriorating
- `fcf_positive_periods` / `fcf_negative_periods`: Counts

#### Signals Emitted

| Signal | Values | Thresholds |
|--------|--------|------------|
| `leverage_risk` | low / moderate / high / critical / unknown | Net debt/EBIT: <1.5 low, <3.0 moderate, <5.0 high, >=5.0 critical; net cash = low; debt + no EBIT = critical |
| `liquidity_risk` | low / moderate / high / critical / unknown | OCF >= 0 = low; runway: >8Q low, >4Q moderate, >2Q high, <=2Q critical |
| `fcf_coverage_signal` | strong / adequate / weak / none / unknown | Debt/FCF: <3 strong, <6 adequate, <10 weak, >=10 none; FCF <= 0 = none |
| `debt_trajectory_signal` | improving / stable / deteriorating / insufficient_data | From net_debt_direction |

#### Completeness Conditions

- **COMPLETE:** `net_debt_to_ebit`, `debt_to_fcf`, and `fcf` are all non-None for the latest period
- **PARTIAL:** One or more of the above are None
- **FAILED:** No financial periods available in context

#### Artifact Schema (abridged)

```json
{
  "schema_version": "1.0",
  "ticker": "BHP",
  "module": "balance_sheet",
  "completeness": "complete",
  "periods": [
    {
      "period_end": "2024-06-30",
      "period_type": "A",
      "net_debt": 12800000000,
      "ebit": 15200000000,
      "fcf": 8500000000,
      "net_debt_to_ebit": 0.8421,
      "debt_to_fcf": 1.5059,
      "cash_runway_quarters": null,
      "net_cash_position": false,
      "deltas": {
        "net_debt_change_abs": -1200000000,
        "net_debt_change_pct": -0.0857
      }
    }
  ],
  "trajectory": {
    "net_debt_direction": "improving",
    "net_debt_slope_per_period": -600000000,
    "fcf_direction": "stable",
    "fcf_positive_periods": 5,
    "fcf_negative_periods": 0
  },
  "signals": {
    "leverage_risk": "low",
    "liquidity_risk": "low",
    "debt_trajectory_signal": "improving",
    "fcf_coverage_signal": "strong"
  },
  "data_quality": {
    "fields_present": ["net_debt", "ebit", "operating_cf", "capex", "cash_end"],
    "fields_missing": [],
    "min_confidence": 0.85,
    "avg_confidence": 0.91
  }
}
```

---

### 3.2 ROIC Module

**File:** `roic.py` (218 lines)
**Type:** D1 only (no LLM)
**Question answered:** "Is the company earning an adequate return on its invested capital? Is the trend improving or declining?"

#### Inputs

- `financials` (required): Annual periods with `ebit`, `revenue`, `net_debt`, `shares_outstanding`
- `price` (optional): Used to compute market cap proxy for invested capital

#### Metrics Computed

| Metric | Formula | Purpose |
|--------|---------|---------|
| `nopat` | `ebit * (1 - tax_rate)` | Net operating profit after tax |
| `invested_capital` | `market_cap_proxy + net_debt` | IC (proxy -- see note) |
| `ebit_on_ic` | `ebit / invested_capital` | Pre-tax ROIC |
| `nopat_on_ic` | `nopat / invested_capital` | Post-tax ROIC |
| `capital_turnover` | `revenue / invested_capital` | Asset efficiency |

**Note on IC proxy:** Total equity is not currently in the extraction schema. Invested capital uses `(price * shares_outstanding) + net_debt` as a market-cap-based proxy. This is a known limitation (see section 8).

#### Trend

- `ebit_on_ic_delta`: Period-over-period change in pre-tax ROIC
- `nopat_on_ic_delta`: Period-over-period change in post-tax ROIC
- `direction`: improving / stable / declining / insufficient_data (5% threshold)

#### Summary Signals

- `roic_above_10pct`: Boolean. Whether latest NOPAT/IC exceeds 10% (the default ROIC hurdle).
- `coverage_years`: List of years for which ROIC could be computed.

#### Completeness Conditions

- **COMPLETE:** `ebit_on_ic`, `nopat_on_ic`, and `capital_turnover` all non-None for latest period
- **PARTIAL:** One or more core metrics are None (typically due to missing price/shares for IC)
- **FAILED:** No financial data or no annual periods available

---

### 3.3 Valuation Module

**File:** `valuation.py` (211 lines)
**Type:** D1 only (no LLM)
**Question answered:** "Is the company cheap, fairly valued, or expensive based on earnings, cash flow, and enterprise value multiples?"

#### Inputs

- `financials` (required): Latest period with `np_attributable`, `ebit`, `revenue`, `operating_cf`, `capex`, `net_debt`, `shares_outstanding`
- `price` (required): Latest close price

#### Metrics Computed

| Metric | Formula |
|--------|---------|
| `market_cap` | `price * shares_outstanding` |
| `enterprise_value` | `market_cap + net_debt` |
| `pe_ratio` | `market_cap / np_attributable` (when NP > 0) |
| `earnings_yield_pct` | `(np_attributable / market_cap) * 100` |
| `ev_ebit` | `enterprise_value / ebit` (when EBIT > 0) |
| `ev_revenue` | `enterprise_value / revenue` |
| `ev_ocf` | `enterprise_value / operating_cf` (when OCF > 0) |
| `p_fcf` | `market_cap / fcf` (when FCF > 0) |
| `fcf_yield_pct` | `(fcf / market_cap) * 100` |
| `eps` | `np_attributable / shares_outstanding` |
| `fcf_per_share` | `fcf / shares_outstanding` |

#### Signals Emitted

Each metric is classified as `cheap`, `fair`, or `expensive`:

| Metric | Cheap | Expensive |
|--------|-------|-----------|
| `pe_ratio` | < 12 | > 25 |
| `ev_ebit` | < 8 | > 16 |
| `fcf_yield_pct` | > 8% (inverted) | < 4% (inverted) |
| `ev_revenue` | < 2 | > 6 |

**Composite signal:** Majority vote across available per-metric signals. Ties broken in order: cheap > fair > expensive.

#### Completeness Conditions

- **COMPLETE:** All 12 multiples are non-None
- **PARTIAL:** One or more multiples are None
- **FAILED:** No price data, invalid price (<=0), no financial data, or no latest period

---

### 3.4 Risk Module

**File:** `risk.py` (335 lines)
**Type:** Hybrid D1 + D2
**Question answered:** "What are the material risks facing this company, how severe are they, and are they improving or worsening?"

#### Inputs

- `financials` (required for D1): Latest period + trends for stress signal computation
- `risk_notes` (required for D1): Risk summaries and bullets from `asx_risk_notes`
- `rag_results` (optional, for D2): RAG hits labeled for risk context

#### D1: Deterministic Risk Assessment

**Risk item extraction:** Walks `risk_notes`, collects `risk_summary` and each `risk_bullet` as individual text items with `source_type` and `document_id`.

**Stress signals:** Computed from latest period financials with these thresholds:

| Signal | Severity | Threshold |
|--------|----------|-----------|
| `low_cash_conversion` | medium | Cash conversion < 0.50 |
| `revenue_declining` | high | Revenue YoY < -10% |
| `high_leverage` | high | Net debt/EBIT > 3.0x |
| `negative_fcf` | medium | FCF < 0 |
| `low_cash_runway` | critical | Cash runway < 4 quarters |

**Risk score:** Aggregate 0-100. Base: `min(risk_item_count * 5, 50)`. Signal weights: critical=20, high=12, medium=6, low=3. Capped at 100.

**Trajectory:** Derived from YoY trends (revenue, EBIT, FCF). Majority of deltas > +5% = improving; majority < -5% = deteriorating; else stable.

#### D2: LLM Risk Synthesis

**When:** `llm_base_url` is provided.

**Prompt design:** Receives D1 risk items, stress signals, and up to 15 RAG evidence snippets (capped at 500 chars each). Requests structured JSON:
- `risk_items`: 3-7 objects with `category` (operational/financial/regulatory/macro/strategic), `severity` (critical/high/medium/low), `description`
- `risk_interactions`: 0-3 objects describing compounding risk pairs
- `risk_summary`: 2-4 sentence narrative

**Failure mode:** D2 failure produces a `d2_synthesis_failed` warning; D1 output is returned unchanged.

#### Completeness Conditions

- **COMPLETE:** At least one risk item or stress signal was identified
- **PARTIAL:** Neither risk items nor stress signals available (sparse data)
- **FAILED:** No financial data available at all

---

### 3.5 Catalysts Module

**File:** `catalysts.py` (283 lines)
**Type:** Hybrid D1 + D2
**Question answered:** "What upcoming events or trends could materially move the share price, and in which direction?"

#### Inputs

- `financials` (at least one of financials or risk_notes required): Period metrics for momentum signals
- `risk_notes` (at least one of financials or risk_notes required): Guidance and material change items
- `rag_results` (optional, for D2): RAG hits across five labeled queries (`catalyst_guidance`, `catalyst_strategy`, `catalyst_outlook`, `catalyst_regulatory`, `catalyst_corporate_action`)

#### D1: Guidance and Momentum Extraction

**Guidance extraction:** Collects `guidance_summary` and `material_changes` from risk notes.

**Momentum signals:** Period-over-period analysis with thresholds:

| Signal | Condition | Description |
|--------|-----------|-------------|
| `potential_earnings_beat` | Revenue YoY > 10% | Revenue growth suggests potential beat |
| `margin_expansion` | EBIT YoY > 15% | EBIT growth indicates margin expansion |
| `possible_capital_return` | FCF YoY > 20% | FCF acceleration signals possible capital return |
| `ma_or_buyback_capacity` | Net debt < 0 (net cash) | Net cash provides M&A or buyback capacity |

#### D2: LLM Catalyst Identification

**When:** `llm_base_url` is provided.

**Prompt design:** Receives guidance items, momentum signals, and RAG evidence. Requests structured JSON:
- `catalysts`: 2-6 objects with `title`, `category` (earnings/corporate_action/regulatory/macro/operational/market), `timeframe` (near_term/medium_term/long_term), `probability` (high/medium/low), `impact_direction` (positive/negative/ambiguous), `description`, `evidence_ids`
- `catalyst_summary`: 2-3 sentence outlook
- `upcoming_events`: List of `{event, expected_timeframe}` objects

**Evidence linking:** D2 catalysts reference `evidence_ids` that trace back to RAG hits and computed signals, enabling provenance auditing.

#### Completeness Conditions

- **COMPLETE:** At least one guidance item or momentum signal was identified
- **PARTIAL:** Neither guidance nor momentum available (sparse data)
- **FAILED:** Both financials and risk_notes are missing

---

### 3.6 Moat Module

**File:** `moat.py` (292 lines)
**Type:** Hybrid D1 + D2
**Question answered:** "Does this company have a durable competitive advantage, and how strong is it?"

#### Inputs

- `financials` (required): Multi-period `PeriodMetrics` for quantitative moat signal computation
- `rag_results` (optional, for D2): RAG hits labeled `competitive_position`

#### D1: Quantitative Moat Signals

Six signals computed from financial period data:

| Signal | Method | Assessment Values |
|--------|--------|-------------------|
| `margin_stability` | EBIT margin stdev + mean across periods | stable (sd<0.03, mean>0.10) / volatile / low |
| `roic_proxy` | EBIT/revenue ratio for latest period | high (>0.15) / stable / low (<0.05) |
| `capex_intensity` | abs(capex)/revenue ratio | low (<0.05) / stable / high (>0.15) |
| `revenue_persistence` | Worst YoY revenue change across periods | stable (>-5%) / low / volatile (<-15%) |
| `cash_conversion_consistency` | Cash conversion stdev across periods | stable (sd<0.15) / volatile |
| `fcf_margin_trend` | First-to-last FCF margin delta | high (>+2pp) / stable / low (<-2pp) |

If 4 or more signals return `insufficient_data`, a warning is emitted.

#### D2: Morningstar 5-Source Framework

**When:** `llm_base_url` is provided.

**Prompt design:** Receives D1 quantitative signals (JSON) and RAG documentary evidence. Uses the Morningstar 5-source moat framework:

1. **Network effects** -- Does usage by one customer increase value for others?
2. **Switching costs** -- How costly is it for customers to switch?
3. **Cost advantages** -- Does the company have structural cost advantages?
4. **Intangible assets** -- Brands, patents, regulatory licenses
5. **Efficient scale** -- Does the company serve a market of limited size?

For each source, the LLM assesses: `present` (bool), `strength` (strong/moderate/weak/absent), `evidence_summary`.

**Structural validation of LLM output:** The module does not trust LLM arithmetic. It recalculates:
- `moat_classification`: Deterministic from source strengths. Wide = 2+ strong OR 1 strong + 2 moderate. Narrow = 1 strong OR 2+ moderate. None = otherwise.
- `moat_score`: 0-100, each source scored: strong=20, moderate=12, weak=5, absent=0.
- `moat_confidence` and `moat_trend` are validated against allowed enum values.

Missing or malformed source entries are replaced with `{present: false, strength: "absent"}`.

#### Completeness Conditions

- **COMPLETE:** `moat_classification` is non-None (requires successful D2)
- **PARTIAL:** D1 signals computed but D2 did not run or failed
- **FAILED:** No financial periods available

---

## 4. Orchestration

### 4.1 AnalysisOrchestrator

The `AnalysisOrchestrator` class (`orchestrator.py`, 209 lines) manages module instantiation, dependency-ordered execution, and artifact writing.

#### Module Registry

The orchestrator builds a registry of all 6 modules at construction time. D1-only modules are instantiated with no arguments. Hybrid modules receive `llm_base_url` and `llm_model`:

```python
{
    "balance_sheet": BalanceSheetModule(),
    "roic": ROICModule(),
    "valuation": ValuationModule(),
    "risk": RiskModule(llm_base_url=..., llm_model=...),
    "catalysts": CatalystsModule(llm_base_url=..., llm_model=...),
    "moat": MoatModule(llm_base_url=..., llm_model=...),
}
```

#### Dependency-Ordered Execution

Modules are organized into three tiers executed in order:

```
Tier 1:  balance_sheet
Tier 2:  roic, risk, valuation, catalysts  (independent)
Tier 3:  moat
```

Each module runs independently within its tier. A failing module does not block others -- exceptions are caught and a `FAILED` ArtifactSet is produced with warning `module_raised_exception`.

#### Exception Isolation

Every module call is wrapped in a try/except. On unhandled exception:
1. The exception is logged with full traceback
2. A `FAILED` ArtifactSet is created with `structured={"error": "unhandled exception"}`
3. Execution continues to the next module

Artifact writing failures are also isolated -- a failed write does not prevent the result from being returned.

### 4.2 analyse_ticker() Entry Point

The top-level `analyse_ticker()` function is the single entry point for running all modules against a ticker:

```python
def analyse_ticker(
    ticker: str,
    *,
    db: Session,
    llm_base_url: str | None = None,
    llm_model: str = "",
    reports_root: str | None = None,
) -> list[ArtifactSet]:
```

Internally:
1. Creates an `AnalysisOrchestrator` with LLM config
2. Merges all module `requires` sets into a single `ContextRequest`
3. Calls `TickerContextLoader.load()` to assemble the frozen `TickerContext`
4. Calls `orchestrator.run_all()` to execute all modules
5. Returns the list of `ArtifactSet` results

### 4.3 Artifact Writing

After each module run, the orchestrator calls `write_artifact()` which:
1. Resolves the canonical path: `{reports_root}/analysis/{ticker}/{module_name}.json`
2. Serializes the ArtifactSet to JSON with metadata (schema version, git commit/branch, module version)
3. Writes atomically: writes to a temp file in the same directory, then `os.replace()` to the final path
4. Includes evidence, narrative (if present), and warnings in the output

---

## 5. Data Flow

### 5.1 Pipeline Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                            │
│                                                                  │
│  ┌──────────────────┐  ┌─────────────┐  ┌───────────────────┐   │
│  │asx_periodic_     │  │asx_risk_    │  │openbb_snapshots   │   │
│  │financials        │  │notes        │  │(price)            │   │
│  │                  │  │             │  │                   │   │
│  │ revenue, ebit,   │  │ risk_summary│  │ payload.close     │   │
│  │ np_attributable, │  │ risk_bullets│  │ payload.currency  │   │
│  │ operating_cf,    │  │ guidance    │  │ provider          │   │
│  │ capex, net_debt, │  │ material_   │  │ captured_at       │   │
│  │ shares, cash_end │  │ changes     │  │                   │   │
│  └────────┬─────────┘  └──────┬──────┘  └────────┬──────────┘   │
│           │                   │                   │              │
│  ┌────────┴───────────────────┴───────────────────┴──────────┐   │
│  │                                                           │   │
│  │documents (document_id, ticker, title, published_at)       │   │
│  │                                                           │   │
│  └───────────────────────────┬───────────────────────────────┘   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   TICKER CONTEXT LOADER                          │
│                                                                  │
│  ContextRequest (merged from all modules)                        │
│  ┌──────────────────────────────────────────────────────┐        │
│  │ needs_financials: true   needs_price: true           │        │
│  │ needs_risk_notes: true   needs_documents: true       │        │
│  │ period_type: "A"         max_periods: 5              │        │
│  │ rag_queries: (optional RAG specs)                    │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                  │
│  Queries DB ──► compute_period_metrics() ──► compute_trends()    │
│  ──► score_financial_health() ──► assembles frozen TickerContext  │
│                                                                  │
│  Optional: RAG callback ──► executes declared queries            │
│                                                                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
                     ┌──────────────────┐
                     │  TickerContext    │  (frozen, immutable)
                     └────────┬─────────┘
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
     ┌─────────────┐  ┌────────────┐  ┌──────────────┐
     │   Tier 1    │  │  Tier 2    │  │   Tier 3     │
     │             │  │            │  │              │
     │balance_sheet│  │roic, risk, │  │    moat      │
     │             │  │valuation,  │  │              │
     │             │  │catalysts   │  │              │
     └──────┬──────┘  └─────┬──────┘  └──────┬───────┘
            │               │                │
            ▼               ▼                ▼
     ┌──────────────────────────────────────────────┐
     │              ArtifactSet[]                    │
     │  (one per module, with evidence + narrative)  │
     └───────────────────────┬──────────────────────┘
                             │
                             ▼
     ┌──────────────────────────────────────────────┐
     │           Artifact Writer                     │
     │                                              │
     │  reports/analysis/{ticker}/                   │
     │  ├── balance_sheet.json                       │
     │  ├── roic.json                                │
     │  ├── valuation.json                           │
     │  ├── risk.json                                │
     │  ├── catalysts.json                           │
     │  └── moat.json                                │
     └──────────────────────────────────────────────┘
```

### 5.2 Data Sources Per Module

| Module | asx_periodic_financials | asx_risk_notes | openbb_snapshots | documents | RAG |
|--------|:----------------------:|:--------------:|:----------------:|:---------:|:---:|
| balance_sheet | required | -- | -- | -- | -- |
| roic | required (annual) | -- | optional | -- | -- |
| valuation | required | -- | required | -- | -- |
| risk | required | required | -- | -- | optional (D2) |
| catalysts | required* | required* | -- | -- | optional (D2) |
| moat | required | -- | -- | -- | optional (D2) |

\* Catalysts requires at least one of financials or risk_notes.

---

## 6. Quality Assurance

### 6.1 D1: Deterministic Testing

The D1 layer is fully deterministic and testable without any external dependencies. The test suite (`backend/tests/test_analysis_modules.py`) contains **43 tests** covering:

- All 6 modules with happy-path and edge-case inputs
- Null/missing field handling for every math function
- Signal classification boundary conditions
- Completeness state transitions (COMPLETE, PARTIAL, FAILED)
- Trend computation with insufficient data
- Evidence chain construction
- Artifact serialization round-trips

All math operations go through `math_utils.py` which provides null-safe wrappers: `ratio()`, `pct_change()`, `safe_sub()`, `safe_add()`, `safe_mul()`, `mean()`, `stdev()`, `linear_slope()`, `classify_direction()`. Every function returns `None` on missing input rather than raising. This eliminates `TypeError` / `ZeroDivisionError` throughout the module code.

### 6.2 D2: Structural Validation

LLM outputs are structurally validated before being used:

- **Risk module:** Checks that D2 returns a dict; extracts expected keys; falls back to D1-only on non-dict or exception.
- **Catalysts module:** Validates dict type; extracts `catalysts`, `upcoming_events`, `catalyst_summary` with safe `.get()` defaults.
- **Moat module:** Full structural validation:
  - Ensures all 5 source keys exist; fills missing sources with `{present: false, strength: "absent"}`
  - Validates `strength` enum membership; replaces invalid values with `"absent"`
  - Recalculates `moat_classification` and `moat_score` deterministically (does not trust LLM arithmetic)
  - Validates `moat_confidence` and `moat_trend` against allowed enums

### 6.3 Completeness Enum

The `Completeness` enum provides graceful degradation:

| Value | Meaning | When |
|-------|---------|------|
| `COMPLETE` | All expected fields populated, no data gaps | All required inputs present, all metrics computed |
| `PARTIAL` | Module ran but some metrics are None | Missing optional data (e.g., no price for ROIC IC computation) |
| `FAILED` | Minimum-viability check failed | Required data entirely absent (no financials, no price, etc.) |

This allows downstream consumers (report generator, portfolio module, cockpit) to decide how to handle partial results without needing to inspect individual fields.

### 6.4 Cache Strategy (D2)

Each D2 `Narrative` includes a `prompt_hash` (SHA-256 of the full prompt, truncated to 16 hex chars). This enables:
- **Cache keying:** Same prompt + same model = same hash. A cache layer (not yet implemented) can use this to skip redundant LLM calls.
- **Audit trail:** The hash uniquely identifies the exact prompt that produced a given narrative, enabling reproducibility auditing.
- **Staleness detection:** When upstream data changes, the prompt changes, the hash changes, and any cache entry is automatically invalidated.

---

## 7. Configuration

### 7.1 Signal Thresholds

**Balance sheet:**

| Signal | Threshold | Value |
|--------|-----------|-------|
| Leverage (low) | Net debt/EBIT | < 1.5 |
| Leverage (moderate) | Net debt/EBIT | 1.5 - 3.0 |
| Leverage (high) | Net debt/EBIT | 3.0 - 5.0 |
| Leverage (critical) | Net debt/EBIT | >= 5.0 |
| Liquidity (low) | Cash runway | > 8 quarters |
| Liquidity (moderate) | Cash runway | 4-8 quarters |
| Liquidity (high) | Cash runway | 2-4 quarters |
| Liquidity (critical) | Cash runway | < 2 quarters |
| FCF coverage (strong) | Debt/FCF | < 3 |
| FCF coverage (adequate) | Debt/FCF | 3-6 |
| FCF coverage (weak) | Debt/FCF | 6-10 |

**Valuation:**

| Metric | Cheap | Expensive |
|--------|-------|-----------|
| P/E ratio | < 12 | > 25 |
| EV/EBIT | < 8 | > 16 |
| FCF yield % | > 8% | < 4% |
| EV/Revenue | < 2 | > 6 |

Valuation thresholds can be overridden via the `thresholds` keyword argument to `ValuationModule.run()`.

**Risk stress signals:**

| Signal | Threshold |
|--------|-----------|
| Cash conversion (low) | < 0.50 |
| Revenue decline | < -10% YoY |
| High leverage | Net debt/EBIT > 3.0x |
| Low cash runway | < 4 quarters |

**Moat D1 signals:**

| Signal | Thresholds |
|--------|-----------|
| Margin stability (stable) | stdev < 0.03, mean > 0.10 |
| ROIC proxy (high) | EBIT/revenue > 0.15 |
| Capex intensity (low) | abs(capex)/revenue < 0.05 |
| Revenue persistence (stable) | Worst YoY > -5% |
| Cash conversion (stable) | stdev < 0.15 |
| FCF margin trend (high) | Delta > +2 percentage points |

### 7.2 Statutory Tax Rate (ROIC)

Default: **30%** (Australian corporate tax rate). Stored in `_DEFAULT_TAX_RATE` in `roic.py`. Used for NOPAT calculation: `NOPAT = EBIT * (1 - 0.30)`.

The tax rate is recorded in every ROIC artifact under `config.statutory_tax_rate` and in evidence as `evidence_id: "roic_tax_rate"`.

### 7.3 LLM Configuration

| Parameter | Source | Default |
|-----------|--------|---------|
| `llm_base_url` | Passed to `analyse_ticker()` or `AnalysisOrchestrator` | `None` (D2 disabled) |
| `llm_model` | Passed to `analyse_ticker()` or `AnalysisOrchestrator` | `""` |
| D2 timeout | Hardcoded in each hybrid module | 60 seconds |
| LLM runtime | `app.services.llamacpp_runtime.generate_json_llamacpp` | llama.cpp compatible endpoint |

When `llm_base_url` is `None`, all hybrid modules run D1 only. No errors are raised; D2 is simply skipped.

### 7.4 Reports Root

Artifact output location is determined by:
1. `reports_root` kwarg to `analyse_ticker()` (highest priority)
2. `DATA_ROOT` environment variable: `{DATA_ROOT}/reports/`
3. Project-relative fallback: `financial-engine_v2/reports/`

All artifacts land under `{reports_root}/analysis/{ticker}/{module_name}.json`.

---

## 8. Data Gaps and Future Work

### 8.1 Missing Extraction Fields

| Field | Impact | Workaround |
|-------|--------|------------|
| `total_equity` | ROIC uses market-cap proxy instead of book IC | Awaiting extraction schema extension |
| `interest_expense` | Cannot compute interest coverage ratio | Not extracted from ASX filings yet |
| `depreciation_amortization` | Cannot compute EBITDA-based multiples | Not extracted from ASX filings yet |
| `total_assets` | Cannot compute ROA | Not extracted from ASX filings yet |
| `dividends_paid` | Cannot compute payout ratio or dividend yield | Not extracted from ASX filings yet |

### 8.2 Deferred Capabilities

| Capability | Status | Dependency |
|------------|--------|------------|
| **Peer comparison** | Deferred | Requires sector classification and cross-ticker analysis. Modules are per-ticker only. |
| **DCF valuation** | Deferred | Requires reliable multi-year projections or analyst consensus data. |
| **WACC estimation** | Deferred | Requires risk-free rate, beta, market risk premium, cost of debt inputs. |
| **Sentiment module** | Proposed in roadmap | Requires news substrate (Phase 1) and sentiment model. |
| **Quality score module** | Proposed in roadmap | Composite quality metric from existing module signals. |
| **Autonomous dev optimization** | Deferred | Requires eval harness. See [14_roadmap_and_modules.md](14_roadmap_and_modules.md). |

### 8.3 Portfolio Module Integration (Phase 4)

The analysis artifacts are designed to be consumed by a future portfolio module (Phase 4). The module will read `reports/analysis/{ticker}/*.json` artifacts and produce exposure, correlation, and position sizing reports under `reports/portfolio/`. The `ArtifactSet` schema, `Completeness` enum, and evidence chains are designed to support this consumption pattern.

### 8.4 D2 Cache Layer

A prompt-hash-based cache layer for D2 LLM calls is not yet implemented. The infrastructure is in place (`Narrative.prompt_hash`, `Narrative.cached` flag) but no cache store exists. When implemented, it should:
- Key on `(ticker, module_name, prompt_hash, model_id)`
- Invalidate automatically when upstream data changes (hash changes)
- Support a configurable TTL for time-sensitive analyses (catalysts, risk)

---

## 9. File Reference Table

| File | Role | Lines |
|------|------|------:|
| `__init__.py` | Package docstring | 5 |
| `base.py` | Protocol contract, Completeness, EvidenceItem, Narrative, ArtifactSet, ModuleHelpers | 188 |
| `ticker_context.py` | TickerContext and all input dataclasses (PeriodMetrics, TrendMetrics, FinancialSummary, RiskNote, DocumentRef, PriceSnapshot, RAGHit, RAGResult, ContextRequest) | 228 |
| `context_loader.py` | TickerContextLoader: DB queries, metric computation, RAG execution, context assembly | 228 |
| `math_utils.py` | Null-safe math: ratio, pct_change, safe_sub/add/mul, mean, stdev, linear_slope, classify_direction | 156 |
| `artifacts.py` | Atomic artifact writing, serialization, git metadata, read_artifact | 149 |
| `orchestrator.py` | AnalysisOrchestrator, tier execution, analyse_ticker() entry point, context request merging | 209 |
| `balance_sheet.py` | D1 balance sheet: leverage, liquidity, FCF, trajectory, signals | 285 |
| `roic.py` | D1 ROIC: pre-tax/post-tax ROIC, IC proxy, capital turnover, trend | 218 |
| `valuation.py` | D1 valuation: 12 multiples, signal classification, composite signal | 211 |
| `risk.py` | Hybrid risk: stress signals, risk score, trajectory, D2 prioritization | 335 |
| `catalysts.py` | Hybrid catalysts: guidance, momentum, D2 catalyst identification | 283 |
| `moat.py` | Hybrid moat: 6 D1 signals, Morningstar 5-source D2, structural validation | 292 |
| **Total** | | **2,787** |

All files are in `financial-engine_v2/backend/app/modules/`.

Test file: `financial-engine_v2/backend/tests/test_analysis_modules.py` (43 tests).

---

## References

- [14_roadmap_and_modules.md](14_roadmap_and_modules.md) -- Original roadmap defining the 5-phase pipeline
- [SYSTEM_CONTRACT.md](SYSTEM_CONTRACT.md) -- Governing system contract (analysis is Layer 5)
- [04_ingestion_pipeline.md](04_ingestion_pipeline.md) -- Phase 1 data acquisition
- [07_rag_contract.md](07_rag_contract.md) -- Phase 2 retrieval
- [03_data_model.md](03_data_model.md) -- Database schema (asx_periodic_financials, asx_risk_notes, openbb_snapshots)
