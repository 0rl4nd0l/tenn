from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.base import EvidenceItem
from app.services.provenance import (
    ProvenanceRecord,
    from_extraction_payload,
    from_extraction_provenance,
    from_orchestrator_evidence,
    from_report_evidence_bundle_item,
    from_report_evidence_item,
    validate_provenance_collection,
    validate_provenance_record,
)


def test_from_extraction_provenance_normalizes_precise_table_reference() -> None:
    record = from_extraction_provenance(
        "revenue",
        "income_statement:page_7:Revenue from contracts with customers",
        source_document_id="123e4567-e89b-12d3-a456-426614174000",
        period_ref="2025-12-31:A",
        confidence=0.84,
    )

    assert record.source_type == "financial_statement"
    assert record.source_document_id == "123e4567-e89b-12d3-a456-426614174000"
    assert record.source_label == "income_statement"
    assert record.location_ref == "page_7"
    assert record.evidence_text == "Revenue from contracts with customers"
    assert record.provenance_status == "precise"
    assert record.confidence == 0.84


def test_from_extraction_provenance_marks_derived_metric() -> None:
    record = from_extraction_provenance(
        "net_debt",
        "derived:balance_sheet:total_debt(800000000)-cash_end(200000000)",
        source_document_id="123e4567-e89b-12d3-a456-426614174000",
        period_ref="2025-12-31:A",
    )

    assert record.provenance_status == "derived"
    assert record.source_label == "balance_sheet"
    assert record.parent_reference_ids == ("total_debt", "cash_end")
    validation = validate_provenance_record(record)
    issue_codes = {issue["code"] for issue in validation["issues"]}
    assert "derived_evidence" in issue_codes


def test_from_extraction_provenance_marks_prose_note_as_low_traceability() -> None:
    record = from_extraction_provenance(
        "shares_outstanding",
        "prose_note:page_13:1,924,937,480 ordinary shares on issue",
        source_document_id="123e4567-e89b-12d3-a456-426614174000",
        period_ref="2025-12-31:A",
    )

    assert record.location_ref == "page_13"
    assert record.provenance_status == "low_traceability"
    validation = validate_provenance_record(record)
    issue_codes = {issue["code"] for issue in validation["issues"]}
    assert "low_traceability" in issue_codes


def test_from_extraction_provenance_flags_placeholder_strings_as_synthetic() -> None:
    record = from_extraction_provenance(
        "revenue",
        "placeholder provenance not_configured for this fixture",
        source_document_id="123e4567-e89b-12d3-a456-426614174000",
        period_ref="2025-12-31:A",
    )

    assert record.provenance_status == "synthetic"
    validation = validate_provenance_record(record)
    issue_codes = {issue["code"] for issue in validation["issues"]}
    assert "synthetic_evidence" in issue_codes


def test_from_extraction_payload_normalizes_metric_collection() -> None:
    payload = {
        "period_end": "2025-12-31",
        "period_type": "A",
        "confidence_metrics": 0.72,
        "provenance": {
            "revenue": "income_statement:page_7:Revenue from contracts with customers",
            "net_debt": "derived:balance_sheet:total_debt(800000000)-cash_end(200000000)",
        },
    }

    records = from_extraction_payload(
        payload,
        source_document_id="123e4567-e89b-12d3-a456-426614174000",
    )

    assert len(records) == 2
    assert {record.period_ref for record in records} == {"2025-12-31:A"}
    assert {record.provenance_status for record in records} == {"precise", "derived"}


def test_from_orchestrator_evidence_handles_financial_truth_payload() -> None:
    record = from_orchestrator_evidence(
        "financial_truth",
        {
            "status": "ok",
            "ticker": "BHP",
            "items": [
                {
                    "period_end": "2025-12-31",
                    "period_type": "A",
                    "source_document_id": "123e4567-e89b-12d3-a456-426614174000",
                    "confidence_metrics": 0.66,
                }
            ],
            "latest_financial_snapshot": {
                "ticker": "BHP",
                "period_end": "2025-12-31",
                "period_type": "A",
                "source_document_id": "123e4567-e89b-12d3-a456-426614174000",
            },
        },
    )

    assert record.source_type == "financial_statement"
    assert record.source_label == "financial_truth"
    assert record.source_document_id == "123e4567-e89b-12d3-a456-426614174000"
    assert record.period_ref == "2025-12-31:A"
    assert record.provenance_status == "partial"


def test_from_orchestrator_evidence_degrades_gracefully_for_missing_fields() -> None:
    record = from_orchestrator_evidence(
        "company_memory",
        {"status": "not_configured", "items": []},
    )

    assert record.source_type == "company_memory"
    assert record.provenance_status == "synthetic"
    validation = validate_provenance_record(record)
    issue_codes = {issue["code"] for issue in validation["issues"]}
    assert "synthetic_evidence" in issue_codes


def test_from_report_evidence_item_normalizes_existing_evidence_item() -> None:
    item = EvidenceItem(
        evidence_id="sentiment_BHP_most_positive",
        source_type="news",
        content="Positive sentiment from commentary and filings.",
        source_id="news:afr",
        confidence=0.61,
    )

    record = from_report_evidence_item(item)

    assert record.source_type == "news"
    assert record.source_label == "news:afr"
    assert record.evidence_text == "Positive sentiment from commentary and filings."
    assert record.provenance_status == "partial"


def test_from_report_evidence_bundle_item_flags_placeholder_evidence() -> None:
    record = from_report_evidence_bundle_item(
        {
            "evidence_id": "news_placeholder",
            "source_type": "news",
            "source_id": "BHP_news",
            "confidence": 0.5,
            "content": "News context placeholder (no live news feed in this run).",
        }
    )

    assert record.provenance_status == "synthetic"
    validation = validate_provenance_record(record)
    issue_codes = {issue["code"] for issue in validation["issues"]}
    assert "synthetic_evidence" in issue_codes


def test_validator_reports_missing_source_identity_and_period_metadata() -> None:
    record = ProvenanceRecord(
        source_type="financial_statement",
        provenance_status="precise",
        evidence_summary="Direct financial statement evidence.",
    )

    validation = validate_provenance_record(record)

    issue_codes = {issue["code"] for issue in validation["issues"]}
    assert validation["ok"] is False
    assert "missing_source_identity" not in issue_codes
    assert "missing_location_ref" in issue_codes
    assert "missing_period_ref" in issue_codes


def test_validator_reports_missing_source_identity_for_empty_record() -> None:
    record = ProvenanceRecord()

    validation = validate_provenance_record(record)

    issue_codes = {issue["code"] for issue in validation["issues"]}
    assert validation["ok"] is False
    assert "missing_source_identity" in issue_codes
    assert "empty_evidence_payload" in issue_codes


def test_validate_provenance_collection_returns_structured_issue_summary() -> None:
    records = [
        from_extraction_provenance(
            "revenue",
            "income_statement:page_7:Revenue from contracts with customers",
            source_document_id="123e4567-e89b-12d3-a456-426614174000",
            period_ref="2025-12-31:A",
        ),
        from_report_evidence_bundle_item(
            {
                "evidence_id": "news_placeholder",
                "source_type": "news",
                "source_id": "BHP_news",
                "confidence": 0.5,
                "content": "News context placeholder (no live news feed in this run).",
            }
        ),
    ]

    result = validate_provenance_collection(records)

    assert result["record_count"] == 2
    assert result["warning_count"] >= 1
    assert any(issue["record_index"] == 1 for issue in result["issues"])
