from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

MARKET_PRICE_OR_TECHNICAL_TREND = "market_price_or_technical_trend"
FINANCIAL_METRIC = "financial_metric"
FILING_CONTEXT = "filing_context"
BUYBACK_ACTIVITY = "buyback_activity"
TARIFF_REGULATORY = "tariff_regulatory"
LOCAL_HOLDINGS = "local_holdings"

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
    if source.get("claim_verified") is True or source.get("supports_claim") is True:
        labels.add("claim_verified")
    return labels


def detect_claim_families(answer_text: str, metadata: Mapping[str, Any] | None = None) -> set[str]:
    """Return broad claim families that need matching evidence classes."""
    text = str(answer_text or "")
    families: set[str] = set()
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

    metadata = metadata or {}
    canonical_intent = str(metadata.get("canonical_intent") or metadata.get("intent") or "").strip().lower()
    if canonical_intent == "holdings":
        families.add(LOCAL_HOLDINGS)
    return families


def evidence_categories_for_source(source: Mapping[str, Any]) -> set[str]:
    """Classify a visible source into the evidence categories it can satisfy."""
    labels = _source_labels(source)
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
    if "context_only" in labels:
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

    if "financial_truth" in labels or re.search(
        r"\b(?:financial_truth|financial statement|income statement|balance sheet|cash flow|"
        r"extracted metric|canonical financial|annual_report|half_year|quarterly)\b",
        haystack,
    ):
        categories.update({"extracted_metric", "financial_statement"})

    if kind in {"document", "rag"} or re.search(
        r"\b(?:asx_announcement|announcement|filing|annual report|appendix|notice)\b",
        haystack,
    ):
        categories.add("filing")
    if _BUYBACK_RE.search(haystack):
        categories.add("buyback_filing")
    if _TARIFF_REGULATORY_RE.search(haystack):
        categories.add("regulatory_source")
    if kind == "news" or "local_news_context" in labels or "news" in doc_type:
        categories.add("news")
    if "claim_verified" in labels:
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

    if evaluation["unsupported_claim_families"]:
        current_status = str(enriched.get("source_coverage_status") or "").strip()
        if current_status not in {"degraded_runtime", "local_personal_data"}:
            enriched["source_coverage_status"] = "missing_required_evidence"
        enriched["sufficient_for_analysis"] = False

    return enriched
