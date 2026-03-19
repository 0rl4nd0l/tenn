from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Sequence

from .models import ArticleRelevance, EntityLink

EXPLICIT_METHODS = {"explicit_symbol"}
STRICT_METHODS = {"explicit_symbol", "alias_strict"}
WEAK_METHODS = {"ticker_token", "alias_ambiguous"}


def _joined_segment_bounds(title: str, description: str, body: str) -> Dict[str, tuple[int, int]]:
    bounds: Dict[str, tuple[int, int]] = {}
    cursor = 0
    for name, value in (
        ("title", str(title or "").strip()),
        ("description", str(description or "").strip()),
        ("body", str(body or "").strip()),
    ):
        if not value:
            continue
        start = cursor
        end = start + len(value)
        bounds[name] = (start, end)
        cursor = end + 2
    return bounds


def _segment_name_for_span(bounds: Dict[str, tuple[int, int]], span_start: int | None) -> str:
    if span_start is None or span_start < 0:
        return ""
    for name in ("title", "description", "body"):
        start, end = bounds.get(name, (-1, -1))
        if start <= span_start < end:
            return name
    return ""


def _breadth_multiplier(distinct_ticker_count: int) -> float:
    if distinct_ticker_count <= 1:
        return 1.0
    if distinct_ticker_count == 2:
        return 0.96
    if distinct_ticker_count == 3:
        return 0.88
    if distinct_ticker_count <= 6:
        return 0.76
    return 0.62


def _rank_relevance_rows(rows: Sequence[ArticleRelevance]) -> List[ArticleRelevance]:
    return sorted(
        rows,
        key=lambda row: (
            -float(row.relevance_score),
            -float(row.confidence),
            0 if bool(row.is_primary) else 1,
            str(row.ticker or ""),
        ),
    )


def serialize_ticker_relevance(rows: Sequence[ArticleRelevance]) -> str:
    payload: Dict[str, Dict[str, Any]] = {}
    for row in _rank_relevance_rows(rows):
        payload[str(row.ticker)] = {
            "score": round(float(row.relevance_score), 6),
            "label": str(row.relation_type or ""),
            "confidence": round(float(row.confidence), 6),
            "primary": bool(row.is_primary),
        }
    if not payload:
        return ""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def choose_primary_ticker(rows: Sequence[ArticleRelevance], fallback_tickers: Sequence[str] | None = None) -> str:
    ranked = _rank_relevance_rows(rows)
    if ranked:
        top = ranked[0]
        if float(top.relevance_score or 0.0) > 0.0 or float(top.confidence or 0.0) > 0.0:
            return str(top.ticker or "")
    fallback = list(fallback_tickers or [])
    fallback = [str(ticker or "").strip().upper() for ticker in fallback if str(ticker or "").strip()]
    fallback = list(dict.fromkeys(fallback))
    return str(fallback[0] or "") if len(fallback) == 1 else ""


