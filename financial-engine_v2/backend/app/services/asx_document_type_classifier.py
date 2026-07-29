"""Pure ASX document-type classifier for synthetic text-surrogate inputs.

This module is intentionally standalone. It classifies document type metadata
only and never routes extraction, infers metrics, or authorizes canonical
writes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any


SUPPORTED_DOCUMENT_TYPES = {
    "annual_report",
    "half_year_report",
    "appendix_4c",
    "appendix_4d",
    "appendix_4e",
    "appendix_5b",
    "quarterly_report",
    "other_asx_announcement",
    "unknown_or_abstain",
}

CASHFLOW_DOCUMENT_TYPES = {"appendix_4c", "appendix_5b"}
APPENDIX_DOCUMENT_TYPES = {
    "appendix_4c": "Appendix 4C",
    "appendix_4d": "Appendix 4D",
    "appendix_4e": "Appendix 4E",
    "appendix_5b": "Appendix 5B",
}

_SUPPORTED_CONTEXT_KEYS = {
    "first_page_title_text",
    "asx_announcement_title",
    "headings",
    "table_captions",
    "relevant_line_anchors",
    "footer_form_labels",
}
_DOCUMENT_PAGES_KEY = "document_pages"

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_SPACE_RE = re.compile(r"\s+")
_UNSUPPORTED_REVIEW_RE = re.compile(r"\b(?:eps|nta|dividend|dividends)\b")


@dataclass(frozen=True)
class AnchorRule:
    anchor: str
    pattern: str
    weight: int = 1
    required_for_high: bool = False


@dataclass(frozen=True)
class EvidenceItem:
    document_type: str
    anchor: str
    matched_text: str
    page: int | None = None


@dataclass(frozen=True)
class _TextSource:
    text: str
    page: int | None


@dataclass(frozen=True)
class AsxDocumentTypeClassification:
    document_type: str
    confidence_band: str
    expected_abstain: bool
    abstain: bool
    canonical_write: bool
    positive_evidence: list[dict[str, Any]] = field(default_factory=list)
    negative_evidence: list[dict[str, Any]] = field(default_factory=list)
    abstain_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _DocumentTypeRule:
    document_type: str
    anchors: tuple[AnchorRule, ...]
    high_score: int
    medium_score: int = 1


_RULES: tuple[_DocumentTypeRule, ...] = (
    _DocumentTypeRule(
        document_type="appendix_4c",
        anchors=(
            AnchorRule("Appendix 4C", r"\bappendix\s+4c\b", weight=4, required_for_high=True),
            AnchorRule("Quarterly cash flow report", r"\bquarterly\s+cash\s+flow\s+report\b", weight=2),
            AnchorRule("Rule 4.7B", r"\brule\s+4\s*7b\b", weight=2),
            AnchorRule("operating cash flow lines", r"\bnet\s+cash\s+from\s*/?\s*\(?used\s+in\)?\s+operating\s+activities\b"),
        ),
        high_score=6,
    ),
    _DocumentTypeRule(
        document_type="appendix_5b",
        anchors=(
            AnchorRule("Appendix 5B", r"\bappendix\s+5b\b", weight=4, required_for_high=True),
            AnchorRule(
                "Mining exploration entity quarterly cash flow report",
                r"\bmining\s+exploration\s+entity\s+quarterly\s+cash\s+flow\s+report\b",
                weight=2,
            ),
            AnchorRule("Rule 5.5", r"\brule\s+5\s*5\b", weight=2),
            AnchorRule("exploration expenditure", r"\bexploration\s+and\s+evaluation\s+expenditure\b"),
            AnchorRule("related-party payments", r"\bpayments\s+to\s+related\s+parties\b"),
        ),
        high_score=6,
    ),
    _DocumentTypeRule(
        document_type="appendix_4d",
        anchors=(
            AnchorRule("Appendix 4D", r"\bappendix\s+4d\b", weight=4, required_for_high=True),
            AnchorRule("Half year report", r"\bhalf[\s-]+year\s+report\b", weight=2),
            AnchorRule("Results for announcement to the market", r"\bresults\s+for\s+announcement\s+to\s+the\s+market\b", weight=2),
            AnchorRule("half-year period", r"\bhalf[\s-]+year\s+ended\b"),
        ),
        high_score=6,
    ),
    _DocumentTypeRule(
        document_type="appendix_4e",
        anchors=(
            AnchorRule("Appendix 4E", r"\bappendix\s+4e\b", weight=4, required_for_high=True),
            AnchorRule("Preliminary final report", r"\bpreliminary\s+final\s+report\b", weight=2),
            AnchorRule("Results for announcement to the market", r"\bresults\s+for\s+announcement\s+to\s+the\s+market\b", weight=2),
            AnchorRule("year-ended period", r"\byear\s+ended\b"),
        ),
        high_score=6,
    ),
    _DocumentTypeRule(
        document_type="annual_report",
        anchors=(
            AnchorRule("Annual Report", r"\bannual\s+report\b", weight=3, required_for_high=True),
            AnchorRule("Directors' report", r"\bdirectors'?[\s]+report\b", weight=2),
            AnchorRule("financial statements", r"\bfinancial\s+statements\b", weight=2),
            AnchorRule("year-ended period", r"\byear\s+ended\b"),
        ),
        high_score=5,
    ),
    _DocumentTypeRule(
        document_type="half_year_report",
        anchors=(
            AnchorRule("Half-Year Report", r"\bhalf[\s-]+year\s+report\b", weight=3, required_for_high=True),
            AnchorRule("Interim financial report", r"\binterim\s+financial\s+report\b", weight=2),
            AnchorRule("Condensed consolidated financial statements", r"\bcondensed\s+consolidated\s+financial\s+statements\b", weight=2),
            AnchorRule("half-year period", r"\bhalf[\s-]+year\s+ended\b"),
        ),
        high_score=5,
    ),
    _DocumentTypeRule(
        document_type="quarterly_report",
        anchors=(
            AnchorRule(
                "Quarterly Report",
                r"\bquarterly\s+(?:activities\s+)?report\b",
                weight=3,
                required_for_high=True,
            ),
            AnchorRule(
                "quarter-ended period",
                r"\b(?:quarter|three\s+months)\s+ended\b",
                weight=2,
            ),
            AnchorRule("Quarterly highlights", r"\bquarterly\s+highlights\b"),
            AnchorRule(
                "Quarterly financial summary",
                r"\bquarterly\s+financial\s+summary\b",
            ),
        ),
        high_score=5,
    ),
    _DocumentTypeRule(
        document_type="other_asx_announcement",
        anchors=(
            AnchorRule("Investor Presentation", r"\binvestor\s+presentation\b", weight=2),
            AnchorRule("strategy update", r"\bstrategy\s+update\b", weight=2),
            AnchorRule("operational update", r"\boperational\s+update\b"),
            AnchorRule("capital raising", r"\bcapital\s+raising\b"),
            AnchorRule("trading update", r"\btrading\s+update\b"),
            AnchorRule("released to ASX", r"\breleased\s+to\s+asx\b"),
        ),
        high_score=6,
        medium_score=2,
    ),
)


def classify_asx_document_type(source_text_surrogate: Mapping[str, Any] | None) -> AsxDocumentTypeClassification:
    """Classify fixture-shaped ASX text-surrogate metadata.

    The return value is metadata-only. `canonical_write` is always false.
    """

    sources = _collect_text_sources(source_text_surrogate)
    text = _joined_text([source.text for source in sources])
    warnings = _warnings_for_text(text)

    if not text:
        return _abstain(
            reasons=["empty or unsupported source_text_surrogate"],
            warnings=warnings,
        )

    evidence_by_type = {
        rule.document_type: _match_rule(rule, sources)
        for rule in _RULES
    }
    form_label_evidence = _appendix_form_label_evidence(evidence_by_type)
    if len(form_label_evidence) > 1:
        return _abstain(
            reasons=[
                "conflicting supported Appendix form labels",
                "abstained instead of choosing between high-confidence anchors",
            ],
            negative_evidence=form_label_evidence,
            warnings=warnings,
        )

    half_year_bundle_evidence = _half_year_bundle_precedence(evidence_by_type)
    if half_year_bundle_evidence:
        return _result(
            document_type="half_year_report",
            confidence_band=_confidence_for(
                _rule_for("half_year_report"),
                half_year_bundle_evidence,
            ),
            positive_evidence=half_year_bundle_evidence,
            warnings=warnings,
        )

    half_year_bundle_conflict = _half_year_bundle_conflict(evidence_by_type)
    if half_year_bundle_conflict:
        return _abstain(
            reasons=[
                "conflicting Appendix 4D and half-year report bundle anchors",
                "whole-document precedence requires later-page report evidence",
            ],
            negative_evidence=half_year_bundle_conflict,
            warnings=warnings,
        )

    best_type, best_score = _best_scoring_type(evidence_by_type)
    if best_type is None or best_score <= 0:
        return _abstain(
            reasons=["low signal surrogate text", "no supported report or Appendix form anchor"],
            warnings=warnings,
        )

    if form_label_evidence:
        appendix_type = form_label_evidence[0].document_type
        positive = evidence_by_type[appendix_type]
        rule = _rule_for(appendix_type)
        return _result(
            document_type=appendix_type,
            confidence_band=_confidence_for(rule, positive),
            positive_evidence=positive,
            warnings=warnings,
        )

    non_appendix_conflicts = _high_non_appendix_conflicts(evidence_by_type)
    if len(non_appendix_conflicts) > 1:
        return _abstain(
            reasons=[
                "conflicting non-Appendix report anchors",
                "abstained instead of guessing document type",
            ],
            negative_evidence=non_appendix_conflicts,
            warnings=warnings,
        )

    if best_type == "other_asx_announcement" and _supported_report_or_appendix_anchor_exists(evidence_by_type):
        return _abstain(
            reasons=[
                "generic ASX announcement evidence conflicts with supported report or Appendix anchors",
                "abstained instead of guessing document type",
            ],
            negative_evidence=evidence_by_type[best_type],
            warnings=warnings,
        )

    rule = _rule_for(best_type)
    positive = evidence_by_type[best_type]
    confidence = _confidence_for(rule, positive)
    if confidence == "low":
        return _abstain(
            reasons=["low signal surrogate text", "no supported report or Appendix form anchor"],
            negative_evidence=positive,
            warnings=warnings,
        )

    return _result(
        document_type=best_type,
        confidence_band=confidence,
        positive_evidence=positive,
        warnings=warnings,
    )


def classify(source_text_surrogate: Mapping[str, Any] | None) -> AsxDocumentTypeClassification:
    """Short alias for callers that want a generic classifier name."""

    return classify_asx_document_type(source_text_surrogate)


def _collect_text_sources(
    source_text_surrogate: Mapping[str, Any] | None,
) -> list[_TextSource]:
    if not isinstance(source_text_surrogate, Mapping):
        return []

    context_text = _joined_text(
        [
            value
            for key in sorted(_SUPPORTED_CONTEXT_KEYS)
            for value in _walk_strings(source_text_surrogate.get(key))
        ]
    )
    sources = (
        [_TextSource(text=context_text, page=None)]
        if context_text
        else []
    )
    pages = source_text_surrogate.get(_DOCUMENT_PAGES_KEY)
    if isinstance(pages, Sequence) and not isinstance(pages, (str, bytes, bytearray)):
        page_values: dict[int | None, list[str]] = {}
        for item in pages:
            if not isinstance(item, Mapping):
                continue
            page = item.get("page")
            page_number = page if isinstance(page, int) and page > 0 else None
            page_values.setdefault(page_number, []).extend(
                _walk_strings(item.get("text"))
            )
        for page_number, values in page_values.items():
            page_text = _joined_text(values)
            if page_text:
                sources.append(_TextSource(text=page_text, page=page_number))
    return sources


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        values: list[str] = []
        for item in value.values():
            values.extend(_walk_strings(item))
        return values
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values = []
        for item in value:
            values.extend(_walk_strings(item))
        return values
    return []


def _joined_text(values: list[str]) -> str:
    normalized_values = [_normalize(value) for value in values if value.strip()]
    return " ".join(value for value in normalized_values if value)


def _normalize(value: str) -> str:
    lowered = value.lower().replace("&", " and ")
    return _SPACE_RE.sub(" ", _NORMALIZE_RE.sub(" ", lowered)).strip()


def _match_rule(
    rule: _DocumentTypeRule,
    sources: Sequence[_TextSource],
) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    for anchor in rule.anchors:
        matching_source: _TextSource | None = None
        for source in sources:
            if re.search(anchor.pattern, _normalize(source.text)):
                matching_source = source
                if source.page is not None:
                    break
        if matching_source is not None:
            evidence.append(
                EvidenceItem(
                    document_type=rule.document_type,
                    anchor=anchor.anchor,
                    matched_text=anchor.anchor,
                    page=matching_source.page,
                )
            )
    return evidence


def _appendix_form_label_evidence(evidence_by_type: Mapping[str, list[EvidenceItem]]) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    for document_type, label in APPENDIX_DOCUMENT_TYPES.items():
        for item in evidence_by_type.get(document_type, []):
            if item.anchor == label:
                evidence.append(item)
                break
    return evidence


def _half_year_bundle_precedence(
    evidence_by_type: Mapping[str, list[EvidenceItem]],
) -> list[EvidenceItem]:
    appendix_label = next(
        (
            item
            for item in evidence_by_type.get("appendix_4d", [])
            if item.anchor == "Appendix 4D" and item.page is not None
        ),
        None,
    )
    half_year_evidence = evidence_by_type.get("half_year_report", [])
    substantive_pages = [
        item.page
        for item in half_year_evidence
        if item.anchor
        in {
            "Interim financial report",
            "Condensed consolidated financial statements",
        }
        and item.page is not None
    ]
    if (
        appendix_label is None
        or not substantive_pages
        or min(substantive_pages) <= appendix_label.page
        or _confidence_for(_rule_for("half_year_report"), half_year_evidence) != "high"
    ):
        return []
    return half_year_evidence


def _half_year_bundle_conflict(
    evidence_by_type: Mapping[str, list[EvidenceItem]],
) -> list[EvidenceItem]:
    appendix_evidence = evidence_by_type.get("appendix_4d", [])
    appendix_label = next(
        (
            item
            for item in appendix_evidence
            if item.anchor == "Appendix 4D" and item.page is not None
        ),
        None,
    )
    half_year_evidence = evidence_by_type.get("half_year_report", [])
    has_substantive_report_evidence = any(
        item.anchor
        in {
            "Interim financial report",
            "Condensed consolidated financial statements",
        }
        and item.page is not None
        for item in half_year_evidence
    )
    if (
        appendix_label is None
        or not has_substantive_report_evidence
        or _confidence_for(_rule_for("half_year_report"), half_year_evidence) != "high"
    ):
        return []
    return appendix_evidence + half_year_evidence


def _best_scoring_type(evidence_by_type: Mapping[str, list[EvidenceItem]]) -> tuple[str | None, int]:
    best_type: str | None = None
    best_score = 0
    for rule in _RULES:
        score = _score(rule, evidence_by_type.get(rule.document_type, []))
        if score > best_score:
            best_type = rule.document_type
            best_score = score
    return best_type, best_score


def _score(rule: _DocumentTypeRule, evidence: list[EvidenceItem]) -> int:
    weights = {anchor.anchor: anchor.weight for anchor in rule.anchors}
    return sum(weights.get(item.anchor, 0) for item in evidence)


def _confidence_for(rule: _DocumentTypeRule, evidence: list[EvidenceItem]) -> str:
    if not evidence:
        return "abstain"

    score = _score(rule, evidence)
    matched = {item.anchor for item in evidence}
    high_required = [anchor.anchor for anchor in rule.anchors if anchor.required_for_high]
    required_ok = not high_required or any(anchor in matched for anchor in high_required)
    if required_ok and score >= rule.high_score:
        return "high"
    if score >= rule.medium_score:
        return "medium"
    return "low"


def _rule_for(document_type: str) -> _DocumentTypeRule:
    for rule in _RULES:
        if rule.document_type == document_type:
            return rule
    raise ValueError(f"unsupported document type rule: {document_type}")


def _high_non_appendix_conflicts(evidence_by_type: Mapping[str, list[EvidenceItem]]) -> list[EvidenceItem]:
    high_type_evidence: list[list[EvidenceItem]] = []
    high_types = 0
    for document_type in ("annual_report", "half_year_report", "quarterly_report"):
        rule = _rule_for(document_type)
        evidence = evidence_by_type.get(document_type, [])
        if _confidence_for(rule, evidence) == "high":
            high_types += 1
            high_type_evidence.append(evidence)
    if high_types <= 1:
        return []

    conflicts: list[EvidenceItem] = []
    for evidence in high_type_evidence:
        conflicts.extend(evidence)
    return conflicts


def _supported_report_or_appendix_anchor_exists(evidence_by_type: Mapping[str, list[EvidenceItem]]) -> bool:
    for document_type, evidence in evidence_by_type.items():
        if document_type == "other_asx_announcement":
            continue
        if evidence:
            return True
    return False


def _warnings_for_text(text: str) -> list[str]:
    warnings = [
        "document type classification is metadata only",
        "canonical_write is always false",
        "document type must not infer revenue, NPAT, net debt, or other financial metrics",
    ]
    if "appendix 4c" in text or "appendix 5b" in text:
        warnings.append(
            "cash-flow Appendix form type does not authorize income-statement metric inference"
        )
    if _UNSUPPORTED_REVIEW_RE.search(text):
        warnings.append(
            "EPS, NTA, and dividends are review-only unsupported context and are not canonical"
        )
    return warnings


def _result(
    *,
    document_type: str,
    confidence_band: str,
    positive_evidence: list[EvidenceItem],
    warnings: list[str],
) -> AsxDocumentTypeClassification:
    return AsxDocumentTypeClassification(
        document_type=document_type,
        confidence_band=confidence_band,
        expected_abstain=False,
        abstain=False,
        canonical_write=False,
        positive_evidence=[asdict(item) for item in positive_evidence],
        negative_evidence=[],
        abstain_reasons=[],
        warnings=warnings,
    )


def _abstain(
    *,
    reasons: list[str],
    warnings: list[str],
    negative_evidence: list[EvidenceItem] | None = None,
) -> AsxDocumentTypeClassification:
    return AsxDocumentTypeClassification(
        document_type="unknown_or_abstain",
        confidence_band="abstain",
        expected_abstain=True,
        abstain=True,
        canonical_write=False,
        positive_evidence=[],
        negative_evidence=[asdict(item) for item in negative_evidence or []],
        abstain_reasons=reasons,
        warnings=warnings,
    )
