from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from shared.evidence_labels import (
    apply_context_only_boundaries,
    canonical_financial_truth_from_labels,
    context_only_from_labels,
)

MARKET_PRICE_OR_TECHNICAL_TREND = "market_price_or_technical_trend"
FINANCIAL_METRIC = "financial_metric"
FILING_CONTEXT = "filing_context"
BUYBACK_ACTIVITY = "buyback_activity"
TARIFF_REGULATORY = "tariff_regulatory"
LOCAL_HOLDINGS = "local_holdings"
RECENT_NEWS_OR_UPDATE = "recent_news_or_update"
RECENT_NEWS_EVENT = "recent_news_event"
LOCAL_NEWS_ONLY_GUARD_REASON = "local_news_only_insufficient_claim_verified_news"

CLAIM_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    MARKET_PRICE_OR_TECHNICAL_TREND: (
        "market_data",
        "price_series",
        "technical_indicator",
    ),
    FINANCIAL_METRIC: ("extracted_metric", "financial_statement"),
    FILING_CONTEXT: ("filing",),
    BUYBACK_ACTIVITY: ("buyback_filing", "filing", "news"),
    TARIFF_REGULATORY: ("regulatory_source", "filing", "news"),
    LOCAL_HOLDINGS: ("local_personal_data",),
    RECENT_NEWS_OR_UPDATE: (RECENT_NEWS_EVENT,),
}

_MARKET_TREND_CLAIM_RE = re.compile(
    r"\b(?:price|share price|stock|market|technical|chart|rsi|macd|"
    r"moving average|sma|ema|trend)\b.{0,90}\b(?:bearish|bullish|"
    r"downtrend|uptrend|falling|rising|weakening|strengthening|selloff|"
    r"rally|plunge|breakout|support|resistance|overbought|oversold)\b|"
    r"\b(?:bearish|bullish|downtrend|uptrend)\b.{0,90}\b(?:price|trend|"
    r"technical|chart|market)\b|"
    r"\b(?:price trend|technical trend|trend regime|market trend)\b",
    re.IGNORECASE,
)
_FINANCIAL_METRIC_CLAIM_RE = re.compile(
    r"\b(?:revenue|profit|loss|earnings|ebitda|ebit|npata|eps|margin|"
    r"gross margin|cash balance|cash flow|operating cash|capex|dividend|"
    r"sales|guidance|free cash flow|debt|net debt)\b",
    re.IGNORECASE,
)
_FILING_CONTEXT_RE = re.compile(
    r"\b(?:filing|announcement|annual report|half[- ]year report|quarterly|"
    r"appendix\s+[34]?[bcde]?|asx release|lodged|notice)\b",
    re.IGNORECASE,
)
_BUYBACK_RE = re.compile(
    r"\b(?:buy[- ]?back|share repurchase|repurchase program|appendix\s+3c|"
    r"appendix\s+3d|appendix\s+3e)\b",
    re.IGNORECASE,
)
_TARIFF_REGULATORY_RE = re.compile(
    r"\b(?:tariff|regulator|regulatory|customs|anti[- ]?dumping|fda|tga|"
    r"accc|asic|asx query|approval|licen[cs]e|sanction|compliance)\b",
    re.IGNORECASE,
)
_LOCAL_HOLDINGS_RE = re.compile(
    r"\b(?:my holdings|my portfolio|local holdings|personal holdings|"
    r"portfolio positions|my positions|personal positions|cost base|"
    r"unrealized (?:p&l|profit|loss)|unrealised (?:p&l|profit|loss))\b",
    re.IGNORECASE,
)
_RECENT_NEWS_OR_UPDATE_RE = re.compile(
    r"\b(?:what happened|happened with|this week|"
    r"recent (?:news|update|updates|coverage|development|developments)|"
    r"(?:today|yesterday)'?s? (?:news|update|updates|announcement|announcements|development|developments)|"
    r"latest (?:news|update|updates|announcement|announcements|development|developments)|"
    r"news update|market update|recall|resignation|event|catalyst)\b",
    re.IGNORECASE,
)
_MISSING_CANONICAL_FINANCIAL_ROWS_RE = re.compile(
    r"\b(?:no canonical financial rows were returned|no canonical financial rows|"
    r"financial rows (?:were )?(?:not returned|unavailable|missing)|"
    r"no (?:extracted|canonical) financial (?:metrics|rows))\b",
    re.IGNORECASE,
)
_LOCAL_NEWS_ONLY_REQUEST_RE = re.compile(
    r"\b(?:latest|recent|current|available|local)\s+local\s+news\b|"
    r"\blocal\s+news\s+evidence\s+only\b|"
    r"\buse\s+local\s+news\s+evidence\s+only\b|"
    r"\blocal[_ -]news[_ -]context\b",
    re.IGNORECASE,
)

