"""sentiment.py — Lightweight sentiment scoring module.

Pure D1 (deterministic, no LLM). Uses VADER from nltk with a financial-domain
keyword booster to correct for VADER's weak coverage of financial language.

Scores each passage from risk_notes, RAG hits, and guidance, then aggregates
into filing_sentiment, news_sentiment, guidance_sentiment, and overall.

Output range: -1.0 (very negative) to +1.0 (very positive).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.modules.base import (
    ArtifactSet, Completeness, EvidenceItem, ModuleHelpers,
)
from app.modules.math_utils import mean, round_or_none
from app.modules.ticker_context import RiskNote, TickerContext

logger = logging.getLogger(__name__)

# -- Financial-domain keyword boosters ---------------------------------------
# VADER underweights financial language. Adjustments applied additively.

_POSITIVE_KW: dict[str, float] = {
    "beat": 0.15, "beats": 0.15, "exceeded": 0.15,
    "upgrade": 0.20, "upgraded": 0.20, "outperform": 0.15,
    "growth": 0.10, "accelerat": 0.12, "record": 0.10,
    "dividend": 0.08, "buyback": 0.10, "acquisition": 0.05,
    "margin expansion": 0.15, "cash generation": 0.10,
    "raised guidance": 0.20, "reaffirmed guidance": 0.10,
    "strong demand": 0.12, "market share gains": 0.12,
    "profitable": 0.10, "surplus": 0.08,
    "tailwind": 0.10, "upside": 0.12,
    "de-risk": 0.08, "deleverag": 0.10,
}
_NEGATIVE_KW: dict[str, float] = {
    "miss": 0.15, "missed": 0.15, "downgrade": 0.20,
    "downturn": 0.15, "decline": 0.12, "declining": 0.12,
    "impairment": 0.18, "write-down": 0.18, "writedown": 0.18,
    "restructur": 0.12, "redundanc": 0.12, "layoff": 0.12,
    "dilut": 0.10, "covenant breach": 0.20,
    "lowered guidance": 0.20, "withdrawn guidance": 0.22,
    "margin compress": 0.15, "margin erosion": 0.15,
    "cash burn": 0.15, "negative free cash flow": 0.18,
    "headwind": 0.10, "downside risk": 0.12,
    "liquidity concern": 0.18, "going concern": 0.25,
    "regulatory risk": 0.10, "litigation": 0.10,
    "loss": 0.08, "losses": 0.08,
}

_POS_PATTERNS = [
    (re.compile(rf"\b{re.escape(kw)}", re.IGNORECASE), b)
    for kw, b in _POSITIVE_KW.items()
]
_NEG_PATTERNS = [
    (re.compile(rf"\b{re.escape(kw)}", re.IGNORECASE), b)
    for kw, b in _NEGATIVE_KW.items()
]

# -- Lazy VADER loader -------------------------------------------------------

_vader = None


def _get_vader() -> Any:
    """Return a cached SentimentIntensityAnalyzer, downloading data if needed."""
    global _vader  # noqa: PLW0603
    if _vader is None:
        import nltk
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        _vader = SentimentIntensityAnalyzer()
    return _vader


# -- Scoring helpers ----------------------------------------------------------


@dataclass(frozen=True)
class ScoredPassage:
    """A scored text passage with provenance."""
    text_excerpt: str   # first 200 chars
    score: float        # -1.0 to 1.0
    source_category: str  # filing | news | guidance
    source_id: str


def _score_text(text: str) -> float:
    """Score a single passage: VADER compound + financial keyword boost."""
    if not text or not text.strip():
        return 0.0
    compound: float = _get_vader().polarity_scores(text)["compound"]
    pos_boost = sum(b for p, b in _POS_PATTERNS if p.search(text))
    neg_boost = sum(b for p, b in _NEG_PATTERNS if p.search(text))
    return max(-1.0, min(1.0, compound + pos_boost - neg_boost))


def _categorize_rag_label(label: str) -> str:
    """Map a RAG label to a sentiment source category."""
    low = label.lower()
    if "news" in low or "market" in low:
        return "news"
    if "guidance" in low or "outlook" in low:
        return "guidance"
    return "filing"


def _risk_note_passages(rn: RiskNote) -> list[tuple[str, str]]:
    """Extract scorable (text, category) pairs from a RiskNote."""
    passages: list[tuple[str, str]] = []
    if rn.risk_summary:
        passages.append((rn.risk_summary, "filing"))
    for bullet in rn.risk_bullets:
        text = str(bullet).strip()
        if text:
            passages.append((text, "filing"))
    if rn.guidance_summary:
        passages.append((rn.guidance_summary, "guidance"))
    if rn.material_changes:
        passages.append((rn.material_changes, "filing"))
    return passages


# -- Module class -------------------------------------------------------------


class SentimentModule(ModuleHelpers):
    """Lightweight sentiment scoring -- VADER + financial keyword boosting.

    Pure D1 (deterministic). No LLM calls. Typically runs in <100ms per ticker.
    """

    @property
    def name(self) -> str:
        return "sentiment"

    @property
    def requires(self) -> frozenset[str]:
        return frozenset({"risk_notes"})

    def run(self, context: TickerContext) -> ArtifactSet:
        ticker = context.ticker
        warnings: list[str] = []
        scored: list[ScoredPassage] = []

        # Score risk notes
        for rn in context.risk_notes:
            for text, category in _risk_note_passages(rn):
                scored.append(ScoredPassage(
                    text[:200], _score_text(text), category, rn.document_id,
                ))

        # Score RAG hits
        for result in context.rag_results:
            category = _categorize_rag_label(result.label)
            for hit in result.hits:
                if not hit.text.strip():
                    continue
                scored.append(ScoredPassage(
                    hit.text[:200], _score_text(hit.text),
                    category, hit.document_id or result.label,
                ))

        if not scored:
            warnings.append("no_scorable_passages")
            return self._build_artifact(
                ticker=ticker, module_name=self.name,
                completeness=Completeness.FAILED,
                structured={"error": "no passages available for sentiment scoring"},
                warnings=tuple(warnings),
            )

        # Aggregate by category
        by_cat = {
            c: [s.score for s in scored if s.source_category == c]
            for c in ("filing", "news", "guidance")
        }
        all_scores = [s.score for s in scored]

        filing_sentiment = round_or_none(mean(by_cat["filing"]), 3)
        news_sentiment = round_or_none(mean(by_cat["news"]), 3)
        guidance_sentiment = round_or_none(mean(by_cat["guidance"]), 3)
        overall_sentiment = round_or_none(mean(all_scores), 3)

        # Find extremes
        sorted_passages = sorted(scored, key=lambda s: s.score)
        most_neg = sorted_passages[0]
        most_pos = sorted_passages[-1]

        # Evidence chain
        evidence_items = (
            EvidenceItem(
                evidence_id=f"sentiment_{ticker}_most_positive",
                source_type="rag_hit", content=most_pos.text_excerpt,
                source_id=most_pos.source_id, confidence=most_pos.score,
            ),
            EvidenceItem(
                evidence_id=f"sentiment_{ticker}_most_negative",
                source_type="rag_hit", content=most_neg.text_excerpt,
                source_id=most_neg.source_id, confidence=most_neg.score,
            ),
        )

        structured: dict[str, Any] = {
            "overall_sentiment": overall_sentiment,
            "filing_sentiment": filing_sentiment,
            "news_sentiment": news_sentiment,
            "guidance_sentiment": guidance_sentiment,
            "passage_count": len(scored),
            "category_counts": {c: len(v) for c, v in by_cat.items()},
            "most_positive": {
                "score": round_or_none(most_pos.score, 3),
                "excerpt": most_pos.text_excerpt,
                "source_category": most_pos.source_category,
                "source_id": most_pos.source_id,
            },
            "most_negative": {
                "score": round_or_none(most_neg.score, 3),
                "excerpt": most_neg.text_excerpt,
                "source_category": most_neg.source_category,
                "source_id": most_neg.source_id,
            },
            "scoring_method": "vader_financial_boosted",
        }

        completeness = (
            Completeness.COMPLETE if len(scored) >= 3
            else Completeness.PARTIAL
        )
        if not by_cat["filing"]:
            warnings.append("no_filing_passages")
        if not by_cat["guidance"]:
            warnings.append("no_guidance_passages")

        return self._build_artifact(
            ticker=ticker, module_name=self.name,
            completeness=completeness, structured=structured,
            evidence=evidence_items, warnings=tuple(warnings),
        )
