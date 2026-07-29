from dataclasses import FrozenInstanceError

import pytest

from app.services.asx_document_type_classifier import classify_asx_document_type
from app.services.asx_extraction_contracts import (
    DOCUMENT_EXTRACTION_CONTRACTS,
    classify_and_select_extraction_contract,
    evaluate_contract_routing,
    select_extraction_contract,
)
from app.services.financial_metric_contract import CANONICAL_METRIC_FIELDS


SUPPORTED_FINANCIAL_DOCUMENT_TYPES = {
    "annual_report",
    "appendix_4e",
    "half_year_report",
    "appendix_4d",
    "quarterly_report",
    "appendix_4c",
    "appendix_5b",
}


def _classification(
    title: str,
    *,
    headings: tuple[str, ...] = (),
    anchors: tuple[str, ...] = (),
):
    return classify_asx_document_type(
        {
            "first_page_title_text": title,
            "headings": headings,
            "relevant_line_anchors": anchors,
        }
    )


def test_registry_is_complete_immutable_and_bound_to_canonical_metric_authority() -> (
    None
):
    assert set(DOCUMENT_EXTRACTION_CONTRACTS) == SUPPORTED_FINANCIAL_DOCUMENT_TYPES

    canonical_fields = set(CANONICAL_METRIC_FIELDS)
    for document_type, contract in DOCUMENT_EXTRACTION_CONTRACTS.items():
        assert contract.document_type == document_type
        assert contract.allowed_canonical_metrics
        assert set(contract.allowed_canonical_metrics) <= canonical_fields
        assert contract.required_context
        assert contract.permitted_period_bases
        assert contract.required_document_type_anchors
        assert contract.minimum_source_evidence
        assert contract.forbidden_inferences
        assert contract.abstention_conditions

    with pytest.raises(TypeError):
        DOCUMENT_EXTRACTION_CONTRACTS["annual_report"] = (  # type: ignore[index]
            DOCUMENT_EXTRACTION_CONTRACTS["annual_report"]
        )
    with pytest.raises(FrozenInstanceError):
        DOCUMENT_EXTRACTION_CONTRACTS["annual_report"].document_type = "other"  # type: ignore[misc]


def test_cashflow_appendix_contracts_forbid_income_and_net_debt_inferences() -> None:
    forbidden_metrics = {"revenue", "ebit", "np_attributable", "net_debt"}

    for document_type in ("appendix_4c", "appendix_5b"):
        contract = DOCUMENT_EXTRACTION_CONTRACTS[document_type]
        assert forbidden_metrics.isdisjoint(contract.allowed_canonical_metrics)
        assert forbidden_metrics <= set(contract.forbidden_inferences)


def test_classification_selects_metadata_only_contract() -> None:
    classification = _classification(
        "Appendix 4C Quarterly cash flow report",
        anchors=("Rule 4.7B", "For the quarter ended 31 March 2026"),
    )
    selection = select_extraction_contract(classification)

    assert selection.abstain is False
    assert selection.contract is DOCUMENT_EXTRACTION_CONTRACTS["appendix_4c"]
    assert selection.canonical_write is False
    assert selection.metric_evidence_proven is False
    assert selection.persistence_authorized is False


def test_unknown_or_ambiguous_classification_abstains_without_contract() -> None:
    for classification in (
        _classification("General ASX announcement"),
        _classification(
            "Annual Report and Quarterly Report",
            headings=("Directors' report", "Financial statements"),
            anchors=(
                "For the year ended 30 June 2025",
                "For the quarter ended 31 March 2025",
            ),
        ),
    ):
        selection = select_extraction_contract(classification)
        assert selection.abstain is True
        assert selection.contract is None
        assert selection.abstain_reasons


@pytest.mark.parametrize(
    ("source_text", "document_type"),
    (
        ("For the year ended 30 June 2025", "appendix_4e"),
        ("For the half-year ended 31 December 2025", "appendix_4d"),
        ("For the quarter ended 31 March 2026", "quarterly_report"),
    ),
)
def test_period_evidence_alone_cannot_select_an_extraction_contract(
    source_text: str,
    document_type: str,
) -> None:
    classification, selection = classify_and_select_extraction_contract(
        {"first_page_title_text": source_text}
    )

    assert classification.document_type == document_type
    assert classification.confidence_band == "medium"
    assert selection.abstain is True
    assert selection.contract is None
    assert selection.abstain_reasons == ("missing_document_type_anchor",)


def test_routing_fails_closed_on_period_context_or_source_evidence_mismatch() -> None:
    selection = select_extraction_contract(
        _classification(
            "Half-Year Report",
            headings=("Interim financial report",),
            anchors=("For the half-year ended 31 December 2025",),
        )
    )

    assert (
        evaluate_contract_routing(
            selection,
            period_basis="H",
            available_context={"document_type_anchor", "period_basis"},
            source_evidence_count=2,
        ).allowed
        is True
    )

    for decision in (
        evaluate_contract_routing(
            selection,
            period_basis="A",
            available_context={"document_type_anchor", "period_basis"},
            source_evidence_count=2,
        ),
        evaluate_contract_routing(
            selection,
            period_basis="H",
            available_context={"document_type_anchor"},
            source_evidence_count=2,
        ),
        evaluate_contract_routing(
            selection,
            period_basis="H",
            available_context={"document_type_anchor", "period_basis"},
            source_evidence_count=0,
        ),
    ):
        assert decision.allowed is False
        assert decision.abstain is True
        assert decision.reasons
