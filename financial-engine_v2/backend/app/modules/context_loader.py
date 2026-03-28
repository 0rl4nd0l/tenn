"""context_loader.py — Bridge between DB/RAG/price systems and frozen TickerContext.

Queries database tables, computes derived metrics, and assembles an immutable
TickerContext object for analysis modules. No LLM calls; RAG queries are
delegated to an optional callback.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date as date_type, datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.models.documents import Document
from app.models.openbb_snapshots import OpenBBPriceSnapshot
from app.modules.math_utils import coerce
from app.modules.ticker_context import (
    ContextRequest, DocumentRef, FinancialSummary, PeriodMetrics,
    PriceSnapshot, RAGHit, RAGResult, RiskNote, TickerContext, TrendMetrics,
)
from app.services.analysis.financial_metrics import (
    compute_period_metrics, compute_trends, score_financial_health,
)

logger = logging.getLogger(__name__)

# (query, collection, top_k) -> list[dict] with keys: text, score, document_id?, title?
RAGFn = Callable[[str, str, int], list[dict[str, Any]]]


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def _parse_period_end(raw: Any) -> date_type:
    if isinstance(raw, str) and raw:
        try:
            return date_type.fromisoformat(raw)
        except ValueError:
            return date_type.today()
    return raw if hasattr(raw, "year") else date_type.today()


def _to_period(d: dict[str, Any]) -> PeriodMetrics:
    return PeriodMetrics(
        period_end=_parse_period_end(d.get("period_end", "")),
        period_type=d.get("period_type", ""),
        revenue=d.get("revenue"), ebit=d.get("ebit"),
        np_attributable=d.get("np_attributable"),
        operating_cf=d.get("operating_cf"), investing_cf=d.get("investing_cf"),
        financing_cf=d.get("financing_cf"), capex=d.get("capex"),
        cash_end=d.get("cash_end"), net_debt=d.get("net_debt"),
        shares_outstanding=d.get("shares_outstanding"),
        fcf=d.get("fcf"), ebit_margin=d.get("ebit_margin"),
        np_margin=d.get("np_margin"), fcf_margin=d.get("fcf_margin"),
        cash_conversion=d.get("cash_conversion"), confidence=d.get("confidence"),
    )


def _to_trends(d: dict[str, Any]) -> TrendMetrics:
    if not d.get("available", False):
        return TrendMetrics(available=False)
    return TrendMetrics(
        available=True, revenue_yoy=d.get("revenue_yoy"),
        ebit_yoy=d.get("ebit_yoy"), np_yoy=d.get("np_yoy"),
        fcf_yoy=d.get("fcf_yoy"), net_debt_yoy=d.get("net_debt_yoy"),
        ebit_margin_delta=d.get("ebit_margin_delta"),
    )


class TickerContextLoader:
    """Assembles a frozen TickerContext from DB, price, and RAG sources."""

    def __init__(self, rag_fn: RAGFn | None = None) -> None:
        self._rag_fn = rag_fn

    def load(self, ticker: str, request: ContextRequest, *, db: Session) -> TickerContext:
        ticker = ticker.strip().upper()
        w: list[str] = []
        return TickerContext(
            ticker=ticker,
            assembled_at=datetime.utcnow(),
            financials=self._financials(ticker, request, db, w),
            risk_notes=self._risk_notes(ticker, request, db, w),
            documents=self._documents(ticker, request, db, w),
            price=self._price(ticker, request, db, w),
            rag_results=self._rag(ticker, request, w),
            warnings=tuple(w),
        )

    def _financials(self, ticker: str, req: ContextRequest, db: Session,
                    w: list[str]) -> FinancialSummary | None:
        if not req.needs_financials:
            return None
        try:
            rows = (
                db.query(ASXPeriodicFinancial)
                .filter(ASXPeriodicFinancial.ticker == ticker,
                        ASXPeriodicFinancial.period_type == req.period_type)
                .order_by(ASXPeriodicFinancial.period_end.desc())
                .limit(req.max_periods).all()
            )
        except Exception:
            logger.exception("DB error querying financials for %s", ticker)
            w.append(f"Failed to query financials for {ticker}.")
            return None
        if not rows:
            w.append(f"No {req.period_type} financial rows for {ticker}.")
            return FinancialSummary(period_type=req.period_type)
        raw = sorted((_row_to_dict(r) for r in rows),
                     key=lambda r: str(r.get("period_end", "")))
        computed = [compute_period_metrics(r) for r in raw]
        trends_d = compute_trends(computed)
        return FinancialSummary(
            period_type=req.period_type,
            periods=tuple(_to_period(c) for c in computed),
            trends=_to_trends(trends_d),
            financial_health_score=score_financial_health(computed, trends_d),
        )

    def _risk_notes(self, ticker: str, req: ContextRequest, db: Session,
                    w: list[str]) -> tuple[RiskNote, ...]:
        if not req.needs_risk_notes:
            return ()
        try:
            doc_ids = [r[0] for r in db.query(Document.document_id)
                       .filter(Document.ticker == ticker).all()]
            if not doc_ids:
                w.append(f"No documents for {ticker}; skipping risk notes.")
                return ()
            notes = (
                db.query(ASXRiskNote)
                .filter(ASXRiskNote.document_id.in_(doc_ids))
                .order_by(ASXRiskNote.updated_at.desc())
                .limit(req.max_risk_notes).all()
            )
        except Exception:
            logger.exception("DB error querying risk notes for %s", ticker)
            w.append(f"Failed to query risk notes for {ticker}.")
            return ()
        if not notes:
            w.append(f"No risk notes found for {ticker}.")
            return ()
        return tuple(
            RiskNote(
                document_id=str(n.document_id), risk_summary=n.risk_summary,
                risk_bullets=tuple(n.risk_bullets) if n.risk_bullets else (),
                guidance_summary=n.guidance_summary,
                material_changes=n.material_changes,
                confidence_narrative=(float(n.confidence_narrative)
                                     if n.confidence_narrative is not None else None),
            ) for n in notes
        )

    def _documents(self, ticker: str, req: ContextRequest, db: Session,
                   w: list[str]) -> tuple[DocumentRef, ...]:
        if not req.needs_documents:
            return ()
        try:
            docs = (
                db.query(Document).filter(Document.ticker == ticker)
                .order_by(Document.published_at.desc())
                .limit(req.max_docs).all()
            )
        except Exception:
            logger.exception("DB error querying documents for %s", ticker)
            w.append(f"Failed to query documents for {ticker}.")
            return ()
        return tuple(
            DocumentRef(document_id=str(d.document_id), ticker=d.ticker,
                        title=d.title, published_at=d.published_at)
            for d in docs
        )

    def _fetch_live_price(self, ticker: str) -> PriceSnapshot | None:
        """Fetch latest close price from Yahoo Finance via yfinance.

        For ASX tickers the Yahoo symbol is ``{ticker}.AX``.
        Returns a PriceSnapshot with source="yahoo" on success, None on failure.
        """
        try:
            import yfinance as yf  # noqa: PLC0415
        except ImportError:
            logger.warning("yfinance not installed; cannot fetch live price for %s", ticker)
            return None

        yahoo_symbol = f"{ticker}.AX"
        try:
            yticker = yf.Ticker(yahoo_symbol)
            info = yticker.info or {}
            # Prefer regularMarketPrice (real-time), fall back to previousClose
            price_val = coerce(
                info.get("regularMarketPrice")
                or info.get("previousClose")
                or info.get("open"),
            )
            if price_val is None:
                logger.warning("yfinance returned no parseable price for %s", yahoo_symbol)
                return None
            currency = str(info.get("currency", "AUD"))
            return PriceSnapshot(
                last_close=price_val,
                currency=currency,
                captured_at=datetime.now(tz=timezone.utc),
                source="yahoo",
            )
        except Exception:
            logger.exception("yfinance fetch failed for %s", yahoo_symbol)
            return None

    @staticmethod
    def _persist_yahoo_price(ticker: str, price: PriceSnapshot, db: Session) -> None:
        """Cache a Yahoo-sourced price into openbb_price_snapshots for future reads."""
        try:
            payload = {
                "close": price.last_close,
                "currency": price.currency,
            }
            request_hash = hashlib.sha256(
                json.dumps({"ticker": ticker, "source": "yahoo"}, sort_keys=True).encode()
            ).hexdigest()
            now = datetime.now(tz=timezone.utc)
            row = OpenBBPriceSnapshot(
                ticker=ticker,
                exchange="ASX",
                symbol=f"{ticker}.AX",
                provider="yahoo",
                dataset_type="price_historical",
                request_hash=request_hash,
                payload=payload,
                captured_at=now,
            )
            db.add(row)
            db.commit()
            logger.info("Persisted Yahoo price for %s: %.4f %s", ticker, price.last_close, price.currency)
        except Exception:
            db.rollback()
            logger.exception("Failed to persist Yahoo price for %s", ticker)

    def _price(self, ticker: str, req: ContextRequest, db: Session,
               w: list[str]) -> PriceSnapshot | None:
        if not req.needs_price:
            return None
        # Step 1: try DB snapshot
        try:
            snap = (
                db.query(OpenBBPriceSnapshot)
                .filter(OpenBBPriceSnapshot.ticker == ticker)
                .order_by(OpenBBPriceSnapshot.captured_at.desc()).first()
            )
        except Exception:
            logger.exception("DB error querying price for %s", ticker)
            snap = None
        if snap is not None:
            payload = snap.payload or {}
            price_val = coerce(payload.get("close") or payload.get("last_close"))
            if price_val is not None:
                return PriceSnapshot(
                    last_close=price_val, currency=payload.get("currency", "AUD"),
                    captured_at=snap.captured_at, source=snap.provider or "openbb",
                )
            w.append(f"Price snapshot for {ticker} has no parseable close price; trying Yahoo.")

        # Step 2: fallback to Yahoo Finance
        logger.info("No DB price for %s; attempting Yahoo Finance fallback.", ticker)
        live = self._fetch_live_price(ticker)
        if live is not None:
            self._persist_yahoo_price(ticker, live, db)
            return live

        # Step 3: give up
        w.append(f"No price snapshot available for {ticker} (DB empty, Yahoo fallback failed).")
        return None

    def _rag(self, ticker: str, req: ContextRequest,
             w: list[str]) -> tuple[RAGResult, ...]:
        if not req.rag_queries:
            return ()
        if self._rag_fn is None:
            w.append("RAG queries requested but no rag_fn provided; skipping.")
            return ()
        results: list[RAGResult] = []
        for spec in req.rag_queries:
            query = spec.query_template.replace("{ticker}", ticker)
            try:
                raw_hits = self._rag_fn(query, spec.collection, spec.top_k)
            except Exception:
                logger.exception("RAG query failed: %s", spec.label)
                w.append(f"RAG query '{spec.label}' failed.")
                continue
            hits = tuple(
                RAGHit(text=h.get("text", ""), score=float(h.get("score", 0.0)),
                       document_id=str(h.get("document_id", "")),
                       title=str(h.get("title", "")), collection=spec.collection)
                for h in raw_hits
            )
            results.append(RAGResult(label=spec.label, query=query,
                                     collection=spec.collection, hits=hits))
        return tuple(results)
