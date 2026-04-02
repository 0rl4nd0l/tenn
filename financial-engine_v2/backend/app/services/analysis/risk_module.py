"""risk_module.py — structured risk aggregation per ticker.

Deterministic assembly of risk insights from:
  1. Postgres: asx_risk_notes (extracted risk summaries + bullets)
  2. RAG: asx_docs (supporting evidence from filings)
  3. RAG: news (optional recent context)

No LLM calls. No direct Qdrant access. Backend service layer only.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.analysis.context_assembler import assemble as assemble_context
from app.services.rag import query_news_chunks, query_rag

logger = logging.getLogger(__name__)

_CATEGORY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "operational": [
        re.compile(r, re.IGNORECASE)
        for r in (
            r"\boperat\w+",
            r"\bsupply\s+chain",
            r"\bproduction\b",
            r"\bsafety\b",
            r"\bworkforce\b",
            r"\bstaff\b",
            r"\bemployee\b",
            r"\bIT\s+system",
            r"\bcyber",
            r"\boutage\b",
            r"\bdisruption\b",
            r"\bproject\s+delay",
            r"\bconstruction\b",
            r"\bmine\s+plan",
            r"\bore\s+reserve",
        )
    ],
    "financial": [
        re.compile(r, re.IGNORECASE)
        for r in (
            r"\bdebt\b",
            r"\bliquidity\b",
            r"\bcash\s*flow",
            r"\bcredit\b",
            r"\bimpairment\b",
            r"\bwrite[\s-]?down",
            r"\bcovenant\b",
            r"\bfunding\b",
            r"\bcapital\s+rais",
            r"\bdilut",
            r"\binsolvenc",
            r"\bgoodwill\b",
            r"\bforecast\b",
            r"\bprofit\s+warning",
            r"\brevenue\s+decline",
        )
    ],
    "regulatory": [
        re.compile(r, re.IGNORECASE)
        for r in (
            r"\bregulat",
            r"\bcomplianc",
            r"\blicen[sc]",
            r"\bpermit\b",
            r"\blitigation\b",
            r"\blawsuit\b",
            r"\blegal\b",
            r"\btax\b",
            r"\benvironmental\b",
            r"\bASIC\b",
            r"\bAPRA\b",
            r"\bACCC\b",
            r"\bgovernment\b",
            r"\blegislat",
            r"\bsanction",
        )
    ],
    "macro": [
        re.compile(r, re.IGNORECASE)
        for r in (
            r"\bmacro",
            r"\binterest\s+rate",
            r"\binflation\b",
            r"\bFX\b",
            r"\bcurrency\b",
            r"\bexchange\s+rate",
            r"\bcommodity\s+pric",
            r"\bgeopoli",
            r"\btariff\b",
            r"\btrade\s+war",
            r"\bpandemic\b",
            r"\bglobal\s+econom",
            r"\brecession\b",
            r"\bChina\b",
            r"\bdemand\s+weak",
        )
    ],
}

_SEVERITY_KEYWORDS: dict[str, list[re.Pattern[str]]] = {
    "high": [
        re.compile(r, re.IGNORECASE)
        for r in (
            r"\bmaterial\b",
            r"\bsignificant\b",
            r"\bsubstantial\b",
            r"\bsever",
            r"\bcritical\b",
            r"\bmajor\b",
            r"\bgoing\s+concern",
            r"\binsolvenc",
            r"\bdefault\b",
        )
    ],
    "medium": [
        re.compile(r, re.IGNORECASE)
        for r in (
            r"\bmoderat",
            r"\buncertain",
            r"\bvolatil",
            r"\bchallenging\b",
            r"\bpotential\b",
            r"\brisk\b",
        )
    ],
}


def _categorize_text(text: str) -> list[str]:
    """Return matching risk category names for a text fragment."""
    matches: list[str] = []
    for category, patterns in _CATEGORY_PATTERNS.items():
        if any(p.search(text) for p in patterns):
            matches.append(category)
    return matches


def _estimate_severity(text: str) -> str:
    """Return 'high', 'medium', or 'low' severity estimate for a risk text."""
    for level in ("high", "medium"):
        if any(p.search(text) for p in _SEVERITY_KEYWORDS[level]):
            return level
    return "low"


def _extract_risk_items(risk_note: dict[str, Any]) -> list[dict[str, str]]:
    """Extract individual risk items from a risk note row.

    Returns list of {"text": ..., "source_type": "risk_bullet"|"risk_summary"}.
    """
    items: list[dict[str, str]] = []
    bullets = risk_note.get("risk_bullets")
    if isinstance(bullets, list):
        for bullet in bullets:
            text = str(bullet).strip() if bullet else ""
            if text:
                items.append({"text": text, "source_type": "risk_bullet"})
    summary = risk_note.get("risk_summary")
    if isinstance(summary, str) and summary.strip():
        items.append({"text": summary.strip(), "source_type": "risk_summary"})
    return items


def run_risk_analysis(
    ticker: str,
    db: Session,
    *,
    include_news: bool = True,
    rag_top_k: int = 6,
    news_top_k: int = 5,
) -> dict[str, Any]:
    """Build a structured risk report for *ticker*.

    Data sources (all read-only):
      1. Postgres: risk notes + recent documents via context_assembler
      2. RAG (asx_docs): supporting evidence from filings
      3. RAG (news): optional recent news context

    Returns a RiskReport dict. No LLM calls. No direct Qdrant access.
    """
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        raise ValueError("ticker is required")

    # --- Step 1: DB context (risk notes + documents) ---
    context = assemble_context(
        ticker,
        db,
        max_risk_notes=10,
        max_docs=15,
    )
    risk_notes: list[dict[str, Any]] = context.get("risk_notes") or []
    recent_docs: list[dict[str, Any]] = context.get("recent_docs") or []
    warnings: list[str] = list(context.get("warnings") or [])

    # --- Step 2: Extract and categorize individual risk items ---
    key_risks: list[str] = []
    risk_categories: dict[str, list[str]] = {
        "operational": [],
        "financial": [],
        "regulatory": [],
        "macro": [],
    }
    severity_counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    supporting_evidence: list[dict[str, Any]] = []

    for note in risk_notes:
        items = _extract_risk_items(note)
        doc_id = str(note.get("document_id") or "")
        for item in items:
            text = item["text"]
            key_risks.append(text)

            categories = _categorize_text(text)
            if not categories:
                categories = ["operational"]  # default bucket
            for cat in categories:
                if cat in risk_categories:
                    risk_categories[cat].append(text)

            severity = _estimate_severity(text)
            severity_counts[severity] += 1

            supporting_evidence.append({
                "text": text,
                "source": "asx_risk_notes",
                "document_id": doc_id,
                "source_type": item["source_type"],
            })

    # --- Step 3: RAG evidence from filings ---
    rag_evidence: list[dict[str, Any]] = []
    try:
        rag_result = query_rag(
            query=f"Key risks and risk factors for {ticker}",
            ticker=ticker,
            top_k=rag_top_k,
        )
        for hit in rag_result.get("hits") or []:
            text = str(hit.get("text") or "").strip()
            if text:
                rag_evidence.append({
                    "text": text,
                    "source": "asx_docs",
                    "document_id": hit.get("document_id", ""),
                    "title": hit.get("title", ""),
                    "score": hit.get("score", 0.0),
                })
    except (RuntimeError, Exception) as exc:
        warnings.append(f"RAG asx_docs query failed: {exc}")
        logger.warning("Risk module RAG query failed for %s: %s", ticker, exc)

    # --- Step 4: Optional news context ---
    news_evidence: list[dict[str, Any]] = []
    if include_news:
        try:
            news_result = query_news_chunks(
                query=f"{ticker} risk",
                ticker=ticker,
                top_k=news_top_k,
            )
            for item in news_result.get("results") or []:
                payload = item.get("payload") or {}
                text = str(payload.get("text") or payload.get("title") or "").strip()
                if text:
                    news_evidence.append({
                        "text": text,
                        "source": "news",
                        "provider": payload.get("provider", ""),
                        "published_at": payload.get("published_at", ""),
                        "score": item.get("score", 0.0),
                    })
        except (RuntimeError, Exception) as exc:
            warnings.append(f"RAG news query failed: {exc}")
            logger.warning("Risk module news query failed for %s: %s", ticker, exc)

    # --- Step 5: Compute category severity estimates ---
    severity_estimate: dict[str, str] = {}
    for cat, texts in risk_categories.items():
        if not texts:
            continue
        severities = [_estimate_severity(t) for t in texts]
        if "high" in severities:
            severity_estimate[cat] = "high"
        elif "medium" in severities:
            severity_estimate[cat] = "medium"
        else:
            severity_estimate[cat] = "low"

    # --- Step 6: Deduplicate key_risks ---
    seen: set[str] = set()
    unique_risks: list[str] = []
    for risk in key_risks:
        normalized = risk.lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            unique_risks.append(risk)

    return {
        "ticker": ticker,
        "key_risks": unique_risks,
        "risk_categories": {k: v for k, v in risk_categories.items() if v},
        "severity_estimate": severity_estimate,
        "severity_counts": severity_counts,
        "supporting_evidence": supporting_evidence + rag_evidence + news_evidence,
        "document_count": len(recent_docs),
        "risk_note_count": len(risk_notes),
        "warnings": warnings,
    }
