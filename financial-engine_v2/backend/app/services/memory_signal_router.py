from __future__ import annotations

import re
from typing import Any

from app.services.company_memory import CompanyMemoryStore
from app.services.market_memory import MarketMemoryStore
from app.services.market_sector_inference import infer_sector

_MACRO_TOPICS = {
    "China stimulus": ("china stimulus", "beijing stimulus"),
    "China demand": ("china demand", "chinese demand"),
    "Interest rates": ("interest rate", "rates", "rate cuts", "rate hikes"),
    "Inflation": ("inflation", "cpi"),
    "USD": ("us dollar", "usd", "dollar strength"),
}
_BUSINESS_THEMES = {
    "costs": ("cost", "cost-out", "cost out", "productivity", "efficiency"),
    "growth": ("growth", "volume", "ramp", "expansion", "pipeline"),
    "production": ("production", "output", "tonnes", "grade", "throughput"),
    "capital": ("capex", "capital", "investment", "spend"),
    "pricing": ("price", "pricing", "premium", "discount", "realised"),
    "demand": ("demand", "orders", "consumption", "sales"),
    "supply": ("supply", "inventory", "supply chain", "logistics", "freight"),
    "operations": ("operations", "outage", "downtime", "rail", "port", "mine"),
    "balance_sheet": ("balance sheet", "cash", "liquidity", "debt", "funding"),
    "regulatory": ("regulatory", "approval", "permit", "policy", "tax", "royalty"),
}
_TIME_REF_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bnear[ -]?term\b", "near_term"),
    (r"\bshort[ -]?term\b", "short_term"),
    (r"\blong[ -]?term\b", "long_term"),
    (r"\bnext quarter\b", "next_quarter"),
    (r"\bthis quarter\b", "this_quarter"),
    (r"\bnext half\b", "next_half"),
    (r"\bsecond half\b|\b2h\b", "second_half"),
    (r"\bfirst half\b|\b1h\b", "first_half"),
    (r"\bfy\s?20\d{2}\b", "fiscal_year"),
    (r"\bq[1-4]\b", "quarter"),
    (r"\b20\d{2}\b", "calendar_year"),
)
_CLAUSE_SPLIT_RE = re.compile(r"\s+(?:and|but|while)\s+", re.IGNORECASE)
_VAGUE_PATTERNS = (
    "things look",
    "looks good",
    "looks bad",
    "positive story",
    "negative story",
    "watch this space",
    "interesting setup",
    "worth watching",
    "could be important",
)
_LOW_INFORMATION_WORDS = {
    "better",
    "worse",
    "good",
    "bad",
    "interesting",
    "positive",
    "negative",
    "strong",
    "weak",
}
_SIGNAL_KIND_BONUS = {
    "observed_fact": 0.08,
    "management_guidance": 0.06,
    "strategic_initiative": 0.04,
    "catalyst": 0.05,
    "risk": 0.05,
    "operating_context": 0.03,
    "interpretation": -0.03,
}
_SIGNAL_KIND_MATERIALITY = {
    "observed_fact": 0.62,
    "management_guidance": 0.72,
    "interpretation": 0.5,
    "risk": 0.82,
    "catalyst": 0.82,
    "strategic_initiative": 0.76,
    "operating_context": 0.58,
}
_REPLACEABLE_SIGNAL_KINDS = {
    "management_guidance",
    "strategic_initiative",
    "operating_context",
    "observed_fact",
}
_STATEMENT_TEXT_KEYS = (
    "statement",
    "text",
    "claim",
    "event",
    "risk",
    "catalyst",
    "summary",
)
_STATEMENT_TARGET_KEYS = (
    "ticker",
    "tickers",
    "target_ticker",
    "target_tickers",
    "company_ticker",
    "company_tickers",
    "entity_id",
    "entity_ids",
    "company",
    "companies",
)