def _score_link_rows(
    *,
    article_id: str,
    lane: str,
    title: str,
    description: str,
    body: str,
    links: Sequence[EntityLink],
) -> List[ArticleRelevance]:
    if not links:
        return []

    bounds = _joined_segment_bounds(title=title, description=description, body=body)
    tickers = sorted({str(link.ticker or "").strip().upper() for link in links if str(link.ticker or "").strip()})
    breadth = _breadth_multiplier(len(tickers))
    evidence_by_ticker: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "mention_count": 0,
            "title_mentions": 0,
            "lead_mentions": 0,
            "strict_mentions": 0,
            "title_strict_mentions": 0,
            "weak_mentions": 0,
            "max_confidence": 0.0,
            "confidence_sum": 0.0,
        }
    )

    for link in links:
        ticker = str(link.ticker or "").strip().upper()
        if not ticker:
            continue
        evidence = evidence_by_ticker[ticker]
        evidence["mention_count"] += 1
        confidence = float(link.confidence or 0.0)
        evidence["confidence_sum"] += confidence
        evidence["max_confidence"] = max(float(evidence["max_confidence"]), confidence)
        method = str(link.method or "").strip().lower()
        segment = _segment_name_for_span(bounds, link.matched_span_start)
        if segment == "title":
            evidence["title_mentions"] += 1
        if segment in {"title", "description"}:
            evidence["lead_mentions"] += 1
        if method in STRICT_METHODS:
            evidence["strict_mentions"] += 1
            if segment == "title":
                evidence["title_strict_mentions"] += 1
        if method in WEAK_METHODS:
            evidence["weak_mentions"] += 1

    rows: List[ArticleRelevance] = []
    for ticker, evidence in evidence_by_ticker.items():
        mention_count = int(evidence["mention_count"])
        title_mentions = int(evidence["title_mentions"])
        lead_mentions = int(evidence["lead_mentions"])
        strict_mentions = int(evidence["strict_mentions"])
        title_strict_mentions = int(evidence["title_strict_mentions"])
        weak_mentions = int(evidence["weak_mentions"])
        max_confidence = float(evidence["max_confidence"])
        confidence_sum = float(evidence["confidence_sum"])

        score = (
            (0.38 * max_confidence)
            + min(0.28, (0.06 * mention_count) + (0.10 * confidence_sum))
            + min(0.18, (0.06 * title_mentions) + (0.07 * title_strict_mentions))
            + (0.05 if strict_mentions > 0 else 0.0)
            + (0.03 if lead_mentions > 0 else 0.0)
        )
        if weak_mentions == mention_count and title_mentions == 0:
            score *= 0.72
        score *= breadth
        score = max(0.0, min(1.0, score))

        relation_type = "mention"
        if title_strict_mentions > 0 or (title_mentions > 0 and max_confidence >= 0.72):
            relation_type = "primary_company"
        elif score >= 0.62:
            relation_type = "company_context"
        elif len(tickers) >= 4 and score >= 0.34:
            relation_type = "sector_context"

        evidence_json = json.dumps(
            {
                "mention_count": mention_count,
                "title_mentions": title_mentions,
                "lead_mentions": lead_mentions,
                "strict_mentions": strict_mentions,
                "title_strict_mentions": title_strict_mentions,
                "weak_mentions": weak_mentions,
                "max_confidence": round(max_confidence, 6),
                "confidence_sum": round(confidence_sum, 6),
                "breadth_multiplier": breadth,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        rows.append(
            ArticleRelevance(
                article_id=article_id,
                ticker=ticker,
                lane=lane,
                relevance_score=score,
                relation_type=relation_type,
                is_primary=False,
                confidence=max_confidence,
                evidence_json=evidence_json,
            )
        )

    ranked = _rank_relevance_rows(rows)
    if ranked:
        top = ranked[0]
        rows = [
            ArticleRelevance(
                article_id=row.article_id,
                ticker=row.ticker,
                lane=row.lane,
                relevance_score=row.relevance_score,
                relation_type=row.relation_type,
                is_primary=row.ticker == top.ticker,
                confidence=row.confidence,
                evidence_json=row.evidence_json,
            )
            for row in ranked
        ]
    return rows


def score_article_relevance(
    *,
    article_id: str,
    title: str,
    description: str,
    body: str,
    links: Sequence[EntityLink],
) -> List[ArticleRelevance]:
    out: List[ArticleRelevance] = []
    for lane in ("high_precision", "high_recall"):
        lane_links = [link for link in links if str(link.lane or "").strip().lower() == lane]
        out.extend(
            _score_link_rows(
                article_id=article_id,
                lane=lane,
                title=title,
                description=description,
                body=body,
                links=lane_links,
            )
        )
    return out


def infer_ticker_relevance_from_text(
    *,
    title: str,
    body: str,
    tickers: Sequence[str],
) -> List[ArticleRelevance]:
    normalized_tickers = sorted({str(ticker or "").strip().upper() for ticker in tickers if str(ticker or "").strip()})
    if not normalized_tickers:
        return []
    breadth = _breadth_multiplier(len(normalized_tickers))
    rows: List[ArticleRelevance] = []
    title_text = str(title or "")
    body_text = str(body or "")
    for ticker in normalized_tickers:
        token = re.escape(ticker)
        title_symbol_hits = len(re.findall(rf"\bASX\s*[:\-]\s*{token}\b", title_text, flags=re.IGNORECASE))
        title_hits = len(re.findall(rf"(?<![A-Za-z0-9]){token}(?:\.AX)?(?![A-Za-z0-9])", title_text, flags=re.IGNORECASE))
        body_symbol_hits = len(re.findall(rf"\bASX\s*[:\-]\s*{token}\b", body_text, flags=re.IGNORECASE))
        body_hits = len(re.findall(rf"(?<![A-Za-z0-9]){token}(?:\.AX)?(?![A-Za-z0-9])", body_text, flags=re.IGNORECASE))
        mention_hits = title_symbol_hits + title_hits + body_symbol_hits + body_hits
        base_score = 0.18 if len(normalized_tickers) == 1 else 0.0
        score = (
            base_score
            + min(0.26, (0.18 * title_symbol_hits) + (0.08 * title_hits))
            + min(0.22, (0.10 * body_symbol_hits) + (0.04 * body_hits))
        )
        score *= breadth
        score = max(0.0, min(1.0, score))
        relation_type = "mention"
        if title_symbol_hits > 0 or title_hits > 0:
            relation_type = "primary_company"
        elif score >= 0.50:
            relation_type = "company_context"
        elif len(normalized_tickers) >= 4:
            relation_type = "sector_context"
        evidence_json = json.dumps(
            {
                "title_symbol_hits": title_symbol_hits,
                "title_hits": title_hits,
                "body_symbol_hits": body_symbol_hits,
                "body_hits": body_hits,
                "mention_hits": mention_hits,
                "breadth_multiplier": breadth,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        confidence = min(1.0, ((0.2 if len(normalized_tickers) == 1 else 0.0) + (0.2 * title_symbol_hits) + (0.1 * title_hits)))
        rows.append(
            ArticleRelevance(
                article_id="",
                ticker=ticker,
                lane="derived",
                relevance_score=score,
                relation_type=relation_type,
                is_primary=False,
                confidence=confidence,
                evidence_json=evidence_json,
            )
        )

    ranked = _rank_relevance_rows(rows)
    if ranked:
        top = ranked[0]
        rows = [
            ArticleRelevance(
                article_id=row.article_id,
                ticker=row.ticker,
                lane=row.lane,
                relevance_score=row.relevance_score,
                relation_type=row.relation_type,
                is_primary=row.ticker == top.ticker,
                confidence=row.confidence,
                evidence_json=row.evidence_json,
            )
            for row in ranked
        ]
    return rows


def parse_ticker_relevance_json(value: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(value, dict):
        return {str(key).strip().upper(): dict(item or {}) for key, item in value.items() if str(key).strip()}
    raw = str(value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for key, item in parsed.items():
        ticker = str(key or "").strip().upper()
        if not ticker or not isinstance(item, dict):
            continue
        out[ticker] = dict(item)
    return out


def ticker_relevance_for_symbol(value: Any, ticker: str) -> Dict[str, Any]:
    ticker_key = str(ticker or "").strip().upper()
    if not ticker_key:
        return {}
    return dict(parse_ticker_relevance_json(value).get(ticker_key) or {})