_PRICE_SOURCE_PREFIXES = (
    "local_price:",
    "price:",
    "price_query:",
    "price_on_date:",
    "price_range:",
    "market_update:",
)
_TECHNICAL_SOURCE_PREFIXES = ("tv_indicators:",)
_NON_EVIDENCE_LABELS = {
    "no_hit",
    "missing_required_evidence",
    "degraded_runtime",
}
_NO_HIT_DOC_TYPES = {"operational_no_hit", "runtime_failure", "missing_required_evidence"}
VISIBLE_GAP_LABELS = (
    "market_data_missing",
    "unsupported_or_not_verified",
    "metric_extraction_missing",
    "insufficient_for_recent_news",
    "missing_required_evidence",
)

_VISIBLE_GAP_COPY = {
    "market_data_missing": (
        "market_data_missing: price or technical trend claims are not verified by "
        "visible market-price or technical evidence."
    ),
    "unsupported_or_not_verified": (
        "unsupported_or_not_verified: treat unsupported claim families as "
        "unverified context, not verified conclusions."
    ),
    "metric_extraction_missing": (
        "metric_extraction_missing: canonical metric or financial-row evidence "
        "is missing or incomplete."
    ),
    "insufficient_for_recent_news": (
        "insufficient_for_recent_news: recent-news or recent-update claims need "
        "actual claim-verified news/event evidence; price, filing, "
        "local-news-context, context-only, and numeric financial-truth context "
        "are not enough."
    ),
    "missing_required_evidence": (
        "missing_required_evidence: required evidence is absent for at least "
        "one claim."
    ),
}