def signals_from_commentary_memo(memo: dict[str, Any]) -> list[dict[str, Any]]:
    source = f"commentary:{str(memo.get('source_type') or 'unknown').strip()}"
    source_id = str(memo.get("source_id") or "").strip()
    tickers = _normalize_tickers(memo.get("tickers") or [])
    source_type = str(memo.get("source_type") or "")

    signals: list[dict[str, Any]] = []
    for source_family, statements in (
        ("claim", memo.get("claims") or []),
        ("catalyst", memo.get("catalysts") or []),
        ("risk", memo.get("risks") or []),
    ):
        for item in _statement_candidates(statements, tickers=tickers):
            signal_kind = _classify_signal_kind(
                item["statement"], default_family=source_family
            )
            confidence = _commentary_confidence(
                source_type,
                signal_kind=signal_kind,
                specificity=item["specificity"],
            )
            materiality = _score_materiality(
                signal_kind,
                specificity=item["specificity"],
                themes=item["themes"],
            )
            signals.extend(
                _signals_for_statement(
                    item["statement"],
                    signal_type=signal_kind,
                    tickers=tickers,
                    explicit_tickers=item["explicit_tickers"],
                    source=source,
                    source_id=source_id,
                    confidence=confidence,
                    materiality=materiality,
                    persistence=_signal_persistence(
                        signal_kind,
                        time_horizon=str(memo.get("time_horizon") or ""),
                        time_refs=item["time_refs"],
                    ),
                    metadata={
                        "speaker": str(memo.get("speaker") or "").strip(),
                        "sentiment": str(memo.get("sentiment") or "").strip().lower(),
                        "published_at": str(memo.get("published_at") or "").strip(),
                        "signal_family": source_family,
                        "signal_kind": signal_kind,
                        "specificity": item["specificity"],
                        "themes": item["themes"],
                        "theme_key": item["theme_key"],
                        "time_refs": item["time_refs"],
                        "replaceable": signal_kind in _REPLACEABLE_SIGNAL_KINDS,
                    },
                )
            )
    return _dedupe_signals(signals)


def signals_from_news_memo(memo: dict[str, Any]) -> list[dict[str, Any]]:
    source = f"news:{str(memo.get('provider') or 'unknown').strip()}"
    source_id = str(memo.get("source_id") or "").strip()
    tickers = _normalize_tickers(memo.get("tickers") or [])
    impact_magnitude = str(memo.get("impact_magnitude") or "")

    signals: list[dict[str, Any]] = []
    for source_family, statements in (
        ("event", memo.get("key_events") or []),
        ("claim", memo.get("claims") or []),
        ("risk", memo.get("risks") or []),
    ):
        for item in _statement_candidates(statements, tickers=tickers):
            signal_kind = _classify_signal_kind(
                item["statement"], default_family=source_family
            )
            confidence = _news_confidence(
                signal_kind=signal_kind,
                specificity=item["specificity"],
            )
            materiality = _score_materiality(
                signal_kind,
                specificity=item["specificity"],
                themes=item["themes"],
                impact_magnitude=impact_magnitude,
            )
            signals.extend(
                _signals_for_statement(
                    item["statement"],
                    signal_type=signal_kind,
                    tickers=tickers,
                    explicit_tickers=item["explicit_tickers"],
                    source=source,
                    source_id=source_id,
                    confidence=confidence,
                    materiality=materiality,
                    persistence=_signal_persistence(
                        signal_kind,
                        time_horizon="",
                        time_refs=item["time_refs"],
                    ),
                    metadata={
                        "provider": str(memo.get("provider") or "").strip(),
                        "sentiment": str(memo.get("sentiment") or "").strip().lower(),
                        "impact_magnitude": str(memo.get("impact_magnitude") or "")
                        .strip()
                        .lower(),
                        "published_at": str(memo.get("published_at") or "").strip(),
                        "signal_family": source_family,
                        "signal_kind": signal_kind,
                        "specificity": item["specificity"],
                        "themes": item["themes"],
                        "theme_key": item["theme_key"],
                        "time_refs": item["time_refs"],
                        "replaceable": signal_kind in _REPLACEABLE_SIGNAL_KINDS,
                    },
                )
            )
    return _dedupe_signals(signals)


def route_signals(
    signals: list[dict[str, Any]],
    *,
    company_memory_store: CompanyMemoryStore | None = None,
    market_memory_store: MarketMemoryStore | None = None,
) -> dict[str, Any]:
    company_store = company_memory_store or CompanyMemoryStore()
    market_store = market_memory_store or MarketMemoryStore()
    company_results: list[dict[str, Any]] = []
    market_results: list[dict[str, Any]] = []

    for signal in signals:
        if signal.get("scope") in {"sector", "macro"}:
            market_results.append(market_store.update_market_memory(signal))
        else:
            company_id = str(signal.get("entity_id") or "").strip().upper()
            if not company_id:
                continue
            company_results.append(
                company_store.update_company_memory(company_id, signal)
            )

    return {
        "company_memory_count": len(company_results),
        "market_memory_count": len(market_results),
        "company_memory_results": company_results,
        "market_memory_results": market_results,
    }


