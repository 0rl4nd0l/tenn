from __future__ import annotations

from unittest.mock import patch


def _good_payload(period_type="H", scale="thousands", currency="AUD", confidence=0.85):
    return {
        "period_end": "2024-12-31",
        "period_type": period_type,
        "scale": scale,
        "currency": currency,
        "metrics": {
            "revenue": 500_000_000,
            "ebit": 80_000_000,
            "np_attributable": 55_000_000,
            "operating_cf": 90_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "capex": None,
            "cash_end": None,
            "net_debt": None,
            "shares_outstanding": None,
        },
        "confidence_metrics": confidence,
    }


def test_validate_gate_blocks_ebitda_persisted_as_ebit():
    """EBITDA row evidence must not populate canonical EBIT."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(scale="millions")
    payload["metrics"]["ebit"] = 6_900_000
    payload["row_refs"] = {
        "revenue": "1H revenue of $44.1 million",
        "ebit": "1H EBITDA of $6.9 million",
        "np_attributable": "NPAT $4.2 million",
    }

    status, error = _validate_gate(payload)
    assert status == "failed"
    assert error == "validation_gate:metric_label_mismatch:ebit:ebitda"


def test_validate_gate_blocks_explicit_source_unit_value_mismatch():
    """A $44.1 million row must not persist as $44.1 billion."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(scale="millions")
    payload["metrics"]["revenue"] = 44_100_000_000
    payload["metrics"]["ebit"] = 6_900_000
    payload["metrics"]["np_attributable"] = 4_200_000
    payload["row_refs"] = {
        "revenue": "1H revenue of $44.1 million up $6.5m",
        "ebit": "EBIT $6.9 million",
        "np_attributable": "NPAT $4.2 million",
    }

    status, error = _validate_gate(payload)
    assert status == "failed"
    assert error == (
        "validation_gate:source_unit_value_mismatch:"
        "revenue:actual=4.41e+10:source_unit=4.41e+07"
    )


def test_validate_gate_accepts_explicit_source_unit_value_match():
    """Valid values matching explicit million evidence must not be weakened."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(scale="millions")
    payload["metrics"]["revenue"] = 44_100_000
    payload["metrics"]["ebit"] = 6_900_000
    payload["metrics"]["np_attributable"] = 4_200_000
    payload["row_refs"] = {
        "revenue": "1H revenue of $44.1 million up $6.5m",
        "ebit": "EBIT $6.9 million",
        "np_attributable": "NPAT $4.2 million",
    }

    status, error = _validate_gate(payload)
    assert status in ("ok", "ok_low_confidence")
    assert error is None


def test_validate_gate_blocks_source_period_mismatch():
    """Annual source evidence must not persist as half-year payload period_type."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="H", scale="units")
    payload["source_period_type"] = "A"
    payload["source_period_evidence"] = {
        "period_type": "A",
        "reason": "year_ended_source_phrase",
    }

    status, error = _validate_gate(payload)
    assert status == "failed"
    assert error == (
        "validation_gate:period_source_mismatch:"
        "payload=H:source=A:year_ended_source_phrase"
    )


def test_validate_gate_accepts_matching_source_period():
    """Matching source-period evidence must not block a valid half-year payload."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="H", scale="thousands")
    payload["source_period_type"] = "H"
    payload["source_period_evidence"] = {
        "period_type": "H",
        "reason": "six_months_ended_source_phrase",
    }

    status, error = _validate_gate(payload)
    assert status in ("ok", "ok_low_confidence")
    assert error is None


def test_validate_gate_accepts_source_explicit_idr_trillion_native_values():
    """IDR trillion native values are low-confidence non-AUD, not AUD cap failures."""
    from app.services.multipass_extraction import _validate_gate, _validate_scale

    payload = _good_payload(period_type="A", scale="trillions", currency="IDR")
    payload["metrics"]["revenue"] = 12_500_000_000_000
    payload["metrics"]["ebit"] = 2_400_000_000_000
    payload["metrics"]["np_attributable"] = 1_100_000_000_000
    payload["row_refs"] = {
        "revenue": "Revenue Rp 12.5 trillion",
        "ebit": "Operating profit Rp 2.4 trillion",
        "np_attributable": "NPAT Rp 1.1 trillion",
    }
    payload["scale_validation"] = _validate_scale(payload)

    status, error = _validate_gate(payload)

    assert payload["scale_validation"] == "pass"
    assert status == "ok_low_confidence"
    assert error is None


def test_validate_gate_blocks_rp_trillion_source_unit_mismatch():
    """A Rp 12.5 trillion row must not persist as Rp 12.5 quadrillion."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="A", scale="trillions", currency="IDR")
    payload["metrics"]["revenue"] = 12_500_000_000_000_000
    payload["metrics"]["ebit"] = 2_400_000_000_000
    payload["metrics"]["np_attributable"] = 1_100_000_000_000
    payload["row_refs"] = {
        "revenue": "Revenue Rp 12.5 trillion",
        "ebit": "Operating profit Rp 2.4 trillion",
        "np_attributable": "NPAT Rp 1.1 trillion",
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == (
        "validation_gate:source_unit_value_mismatch:"
        "revenue:actual=1.25e+16:source_unit=1.25e+13"
    )


def test_source_period_evidence_detects_annual_and_ambiguous_cases():
    """Source-period detection is contradiction-only and leaves ambiguity non-blocking."""
    from app.services.multipass_extraction import _detect_source_period_evidence

    annual = _detect_source_period_evidence(
        "Financial Report 31 December 2025",
        "The annual report is for the year ended 31 December 2025.",
    )
    assert annual["period_type"] == "A"

    ambiguous = _detect_source_period_evidence(
        "Appendix 4D and Annual Report",
        "Half-year results with annual report appendix references.",
    )
    assert ambiguous["period_type"] is None
    assert ambiguous["reason"] == "ambiguous"


def test_source_document_classification_formalizes_advisory_and_report_cases():
    """Source classification exposes policy without weakening existing gates."""
    from app.services.multipass_extraction import classify_source_document

    advisory = classify_source_document(
        "March 2026 Quarterly Activities Report Advisory",
        "",
    )
    assert advisory.document_class == "advisory_only_document"
    assert advisory.extraction_candidate_allowed is False
    assert advisory.canary_candidate_allowed is False

    report = classify_source_document(
        "Financial Report 31 December 2025",
        "For the year ended 31 December 2025.",
    )
    assert report.document_class == "financial_report"
    assert report.extraction_candidate_allowed is True
    assert report.canary_candidate_allowed is True


def test_run_multipass_blocks_advisory_only_document_before_llm():
    """Quarterly report advisory documents must fail before metric extraction."""
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 1
        docling_version = None
        sections = [{"text": "Quarterly Report Advisory", "page": 1}]
        tables = []

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._llm_json_call",
        side_effect=AssertionError("advisory-only document should not call LLM"),
    ):
        result = run_multipass_extraction(
            "/fake/advisory.pdf",
            {"document_id": "sfr", "ticker": "SFR", "title": "Quarterly Report Advisory"},
            llm_client=None,
        )

    assert result.status == "failed"
    assert result.error == "validation_gate:advisory_only_document"
    assert result.payload["source_document_gate"] == "advisory_only_document"
    assert result.payload["source_document_classification"]["document_class"] == (
        "advisory_only_document"
    )
