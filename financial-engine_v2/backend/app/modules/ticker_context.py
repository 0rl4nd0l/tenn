"""ticker_context.py — Typed, frozen context for analysis modules.

All dataclasses are immutable. No I/O methods — the TickerContextLoader
(separate file) handles construction.

Design decisions (from architecture debate):
  - Selective-fat pattern: modules declare needs via ContextRequest; loader
    pre-fetches only what is requested; returns a frozen object.
  - Multi-period data as tuple of PeriodMetrics with .latest/.prior accessors.
  - Price is optional (only valuation needs it).
  - RAG queries declared upfront in ContextRequest, executed by loader.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Period-level financial data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PeriodMetrics:
    """Single-period financial metrics from asx_periodic_financials."""

    period_end: date
    period_type: str  # "Q" | "H" | "A"
    revenue: float | None = None
    ebit: float | None = None
    np_attributable: float | None = None
    operating_cf: float | None = None
    investing_cf: float | None = None
    financing_cf: float | None = None
    capex: float | None = None
    cash_end: float | None = None
    net_debt: float | None = None
    shares_outstanding: float | None = None
    # Derived
    fcf: float | None = None
    ebit_margin: float | None = None
    np_margin: float | None = None
    fcf_margin: float | None = None
    cash_conversion: float | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class TrendMetrics:
    """YoY deltas between the two most recent periods."""

    available: bool = False
    revenue_yoy: float | None = None
    ebit_yoy: float | None = None
    np_yoy: float | None = None
    fcf_yoy: float | None = None
    net_debt_yoy: float | None = None
    ebit_margin_delta: float | None = None


@dataclass(frozen=True)
class FinancialSummary:
    """Multi-period financial data with computed trends."""

    period_type: str  # "A" | "H" | "Q"
    periods: tuple[PeriodMetrics, ...] = ()  # oldest-first
    trends: TrendMetrics = TrendMetrics()
    financial_health_score: float = 0.0

    @property
    def latest(self) -> PeriodMetrics | None:
        return self.periods[-1] if self.periods else None

    @property
    def prior(self) -> PeriodMetrics | None:
        return self.periods[-2] if len(self.periods) >= 2 else None

    @property
    def period_count(self) -> int:
        return len(self.periods)


# ---------------------------------------------------------------------------
# Risk data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskNote:
    """Risk note from asx_risk_notes."""

    document_id: str
    risk_summary: str | None = None
    risk_bullets: tuple[str, ...] = ()
    guidance_summary: str | None = None
    material_changes: str | None = None
    confidence_narrative: float | None = None


# ---------------------------------------------------------------------------
# Document metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentRef:
    """Lightweight reference to a filed document."""

    document_id: str
    ticker: str
    title: str | None = None
    published_at: datetime | None = None


# ---------------------------------------------------------------------------
# Price / market data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriceSnapshot:
    """Latest price data for valuation computations."""

    last_close: float
    currency: str = "AUD"
    captured_at: datetime | None = None
    source: str = "openbb"


# ---------------------------------------------------------------------------
# RAG evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RAGHit:
    """Single retrieval result."""

    text: str
    score: float
    document_id: str = ""
    title: str = ""
    collection: str = ""


@dataclass(frozen=True)
class RAGResult:
    """Labeled set of RAG hits for a specific query."""

    label: str
    query: str
    collection: str
    hits: tuple[RAGHit, ...] = ()


# ---------------------------------------------------------------------------
# Context request (modules declare what they need)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RAGQuerySpec:
    """Declarative RAG query — executed by the loader, not the module."""

    label: str
    query_template: str  # may contain {ticker}
    collection: str = "asx_docs"
    top_k: int = 6


@dataclass(frozen=True)
class ContextRequest:
    """What a module needs from the loader."""

    needs_financials: bool = True
    needs_risk_notes: bool = True
    needs_documents: bool = True
    needs_price: bool = False
    rag_queries: tuple[RAGQuerySpec, ...] = ()
    period_type: str = "A"
    max_periods: int = 5
    max_risk_notes: int = 3
    max_docs: int = 10


# ---------------------------------------------------------------------------
# The assembled context (fully frozen, no I/O methods)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TickerContext:
    """Complete, immutable context for a single ticker analysis.

    Constructed by TickerContextLoader. Modules receive this and
    read from it — no mutations, no I/O.
    """

    ticker: str
    assembled_at: datetime

    # Always populated
    financials: FinancialSummary | None = None
    risk_notes: tuple[RiskNote, ...] = ()
    documents: tuple[DocumentRef, ...] = ()

    # Optional — populated only when requested
    price: PriceSnapshot | None = None
    rag_results: tuple[RAGResult, ...] = ()

    # Assembly warnings
    warnings: tuple[str, ...] = ()

    def rag_by_label(self, label: str) -> RAGResult | None:
        for r in self.rag_results:
            if r.label == label:
                return r
        return None

    @property
    def has_financials(self) -> bool:
        return self.financials is not None and self.financials.period_count > 0

    @property
    def has_price(self) -> bool:
        return self.price is not None