def _signals_for_statement(
    statement: str,
    *,
    signal_type: str,
    tickers: list[str],
    explicit_tickers: list[str] | None = None,
    source: str,
    source_id: str,
    confidence: float,
    materiality: float,
    persistence: str,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for ticker in _company_targets_for_statement(
        statement,
        tickers=tickers,
        explicit_tickers=explicit_tickers or [],
    ):
        signals.append(
            {
                "type": signal_type,
                "statement": statement,
                "entity_id": ticker,
                "confidence": confidence,
                "materiality": materiality,
                "persistence": persistence,
                "status": "active",
                "source": source,
                "source_id": source_id,
                "metadata": metadata,
            }
        )

    market_signal = _market_signal_for_statement(
        statement,
        signal_type=signal_type,
        tickers=tickers,
        source=source,
        source_id=source_id,
        confidence=confidence,
        materiality=materiality,
        persistence=persistence,
        metadata=metadata,
    )
    if market_signal is not None:
        signals.append(market_signal)
    return signals


def _company_targets_for_statement(
    statement: str,
    *,
    tickers: list[str],
    explicit_tickers: list[str],
) -> list[str]:
    normalized_tickers = _normalize_tickers(tickers)
    normalized_explicit = _normalize_tickers(explicit_tickers)
    if normalized_explicit:
        if normalized_tickers:
            allowed = set(normalized_tickers)
            normalized_explicit = [
                ticker for ticker in normalized_explicit if ticker in allowed
            ]
        return normalized_explicit if len(normalized_explicit) == 1 else []

    if len(normalized_tickers) == 1:
        return normalized_tickers

    text_targets = [
        ticker
        for ticker in normalized_tickers
        if _ticker_is_explicitly_mentioned(statement, ticker)
    ]
    return text_targets if len(text_targets) == 1 else []


def _ticker_is_explicitly_mentioned(statement: str, ticker: str) -> bool:
    normalized = str(ticker or "").strip().upper()
    if not normalized:
        return False
    return bool(
        re.search(
            rf"(?<![A-Z0-9])\$?{re.escape(normalized)}(?:\.AX)?(?![A-Z0-9])",
            str(statement or ""),
            flags=re.IGNORECASE,
        )
    )


def _market_signal_for_statement(
    statement: str,
    *,
    signal_type: str,
    tickers: list[str],
    source: str,
    source_id: str,
    confidence: float,
    materiality: float,
    persistence: str,
    metadata: dict[str, Any],
) -> dict[str, Any] | None:
    macro_topic = _infer_macro_topic(statement)
    if macro_topic is not None:
        return {
            "scope": "macro",
            "macro_topic": macro_topic,
            "type": _market_signal_type(signal_type, scope="macro"),
            "statement": statement,
            "confidence": confidence,
            "materiality": materiality,
            "persistence": persistence,
            "status": "active",
            "source": source,
            "source_id": source_id,
            "metadata": metadata,
        }

    sector = _infer_sector(statement, tickers)
    if sector is not None:
        return {
            "scope": "sector",
            "sector": sector,
            "type": _market_signal_type(signal_type, scope="sector"),
            "statement": statement,
            "confidence": confidence,
            "materiality": materiality,
            "persistence": persistence,
            "status": "active",
            "source": source,
            "source_id": source_id,
            "linked_tickers": tickers,
            "metadata": metadata,
        }
    return None


def _market_signal_type(signal_type: str, *, scope: str) -> str:
    is_risk = signal_type == "risk"
    if scope == "macro":
        return "macro_risk" if is_risk else "macro_theme"
    return "sector_risk" if is_risk else "sector_trend"


def _infer_sector(statement: str, tickers: list[str]) -> str | None:
    return infer_sector(statement, tickers)


def _infer_macro_topic(statement: str) -> str | None:
    lowered = statement.lower()
    for topic, keywords in _MACRO_TOPICS.items():
        if any(keyword in lowered for keyword in keywords):
            return topic
    return None


def _commentary_confidence(
    source_type: str,
    *,
    signal_kind: str,
    specificity: float,
) -> float:
    normalized = str(source_type or "").strip().lower()
    base = 0.6
    if normalized == "market_commentary":
        base = 0.58
    elif normalized in {"podcast_transcript", "youtube_transcript"}:
        base = 0.54
    return _clamp(
        base + (specificity * 0.25) + _SIGNAL_KIND_BONUS.get(signal_kind, 0.0)
    )


def _news_confidence(*, signal_kind: str, specificity: float) -> float:
    return _clamp(
        0.62 + (specificity * 0.22) + _SIGNAL_KIND_BONUS.get(signal_kind, 0.0)
    )


def _news_materiality(impact_magnitude: str) -> float:
    normalized = str(impact_magnitude or "").strip().lower()
    if normalized == "material":
        return 0.9
    if normalized == "moderate":
        return 0.7
    if normalized == "minor":
        return 0.5
    return 0.6


def _score_materiality(
    signal_kind: str,
    *,
    specificity: float,
    themes: list[str],
    impact_magnitude: str = "",
) -> float:
    score = _SIGNAL_KIND_MATERIALITY.get(signal_kind, 0.6)
    score = (
        max(score, _news_materiality(impact_magnitude)) if impact_magnitude else score
    )
    if themes:
        score += 0.04
    if any(
        theme in {"capital", "production", "pricing", "regulatory"} for theme in themes
    ):
        score += 0.05
    if specificity < 0.45:
        score -= 0.08
    return _clamp(score)


def _persistence_from_time_horizon(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"short-term", "short term", "near-term", "near term"}:
        return "short"
    if normalized in {"long-term", "long term"}:
        return "long"
    return "medium"


def _signal_persistence(
    signal_kind: str, *, time_horizon: str, time_refs: list[str]
) -> str:
    if signal_kind == "operating_context":
        return "short"
    if signal_kind == "strategic_initiative":
        return "long"
    if signal_kind == "management_guidance" and any(
        ref in {"near_term", "short_term", "next_quarter", "this_quarter", "next_half"}
        for ref in time_refs
    ):
        return "short"
    return _persistence_from_time_horizon(time_horizon)


def _normalize_statements(values: Any) -> list[str]:
    items = values if isinstance(values, list) else [values]
    results: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        results.append(text)
    return results


def _statement_candidates(values: Any, *, tickers: list[str]) -> list[dict[str, Any]]:
    items = values if isinstance(values, list) else [values]
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        explicit_tickers = _explicit_tickers_from_statement_item(item)
        for text in _statement_text_values(item):
            for part in _split_atomic_statements(text):
                statement = _normalize_statement_text(part, tickers=tickers)
                themes = _infer_themes(statement)
                time_refs = _extract_time_refs(statement)
                specificity = _statement_specificity(
                    statement,
                    themes=themes,
                    time_refs=time_refs,
                    tickers=tickers,
                )
                if _reject_low_specificity(statement, specificity):
                    continue
                key = _statement_dedupe_key(statement)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    {
                        "statement": statement,
                        "explicit_tickers": explicit_tickers,
                        "themes": themes,
                        "theme_key": themes[0]
                        if themes
                        else _fallback_theme_key(statement),
                        "time_refs": time_refs,
                        "specificity": specificity,
                    }
                )
    return candidates


