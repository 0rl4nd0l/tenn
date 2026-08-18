"""Immutable ASX document-type extraction contracts.

This module binds deterministic document classification to the existing
canonical metric authority.  A selected contract is routing metadata only: it
does not prove a metric, satisfy provenance, authorize persistence, or write
canonical financial data.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType

from app.services.asx_document_type_classifier import (
    AsxDocumentTypeClassification,
    classify_asx_document_type,
)
from app.services.financial_metric_contract import CANONICAL_METRIC_FIELDS


_ALL_CANONICAL_METRICS = tuple(CANONICAL_METRIC_FIELDS)
_CASHFLOW_METRICS = (
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
)
_BASE_REQUIRED_CONTEXT = ("document_type_anchor", "period_basis")
_BASE_FORBIDDEN_INFERENCES = (
    "classification_as_metric_evidence",
    "classification_as_provenance",
    "classification_as_persistence_authority",
)
_BASE_ABSTENTION_CONDITIONS = (
    "unknown_or_unsupported_document_type",
    "ambiguous_document_type",
    "missing_document_type_anchor",
    "missing_or_invalid_period_basis",
    "insufficient_classification_source_evidence",
)


@dataclass(frozen=True)
class AsxDocumentExtractionContract:
    """Declarative extraction allowance for one supported document type."""

    contract_id: str
    document_type: str
    allowed_canonical_metrics: tuple[str, ...]
    required_context: tuple[str, ...]
    permitted_period_bases: tuple[str, ...]
    required_document_type_anchors: tuple[str, ...]
    minimum_source_evidence: int
    forbidden_inferences: tuple[str, ...]
    abstention_conditions: tuple[str, ...]


@dataclass(frozen=True)
class ExtractionContractSelection:
    """Metadata-only result of selecting a document extraction contract."""

    document_type: str
    contract: AsxDocumentExtractionContract | None
    abstain: bool
    abstain_reasons: tuple[str, ...]
    canonical_write: bool = False
    metric_evidence_proven: bool = False
    persistence_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        contract = self.contract
        payload["contract_id"] = contract.contract_id if contract else None
        payload["allowed_canonical_metrics"] = (
            list(contract.allowed_canonical_metrics) if contract else []
        )
        payload.pop("contract", None)
        return payload


@dataclass(frozen=True)
class ContractRoutingDecision:
    """Fail-closed decision for applying a selected contract to routing."""

    allowed: bool
    abstain: bool
    reasons: tuple[str, ...]
    contract: AsxDocumentExtractionContract | None

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "abstain": self.abstain,
            "reasons": list(self.reasons),
            "contract_id": self.contract.contract_id if self.contract else None,
        }


def _contract(
    document_type: str,
    *,
    metrics: tuple[str, ...],
    periods: tuple[str, ...],
    document_type_anchors: tuple[str, ...],
    forbidden: tuple[str, ...] = (),
) -> AsxDocumentExtractionContract:
    canonical = set(CANONICAL_METRIC_FIELDS)
    if not set(metrics) <= canonical:
        raise ValueError(f"{document_type} widens canonical metric authority")
    return AsxDocumentExtractionContract(
        contract_id=f"asx_{document_type}_extraction_contract_v1",
        document_type=document_type,
        allowed_canonical_metrics=metrics,
        required_context=_BASE_REQUIRED_CONTEXT,
        permitted_period_bases=periods,
        required_document_type_anchors=document_type_anchors,
        minimum_source_evidence=1,
        forbidden_inferences=_BASE_FORBIDDEN_INFERENCES + forbidden,
        abstention_conditions=_BASE_ABSTENTION_CONDITIONS,
    )


DOCUMENT_EXTRACTION_CONTRACTS: Mapping[str, AsxDocumentExtractionContract] = (
    MappingProxyType(
        {
            "annual_report": _contract(
                "annual_report",
                metrics=_ALL_CANONICAL_METRICS,
                periods=("A",),
                document_type_anchors=(
                    "Annual Report",
                    "Directors' report",
                    "financial statements",
                ),
            ),
            "appendix_4e": _contract(
                "appendix_4e",
                metrics=_ALL_CANONICAL_METRICS,
                periods=("A",),
                document_type_anchors=("Appendix 4E", "Preliminary final report"),
            ),
            "half_year_report": _contract(
                "half_year_report",
                metrics=_ALL_CANONICAL_METRICS,
                periods=("H",),
                document_type_anchors=(
                    "Half-Year Report",
                    "Interim financial report",
                    "Condensed consolidated financial statements",
                ),
            ),
            "appendix_4d": _contract(
                "appendix_4d",
                metrics=_ALL_CANONICAL_METRICS,
                periods=("H",),
                document_type_anchors=("Appendix 4D", "Half year report"),
            ),
            "quarterly_report": _contract(
                "quarterly_report",
                metrics=_ALL_CANONICAL_METRICS,
                periods=("Q",),
                document_type_anchors=(
                    "Quarterly Report",
                    "Quarterly highlights",
                    "Quarterly financial summary",
                ),
            ),
            "appendix_4c": _contract(
                "appendix_4c",
                metrics=_CASHFLOW_METRICS,
                periods=("Q",),
                document_type_anchors=(
                    "Appendix 4C",
                    "Quarterly cash flow report",
                    "Rule 4.7B",
                    "operating cash flow lines",
                ),
                forbidden=("revenue", "ebit", "np_attributable", "net_debt"),
            ),
            "appendix_5b": _contract(
                "appendix_5b",
                metrics=_CASHFLOW_METRICS,
                periods=("Q",),
                document_type_anchors=(
                    "Appendix 5B",
                    "Mining exploration entity quarterly cash flow report",
                    "Rule 5.5",
                    "exploration expenditure",
                    "related-party payments",
                ),
                forbidden=("revenue", "ebit", "np_attributable", "net_debt"),
            ),
        }
    )
)


def classify_and_select_extraction_contract(
    source_text_surrogate: Mapping[str, object] | None,
) -> tuple[AsxDocumentTypeClassification, ExtractionContractSelection]:
    """Classify one source surrogate and select its metadata-only contract."""

    classification = classify_asx_document_type(source_text_surrogate)
    return classification, select_extraction_contract(classification)


def select_extraction_contract(
    classification: AsxDocumentTypeClassification | Mapping[str, object],
) -> ExtractionContractSelection:
    """Select a contract from deterministic classification metadata only."""

    if isinstance(classification, AsxDocumentTypeClassification):
        document_type = classification.document_type
        abstain = classification.abstain
        reasons = tuple(classification.abstain_reasons)
        positive_evidence = classification.positive_evidence
    elif isinstance(classification, Mapping):
        document_type = str(classification.get("document_type") or "")
        abstain = bool(classification.get("abstain", True))
        raw_reasons = classification.get("abstain_reasons")
        reasons = (
            tuple(str(reason) for reason in raw_reasons if isinstance(reason, str))
            if isinstance(raw_reasons, Collection)
            and not isinstance(raw_reasons, (str, bytes))
            else ()
        )
        raw_evidence = classification.get("positive_evidence")
        positive_evidence = (
            raw_evidence
            if isinstance(raw_evidence, Collection)
            and not isinstance(raw_evidence, (str, bytes))
            else ()
        )
    else:
        return _abstain_selection("", ("invalid_classification_metadata",))

    if abstain:
        return _abstain_selection(
            document_type,
            reasons or ("classification_abstained",),
        )

    contract = DOCUMENT_EXTRACTION_CONTRACTS.get(document_type)
    if contract is None:
        return _abstain_selection(
            document_type,
            ("unsupported_document_type",),
        )
    evidence_anchors = {
        str(item.get("anchor"))
        for item in positive_evidence
        if isinstance(item, Mapping) and item.get("anchor")
    }
    if not evidence_anchors.intersection(contract.required_document_type_anchors):
        return _abstain_selection(
            document_type,
            ("missing_document_type_anchor",),
        )
    if len(positive_evidence) < contract.minimum_source_evidence:
        return _abstain_selection(
            document_type,
            ("insufficient_classification_source_evidence",),
        )

    return ExtractionContractSelection(
        document_type=document_type,
        contract=contract,
        abstain=False,
        abstain_reasons=(),
    )


def evaluate_contract_routing(
    selection: ExtractionContractSelection,
    *,
    period_basis: str | None,
    available_context: Collection[str],
    source_evidence_count: int,
) -> ContractRoutingDecision:
    """Validate contract prerequisites before metric extraction is allowed."""

    if selection.abstain or selection.contract is None:
        return ContractRoutingDecision(
            allowed=False,
            abstain=True,
            reasons=selection.abstain_reasons or ("contract_not_selected",),
            contract=None,
        )

    contract = selection.contract
    reasons: list[str] = []
    if period_basis not in contract.permitted_period_bases:
        reasons.append("extraction_contract_period_basis_mismatch")
    missing_context = sorted(set(contract.required_context) - set(available_context))
    if missing_context:
        reasons.append(f"missing_required_context:{','.join(missing_context)}")
    if source_evidence_count < contract.minimum_source_evidence:
        reasons.append("insufficient_classification_source_evidence")

    return ContractRoutingDecision(
        allowed=not reasons,
        abstain=bool(reasons),
        reasons=tuple(reasons),
        contract=contract if not reasons else None,
    )


def _abstain_selection(
    document_type: str,
    reasons: tuple[str, ...],
) -> ExtractionContractSelection:
    return ExtractionContractSelection(
        document_type=document_type or "unknown_or_abstain",
        contract=None,
        abstain=True,
        abstain_reasons=reasons,
    )