def _string_array(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [str(item).strip() for item in value if str(item or "").strip()]
    return []


def _source_value(source: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _source_labels(source: Mapping[str, Any]) -> set[str]:
    labels: set[str] = set()
    for key in ("evidence_labels", "source_labels", "evidence_label", "source_label"):
        labels.update(_string_array(source.get(key)))
    return apply_context_only_boundaries(labels)


def _source_role_tokens(source: Mapping[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for key in (
        "source_role_labels",
        "source_roles",
        "source_role",
        "evidence_role",
        "evidence_roles",
        "evidence_kind",
        "source_type",
    ):
        tokens.update(item.lower() for item in _string_array(source.get(key)))
    return tokens


def detect_claim_families(answer_text: str, metadata: Mapping[str, Any] | None = None) -> set[str]:
    """Return broad claim families that need matching evidence classes."""
    text = str(answer_text or "")
    families: set[str] = set()
    if re.match(r"\s*Recent videos from\b", text, re.IGNORECASE):
        return families
    if _MARKET_TREND_CLAIM_RE.search(text):
        families.add(MARKET_PRICE_OR_TECHNICAL_TREND)
    if _FINANCIAL_METRIC_CLAIM_RE.search(text):
        families.add(FINANCIAL_METRIC)
    if _FILING_CONTEXT_RE.search(text):
        families.add(FILING_CONTEXT)
    if _BUYBACK_RE.search(text):
        families.add(BUYBACK_ACTIVITY)
    if _TARIFF_REGULATORY_RE.search(text):
        families.add(TARIFF_REGULATORY)
    if _LOCAL_HOLDINGS_RE.search(text):
        families.add(LOCAL_HOLDINGS)
    if _RECENT_NEWS_OR_UPDATE_RE.search(text):
        families.add(RECENT_NEWS_OR_UPDATE)

    metadata = metadata or {}
    canonical_intent = str(metadata.get("canonical_intent") or metadata.get("intent") or "").strip().lower()
    if canonical_intent == "holdings":
        families.add(LOCAL_HOLDINGS)
    return families


def evidence_categories_for_source(source: Mapping[str, Any]) -> set[str]:
    """Classify a visible source into the evidence categories it can satisfy."""
    labels = _source_labels(source)
    role_tokens = _source_role_tokens(source)
    source_id = _source_value(source, "source_id", "sourceId", "chunk_id")
    kind = _source_value(source, "kind").lower()
    doc_type = _source_value(source, "doc_type", "docType", "source_type", "source").lower()
    haystack = " ".join(
        value
        for value in (
            source_id,
            kind,
            doc_type,
            _source_value(source, "title", "source_name"),
            _source_value(source, "snippet", "text", "excerpt", "content"),
            " ".join(sorted(labels)),
        )
        if value
    ).lower()

    categories: set[str] = set()
    if "degraded_runtime" in labels or source_id.startswith("runtime_failure:") or doc_type == "runtime_failure":
        categories.add("degraded_runtime")
    if labels & {"no_hit", "missing_required_evidence"} or doc_type in _NO_HIT_DOC_TYPES:
        categories.add("no_hit")
    claim_verified = "claim_verified" in labels
    context_only_label = "context_only" in labels
    context_only = context_only_label and not claim_verified
    if context_only:
        categories.add("context_only")
    if "local_personal_data" in labels:
        categories.add("local_personal_data")

    non_evidence = bool(labels & _NON_EVIDENCE_LABELS) or doc_type in _NO_HIT_DOC_TYPES
    if non_evidence:
        return categories

    if source_id.startswith(_PRICE_SOURCE_PREFIXES):
        categories.update({"market_data", "price_series"})
    if source_id.startswith(_TECHNICAL_SOURCE_PREFIXES):
        categories.update({"market_data", "technical_indicator"})
    if re.search(r"\b(?:market_data|market price|price_data|price data)\b", haystack):
        categories.update({"market_data", "price_series"})
    if re.search(r"\b(?:technical_indicator|technical indicators|rsi|macd|moving average)\b", haystack):
        categories.update({"market_data", "technical_indicator"})

    financial_truth_text = re.search(
        r"\b(?:financial_truth|financial statement|income statement|balance sheet|cash flow|"
        r"extracted metric|canonical financial|annual_report|half_year|quarterly)\b",
        haystack,
    )
    if canonical_financial_truth_from_labels(labels) or (
        financial_truth_text and not context_only_from_labels(labels)
    ):
        categories.update({"extracted_metric", "financial_statement"})
        if "claim_verified" not in labels:
            categories.add("financial_truth_numeric")

    if kind in {"document", "rag"} or re.search(
        r"\b(?:asx_announcement|announcement|filing|annual report|appendix|notice)\b",
        haystack,
    ):
        categories.add("filing")
    if not context_only_label and (
        kind == "news"
        or re.search(
            r"\b(?:asx_announcement|announcement|news article|notice|release)\b",
            haystack,
        )
    ):
        categories.add("event_source")
    if _BUYBACK_RE.search(haystack):
        categories.add("buyback_filing")
    if _TARIFF_REGULATORY_RE.search(haystack):
        categories.add("regulatory_source")
    news_like = (
        kind == "news"
        or source_id.startswith("news:")
        or "local_news_context" in labels
        or "news" in doc_type
        or "news" in role_tokens
    )
    event_like = news_like or bool(
        role_tokens
        & {
            "event_source",
            "recent_news_event",
            "news_event",
            "announcement_event",
        }
    )
    if news_like:
        categories.add("news")
    if claim_verified and event_like and not context_only_label:
        categories.add(RECENT_NEWS_EVENT)
    if claim_verified:
        categories.add("claim_verified")
    return categories


def evidence_categories_for_sources(sources: Sequence[Mapping[str, Any]]) -> set[str]:
    categories: set[str] = set()
    for source in sources:
        categories.update(evidence_categories_for_source(source))
    return categories


def _missing_category_for_claim_family(claim_family: str) -> str:
    if claim_family == MARKET_PRICE_OR_TECHNICAL_TREND:
        return "market_data"
    if claim_family == FINANCIAL_METRIC:
        return "metric_extraction"
    if claim_family == LOCAL_HOLDINGS:
        return "local_personal_data"
    if claim_family == RECENT_NEWS_OR_UPDATE:
        return "recent_news"
    if claim_family == TARIFF_REGULATORY:
        return "regulatory_source"
    if claim_family == BUYBACK_ACTIVITY:
        return "filing"
    return "required_evidence"


def _label_for_missing_category(category: str) -> str:
    if category == "market_data":
        return "market_data_missing"
    if category == "metric_extraction":
        return "metric_extraction_missing"
    if category == "recent_news":
        return "insufficient_for_recent_news"
    return f"{category}_missing"


def evaluate_chat_evidence_requirements(
    *,
    answer_text: str,
    sources: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate whether visible evidence satisfies detected claim families.

    The helper is intentionally metadata-only: it does not retrieve, rank,
    mutate, or remove sources.
    """
    metadata = metadata or {}
    claim_families = detect_claim_families(answer_text, metadata)
    evidence_categories = evidence_categories_for_sources(sources)
    labels = set(_string_array(metadata.get("evidence_labels")))
    source_status = str(metadata.get("source_coverage_status") or "").strip()
    if source_status:
        labels.add(source_status)
    if "degraded_runtime" in evidence_categories:
        labels.add("degraded_runtime")
    if "no_hit" in evidence_categories:
        labels.add("no_hit")

    requirement_rows: list[dict[str, Any]] = []
    missing_categories: set[str] = set()
    unsupported_families: set[str] = set()
    context_only_families: set[str] = set()

    for family in sorted(claim_families):
        required_any = CLAIM_REQUIREMENTS[family]
        satisfied = bool(evidence_categories.intersection(required_any))
        status = "satisfied" if satisfied else "missing_required_evidence"

        if family in {FILING_CONTEXT, BUYBACK_ACTIVITY, TARIFF_REGULATORY} and satisfied:
            if "claim_verified" not in labels and "claim_verified" not in evidence_categories:
                status = "context_only"
                context_only_families.add(family)

        if not satisfied:
            missing_category = _missing_category_for_claim_family(family)
            missing_categories.add(missing_category)
            unsupported_families.add(family)
            labels.add(_label_for_missing_category(missing_category))

        requirement_rows.append(
            {
                "claim_family": family,
                "required_any": list(required_any),
                "status": status,
                "satisfied": satisfied,
            }
        )

    if unsupported_families:
        labels.update({"missing_required_evidence", "unsupported_or_not_verified"})
    if _MISSING_CANONICAL_FINANCIAL_ROWS_RE.search(answer_text):
        missing_categories.add("metric_extraction")
        labels.update({"metric_extraction_missing", "missing_required_evidence"})
    if context_only_families:
        labels.add("context_only")

    return {
        "claim_families": sorted(claim_families),
        "evidence_categories": sorted(evidence_categories),
        "missing_evidence_categories": sorted(missing_categories),
        "unsupported_claim_families": sorted(unsupported_families),
        "context_only_claim_families": sorted(context_only_families),
        "evidence_requirement_labels": sorted(labels - set(_string_array(metadata.get("evidence_labels")))),
        "claim_evidence_requirements": requirement_rows,
    }


def enrich_chat_metadata_with_evidence_guard(
    metadata: Mapping[str, Any],
    *,
    answer_text: str,
    sources: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Attach deterministic evidence requirement metadata to chat responses."""
    enriched = dict(metadata)
    evaluation = evaluate_chat_evidence_requirements(
        answer_text=answer_text,
        sources=sources,
        metadata=enriched,
    )

    labels = set(_string_array(enriched.get("evidence_labels")))
    labels.update(evaluation["evidence_requirement_labels"])
    if labels:
        enriched["evidence_labels"] = sorted(labels)

    missing_categories = set(_string_array(enriched.get("missing_categories_after_recovery")))
    missing_categories.update(evaluation["missing_evidence_categories"])
    if missing_categories:
        enriched["missing_categories_after_recovery"] = sorted(missing_categories)

    if evaluation["claim_families"] or evaluation["evidence_requirement_labels"]:
        enriched["claim_evidence_families"] = evaluation["claim_families"]
        enriched["evidence_categories"] = evaluation["evidence_categories"]
        enriched["missing_evidence_categories"] = evaluation["missing_evidence_categories"]
        enriched["unsupported_claim_families"] = evaluation["unsupported_claim_families"]
        enriched["context_only_claim_families"] = evaluation["context_only_claim_families"]
        enriched["evidence_requirement_labels"] = evaluation["evidence_requirement_labels"]
        enriched["claim_evidence_requirements"] = evaluation["claim_evidence_requirements"]

    if evaluation["unsupported_claim_families"] or evaluation["missing_evidence_categories"]:
        current_status = str(enriched.get("source_coverage_status") or "").strip()
        if current_status not in {"degraded_runtime", "local_personal_data"}:
            enriched["source_coverage_status"] = "missing_required_evidence"
        enriched["sufficient_for_analysis"] = False

    return enriched


def requires_local_news_only_guard(user_message: str) -> bool:
    return bool(_LOCAL_NEWS_ONLY_REQUEST_RE.search(str(user_message or "")))


def _is_local_news_context_source(source: Mapping[str, Any]) -> bool:
    labels = _source_labels(source)
    source_id = _source_value(source, "source_id", "sourceId", "chunk_id").lower()
    kind = _source_value(source, "kind").lower()
    doc_type = _source_value(source, "doc_type", "docType", "source_type", "source").lower()
    if "external_web_context" in labels:
        return False
    return (
        "local_news_context" in labels
        or source_id.startswith("news:")
        or kind == "news"
        or "news" in doc_type
    )


def _is_claim_verified_local_news(source: Mapping[str, Any]) -> bool:
    labels = _source_labels(source)
    role_tokens = _source_role_tokens(source)
    if not _is_local_news_context_source(source):
        return False
    if "context_only" in labels:
        return False
    return bool(
        source.get("claim_verified") is True
        and (
            "claim_verified" in labels
            or RECENT_NEWS_EVENT in role_tokens
            or "news_event" in role_tokens
        )
    )


def _source_date(source: Mapping[str, Any]) -> str:
    for key in (
        "published_at",
        "publication_date",
        "date",
        "as_of",
        "timestamp",
        "created_at",
    ):
        value = str(source.get(key) or "").strip()
        if value:
            return value[:10]
    return "undated"


def _source_title(source: Mapping[str, Any]) -> str:
    for key in ("title", "source_name", "name", "source_id", "sourceId", "chunk_id"):
        value = str(source.get(key) or "").strip()
        if value:
            return value
    return "untitled local news context"


def _local_news_context_lines(sources: Sequence[Mapping[str, Any]]) -> list[str]:
    lines: list[str] = []
    for source in sources[:5]:
        lines.append(f"- {_source_date(source)} | {_source_title(source)}")
    return lines


def apply_local_news_only_guard(
    answer_text: str,
    sources: Sequence[Mapping[str, Any]],
    metadata: Mapping[str, Any],
    *,
    user_message: str,
) -> tuple[str, dict[str, Any]]:
    """Prevent non-news context from satisfying local-news-only requests."""
    text = str(answer_text or "")
    enriched = dict(metadata)
    if not requires_local_news_only_guard(user_message):
        return text, enriched

    local_news_sources = [
        source for source in sources if _is_local_news_context_source(source)
    ]
    verified_local_news_sources = [
        source for source in local_news_sources if _is_claim_verified_local_news(source)
    ]
    if verified_local_news_sources:
        enriched["local_news_context_count"] = len(local_news_sources)
        enriched["claim_verified_local_news_count"] = len(verified_local_news_sources)
        return text, enriched

    labels = set(_string_array(enriched.get("evidence_labels")))
    labels.update({"insufficient_for_recent_news", "missing_required_evidence"})
    if local_news_sources:
        labels.update({"local_news_context", "context_only"})
    else:
        labels.add("no_hit")
    enriched["evidence_labels"] = sorted(labels)

    missing_categories = set(_string_array(enriched.get("missing_evidence_categories")))
    missing_categories.update(_string_array(enriched.get("missing_categories_after_recovery")))
    missing_categories.add("recent_news")
    enriched["missing_evidence_categories"] = sorted(missing_categories)
    enriched["missing_categories_after_recovery"] = sorted(missing_categories)
    enriched["local_news_context_count"] = len(local_news_sources)
    enriched["claim_verified_local_news_count"] = 0
    enriched["claim_verified_source_count"] = 0
    enriched["sufficient_for_analysis"] = False
    enriched["local_news_only_guard"] = {
        "applied": True,
        "reason": LOCAL_NEWS_ONLY_GUARD_REASON,
        "local_news_context_count": len(local_news_sources),
        "claim_verified_local_news_count": 0,
    }

    current_status = str(enriched.get("source_coverage_status") or "").strip()
    if current_status not in {"degraded_runtime", "local_personal_data"}:
        enriched["source_coverage_status"] = "missing_required_evidence"

    if not local_news_sources:
        guarded_text = (
            "DATA_MISSING: no relevant local_news_context was returned for this "
            "local-news-only request. I will not use ASX filings, documents, "
            "price data, memory, or operational traces as local news."
        )
    else:
        source_lines = "\n".join(_local_news_context_lines(local_news_sources))
        guarded_text = (
            "DATA_MISSING: local_news_context was returned for this "
            "local-news-only request, but it is context-only and not "
            "claim-verified. I will not use ASX filings, documents, price data, "
            "memory, or operational traces as local news."
        )
        if source_lines:
            guarded_text = (
                f"{guarded_text}\n\n"
                "Context-only local news sources returned:\n"
                f"{source_lines}"
            )
    return guarded_text, enriched


def _metadata_gap_labels(metadata: Mapping[str, Any]) -> list[str]:
    labels = set(_string_array(metadata.get("evidence_labels")))
    labels.update(_string_array(metadata.get("evidence_requirement_labels")))
    source_status = str(metadata.get("source_coverage_status") or "").strip()
    if source_status:
        labels.add(source_status)

    missing_categories = set(_string_array(metadata.get("missing_evidence_categories")))
    missing_categories.update(_string_array(metadata.get("missing_categories_after_recovery")))
    if "market_data" in missing_categories:
        labels.add("market_data_missing")
    if "metric_extraction" in missing_categories:
        labels.add("metric_extraction_missing")
    if "recent_news" in missing_categories:
        labels.add("insufficient_for_recent_news")
    if missing_categories:
        labels.add("missing_required_evidence")

    return [label for label in VISIBLE_GAP_LABELS if label in labels]


def _qualify_context_memory_sections(answer_text: str, *, has_market_gap: bool) -> str:
    lines = answer_text.splitlines()
    qualified: list[str] = []
    section: str | None = None

    for raw_line in lines:
        stripped = raw_line.strip()
        lower = stripped.lower()
        if lower == "interpretation from company memory:":
            section = "company"
            qualified.append(
                "Context-only company memory (not verified market/technical evidence):"
                if has_market_gap
                else "Context-only company memory:"
            )
            continue
        if lower == "external context from market memory:":
            section = "market"
            qualified.append(
                "Context-only market memory (not verified market/technical evidence):"
                if has_market_gap
                else "Context-only market memory:"
            )
            continue
        if stripped and not stripped.startswith("-") and stripped.endswith(":"):
            section = None

        if section and stripped.startswith("-") and "context-only" not in lower:
            prefix, _, detail = raw_line.partition("-")
            label = (
                "context-only company memory note (not market-verified)"
                if section == "company" and has_market_gap
                else f"context-only {section} memory note"
            )
            qualified.append(f"{prefix}- {label}: {detail.strip()}")
            continue

        qualified.append(raw_line)

    return "\n".join(qualified)


def _qualify_financial_truth_event_wording(
    answer_text: str,
    *,
    has_recent_news_gap: bool,
) -> str:
    if not has_recent_news_gap:
        return answer_text
    replacements = {
        "Confirmed evidence already present:": (
            "Context available (not claim verification for missing evidence categories):"
        ),
        "- financial truth": (
            "- financial truth numeric context (numbers only; not event/news/announcement verification)"
        ),
        "- announcements/news context": (
            "- announcement/news context (context only unless separately claim-verified and recent)"
        ),
        "Available announcement/news context from financial truth:": (
            "Available filing/announcement context from financial truth "
            "(not event/news verification):"
        ),
        "Recent news context:": (
            "Local news/context snippets (not sufficient recent-event verification):"
        ),
        "Recovery outcome: sufficient evidence available; proceeding with analysis.": (
            "Recovery outcome: evidence remains incomplete for the gap categories; "
            "proceeding only with context."
        ),
        "this is a recent-event summary from price, filing, and news evidence": (
            "this is context-only from price, filing, and local-news snippets; "
            "recent-event evidence is insufficient"
        ),
        (
            "Answer below is context-only for those gap areas; do not treat price, "
            "technical, or memory-derived lines as verified unless a visible "
            "source explicitly supports them."
        ): (
            "Answer below is context-only for those gap areas; do not treat "
            "price, filing, local-news-context, numeric financial truth, "
            "technical, or memory-derived lines as verified unless a visible "
            "source explicitly supports them."
        ),
    }
    qualified = answer_text
    for old, new in replacements.items():
        qualified = qualified.replace(old, new)
    return qualified


def _apply_gap_block(text: str, gap_labels: list[str]) -> str:
    gap_lines = [f"- {_VISIBLE_GAP_COPY[label]}" for label in gap_labels]
    if "DATA_MISSING / evidence gaps:" in text[:1000]:
        lines = text.splitlines()
        header_index = next(
            (
                index
                for index, line in enumerate(lines)
                if line.strip() == "DATA_MISSING / evidence gaps:"
            ),
            -1,
        )
        if header_index < 0:
            return text
        missing_lines = [
            line
            for line in gap_lines
            if line.split(":", 1)[0].removeprefix("- ") not in text
        ]
        if not missing_lines:
            return text
        return "\n".join(
            [*lines[: header_index + 1], *missing_lines, *lines[header_index + 1 :]]
        )

    gap_block = "\n".join(
        [
            "DATA_MISSING / evidence gaps:",
            *gap_lines,
            "",
            "Answer below is context-only for those gap areas; do not treat "
            "price, filing, local-news-context, numeric financial truth, "
            "technical, or memory-derived lines as verified unless a visible "
            "source explicitly supports them.",
        ]
    )
    return f"{gap_block}\n\n{text}".strip()


def apply_visible_evidence_gap_labels(
    answer_text: str,
    metadata: Mapping[str, Any],
) -> str:
    """Make response-level evidence gaps visible in the answer text itself."""
    text = str(answer_text or "")
    gap_labels = _metadata_gap_labels(metadata)
    if not gap_labels:
        return text
    has_recent_news_gap = "insufficient_for_recent_news" in gap_labels

    qualified_text = _qualify_context_memory_sections(
        text,
        has_market_gap=(
            "market_data_missing" in gap_labels
            or "unsupported_or_not_verified" in gap_labels
        ),
    )
    qualified_text = _qualify_financial_truth_event_wording(
        qualified_text,
        has_recent_news_gap=has_recent_news_gap,
    )
    return _apply_gap_block(qualified_text, gap_labels)