def _statement_text_values(item: Any) -> list[str]:
    if isinstance(item, dict):
        for key in _STATEMENT_TEXT_KEYS:
            if key not in item:
                continue
            values = _flatten_values(item.get(key))
            if values:
                return [value for value in values if value]
        return []
    return _normalize_statements(item)


def _explicit_tickers_from_statement_item(item: Any) -> list[str]:
    if not isinstance(item, dict):
        return []
    values: list[Any] = []
    for key in _STATEMENT_TARGET_KEYS:
        values.extend(_flatten_values(item.get(key)))
    return _normalize_tickers(values)


def _flatten_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        return []
    if isinstance(value, (list, tuple, set)):
        values: list[str] = []
        for item in value:
            values.extend(_flatten_values(item))
        return values
    text = str(value or "").strip()
    return [text] if text else []


def _split_atomic_statements(value: str) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    fragments = [text]
    for separator in ("\n", ";", "•"):
        next_fragments: list[str] = []
        for fragment in fragments:
            next_fragments.extend(
                part for part in fragment.split(separator) if part.strip()
            )
        fragments = next_fragments or fragments

    atomic: list[str] = []
    for fragment in fragments:
        parts = re.split(r"(?<=[.!?])\s+", fragment)
        for part in parts:
            part = part.strip(" .")
            if not part:
                continue
            splits = _split_on_conjunctions(part)
            atomic.extend(splits or [part])
    return atomic


def _split_on_conjunctions(value: str) -> list[str]:
    parts = _CLAUSE_SPLIT_RE.split(value)
    if len(parts) <= 1:
        return []
    if not all(_looks_like_clause(part) for part in parts):
        return []
    return [part.strip(" .,") for part in parts if part.strip(" .,")]


