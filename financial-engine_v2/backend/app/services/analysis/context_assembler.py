"""context_assembler.py — gather all inputs for a ticker analysis.

Queries the database for financial rows and risk notes, then packages
everything into a single dict that report_generator.py can consume.
No LLM calls; no network calls beyond the DB.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.asx_financials import ASXRiskNote
from app.models.documents import Document
from app.services.analysis.financial_metrics import build_metrics_summary
from app.services.financial_observations import stable_financial_profile

logger = logging.getLogger(__name__)


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy model instance to a plain dict."""
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def assemble(
    ticker: str,
    db: Session,
    *,
    period_type: str = "A",
    max_periods: int = 5,
    max_risk_notes: int = 3,
    max_docs: int = 10,
) -> dict[str, Any]:
    """
    Build the full analysis context for *ticker*.

    Returns:
        {
          "ticker": str,
          "metrics": dict,          # from financial_metrics.build_metrics_summary
          "risk_notes": list[dict], # from asx_risk_notes (joined via document_id)
          "recent_docs": list[dict],# from documents table (most recent first)
          "warnings": list[str],    # non-fatal issues to surface in the report
        }
    """
    ticker = ticker.strip().upper()
    warnings: list[str] = []

    # --- Financial rows ---
    raw_rows = list(stable_financial_profile(db, ticker=ticker))[
        : max_periods * 3
    ]
    if not raw_rows:
        warnings.append(f"No financial rows found for {ticker}.")
    metrics = build_metrics_summary(raw_rows, period_type=period_type, max_periods=max_periods)

    # --- Documents ---
    docs = (
        db.query(Document)
        .filter(Document.ticker == ticker)
        .order_by(Document.published_at.desc())
        .limit(max_docs)
        .all()
    )
    doc_rows = [_row_to_dict(d) for d in docs]
    doc_ids = {str(d.document_id) for d in docs}

    # --- Risk notes (joined to ticker via document_id) ---
    risk_note_rows: list[dict[str, Any]] = []
    if doc_ids:
        import uuid
        risk_notes = (
            db.query(ASXRiskNote)
            .filter(
                ASXRiskNote.document_id.in_(
                    [uuid.UUID(did) for did in doc_ids]
                )
            )
            .order_by(ASXRiskNote.updated_at.desc())
            .limit(max_risk_notes)
            .all()
        )
        risk_note_rows = [_row_to_dict(r) for r in risk_notes]
    if not risk_note_rows:
        warnings.append(f"No risk notes found for {ticker}.")

    return {
        "ticker": ticker,
        "metrics": metrics,
        "risk_notes": risk_note_rows,
        "recent_docs": doc_rows,
        "warnings": warnings,
    }