def _looks_like_clause(value: str) -> bool:
    lowered = str(value or "").strip().lower()
    if len(lowered.split()) < 4:
        return False
    return bool(
        re.search(
            r"\b(is|are|was|were|remains|expects|guides|targets|plans|said|says|looks|points|implies|supports|pressures|improves|declines|increases|falls|rises)\b",
            lowered,
        )
    )


def _normalize_statement_text(value: str, *, tickers: list[str]) -> str:
    normalized = " ".join(str(value or "").strip().split())
    for ticker in tickers:
        normalized = re.sub(
            rf"\$?\b{re.escape(ticker)}(?:\.AX)?\b",
            ticker,
            normalized,
            flags=re.IGNORECASE,
        )
    return normalized.strip(" .")


def _classify_signal_kind(statement: str, *, default_family: str) -> str:
    if default_family == "risk":
        return "risk"
    if default_family == "catalyst":
        return "catalyst"
    lowered = statement.lower()
    if any(
        cue in lowered
        for cue in (
            "management",
            "guidance",
            "guides",
            "expects",
            "expects to",
            "target",
            "targets",
            "prioritising",
            "prioritizing",
            "plans to",
            "outlook",
        )
    ):
        return "management_guidance"
    if any(
        cue in lowered
        for cue in (
            "initiative",
            "strategy",
            "program",
            "expansion",
            "acquisition",
            "automation",
            "partnership",
            "cost-out",
            "cost out",
        )
    ):
        return "strategic_initiative"
    if any(
        cue in lowered
        for cue in (
            "implies",
            "suggests",
            "points to",
            "signals",
            "reflects",
            "looks like",
        )
    ):
        return "interpretation"
    if any(
        cue in lowered
        for cue in (
            "outage",
            "constraint",
            "downtime",
            "labour",
            "labor",
            "weather",
            "supply chain",
            "rail",
            "port",
        )
    ):
        return "operating_context"
    if default_family == "event":
        return "observed_fact"
    if re.search(r"\b\d", lowered):
        return "observed_fact"
    return "observed_fact" if default_family == "claim" else "operating_context"


def _infer_themes(statement: str) -> list[str]:
    lowered = statement.lower()
    themes = [
        theme
        for theme, keywords in _BUSINESS_THEMES.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    if not themes:
        if "guidance" in lowered or "outlook" in lowered:
            themes.append("guidance")
        elif "risk" in lowered:
            themes.append("risk")
    return themes


def _extract_time_refs(statement: str) -> list[str]:
    lowered = statement.lower()
    refs: list[str] = []
    for pattern, label in _TIME_REF_PATTERNS:
        if re.search(pattern, lowered):
            refs.append(label)
    return refs


def _statement_specificity(
    statement: str,
    *,
    themes: list[str],
    time_refs: list[str],
    tickers: list[str],
) -> float:
    lowered = statement.lower()
    words = [token for token in re.findall(r"[a-z0-9]+", lowered) if token]
    unique_words = len(set(words))
    score = 0.25 if len(words) >= 6 else 0.1
    score += min(unique_words / 20, 0.25)
    if any(token.isdigit() for token in words):
        score += 0.12
    if themes:
        score += min(len(themes) * 0.08, 0.16)
    if time_refs:
        score += 0.1
    if any(ticker.lower() in lowered for ticker in tickers):
        score += 0.08
    if sum(word in _LOW_INFORMATION_WORDS for word in words) >= max(1, len(words) // 3):
        score -= 0.18
    return round(_clamp(score, minimum=0.0), 2)


def _reject_low_specificity(statement: str, specificity: float) -> bool:
    lowered = statement.lower()
    if specificity < 0.28:
        return True
    return any(pattern in lowered for pattern in _VAGUE_PATTERNS)


def _statement_dedupe_key(statement: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", statement.lower())
    return " ".join(normalized.split())


def _fallback_theme_key(statement: str) -> str:
    tokens = [
        token for token in re.findall(r"[a-z0-9]+", statement.lower()) if len(token) > 2
    ]
    return " ".join(tokens[:4])


def _clamp(value: float, minimum: float = 0.2, maximum: float = 0.95) -> float:
    return max(minimum, min(maximum, round(float(value), 2)))


def _normalize_tickers(values: Any) -> list[str]:
    return [ticker.upper() for ticker in _normalize_statements(values)]


def _dedupe_signals(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for signal in signals:
        target = str(
            signal.get("entity_id")
            or signal.get("sector")
            or signal.get("macro_topic")
            or ""
        )
        key = (
            str(signal.get("type") or ""),
            target,
            _statement_dedupe_key(str(signal.get("statement") or "")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(signal)
    return deduped
