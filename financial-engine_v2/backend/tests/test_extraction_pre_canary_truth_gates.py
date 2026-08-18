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


def test_source_period_evidence_ctn_quarterly_activity_report_beats_annual_reference():
    """CTN quarterly evidence must not be hijacked by a historical annual reference."""
    from app.services.multipass_extraction import _detect_source_period_evidence

    evidence = _detect_source_period_evidence(
        (
            "2022-04-28_quarterly-activities-appendix-5b-cash-flow-report_"
            "dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39.pdf"
        ),
        (
            "Quarterly Activity Report. Period ending 31st March 2022. "
            "Notes are prepared on a historical cost basis. "
            "Refer to the 2014 Annual Report to Shareholders for background."
        ),
    )

    assert evidence["period_type"] == "Q"
    assert evidence["reason"] == "quarterly_source_precedence_over_annual_report_reference"
    hits = evidence["hits"]
    assert any(hit["reason"] == "appendix_5b_source_phrase" for hit in hits)
    assert any(
        hit["reason"] == "quarterly_activity_report_source_phrase"
        and hit["source"] == "source_text"
        for hit in hits
    )
    assert any(
        hit["reason"] == "annual_report_title" and hit["source"] == "source_text"
        for hit in hits
    )


def test_source_period_evidence_detects_appendix_5b_quarterly_source():
    from app.services.multipass_extraction import _detect_source_period_evidence

    evidence = _detect_source_period_evidence(
        "Appendix 5B - Quarterly Cash Flow Report",
        (
            "Appendix 5B Mining exploration entity or oil and gas exploration "
            "entity quarterly cash flow report. Quarter ended 31/03/2022."
        ),
    )

    assert evidence["period_type"] == "Q"
    assert any(
        hit["reason"] == "appendix_5b_source_phrase" for hit in evidence["hits"]
    )


def test_source_period_evidence_keeps_true_mixed_annual_quarterly_ambiguous():
    from app.services.multipass_extraction import _detect_source_period_evidence

    title_annual = _detect_source_period_evidence(
        "Annual Report and Appendix 5B",
        "Quarterly Activity Report. Period ending 31st March 2022.",
    )
    assert title_annual["period_type"] is None
    assert title_annual["reason"] == "ambiguous"

    explicit_annual = _detect_source_period_evidence(
        "Appendix 5B",
        (
            "Annual report for the year ended 31 December 2025. "
            "Quarterly Activity Report."
        ),
    )
    assert explicit_annual["period_type"] is None
    assert explicit_annual["reason"] == "ambiguous"


def test_source_document_classifier_preserves_ctn_quarterly_candidate():
    from app.services.multipass_extraction import classify_source_document

    classification = classify_source_document(
        (
            "2022-04-28_quarterly-activities-appendix-5b-cash-flow-report_"
            "dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39.pdf"
        ),
        (
            "Quarterly Activity Report. Period ending 31st March 2022. "
            "Refer to the 2014 Annual Report to Shareholders for background."
        ),
    )

    assert classification.document_class == "financial_report"
    assert classification.extraction_candidate_allowed is True
    assert classification.canary_candidate_allowed is True
    assert (
        classification.reason
        == "quarterly_source_precedence_over_annual_report_reference"
    )
    assert "quarterly_activity_report_source_phrase" in classification.evidence


def test_validate_gate_accepts_ctn_q_payload_with_quarterly_source_evidence():
    from app.services.multipass_extraction import (
        _detect_source_period_evidence,
        _validate_gate,
    )

    source_period_evidence = _detect_source_period_evidence(
        (
            "2022-04-28_quarterly-activities-appendix-5b-cash-flow-report_"
            "dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39.pdf"
        ),
        (
            "Quarterly Activity Report. Period ending 31st March 2022. "
            "Refer to the 2014 Annual Report to Shareholders for background."
        ),
    )
    payload = _good_payload(period_type="Q", scale="thousands")
    payload["period_end"] = "2022-03-31"
    payload["metrics"] = {metric_name: None for metric_name in payload["metrics"]}
    payload["metrics"]["operating_cf"] = -164_000
    payload["row_refs"] = {
        "operating_cf": "Net cash from / (used in) operating activities (164)"
    }
    payload["source_period_type"] = source_period_evidence["period_type"]
    payload["source_period_evidence"] = source_period_evidence

    status, error = _validate_gate(payload)

    assert status in ("ok", "ok_low_confidence")
    assert error is None


def test_validate_gate_still_rejects_q_payload_against_explicit_annual_period_end():
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="Q", scale="thousands")
    payload["period_end"] = "2022-03-31"
    payload["metrics"] = {metric_name: None for metric_name in payload["metrics"]}
    payload["metrics"]["operating_cf"] = -164_000
    payload["row_refs"] = {
        "operating_cf": "Net cash from / (used in) operating activities (164)"
    }
    payload["source_period_end_evidence"] = {
        "period_type": "A",
        "period_end": "2022-12-31",
        "reason": "year_ended_explicit_date",
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == (
        "validation_gate:period_source_mismatch:"
        "payload=Q:source=A:year_ended_explicit_date"
    )


def test_explicit_source_period_end_conflict_is_hard_blocked():
    from app.services.multipass_extraction import (
        _detect_source_period_end_evidence,
        _validate_gate,
    )

    evidence = _detect_source_period_end_evidence(
        "Annual Report",
        "ANTILLES GOLD LIMITED FOR THE YEAR ENDED 31 DECEMBER 2025",
    )
    assert evidence["period_type"] == "A"
    assert evidence["period_end"] == "2025-12-31"

    payload = _good_payload(period_type="A", scale="thousands")
    payload["period_end"] = "2024-12-31"
    payload["source_period_end_evidence"] = evidence

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == (
        "validation_gate:period_end_source_mismatch:"
        "payload=2024-12-31:source=2025-12-31:year_ended_explicit_date"
    )


def test_explicit_source_period_end_type_conflict_is_hard_blocked():
    from app.services.multipass_extraction import (
        _detect_source_period_end_evidence,
        _validate_gate,
    )

    evidence = _detect_source_period_end_evidence(
        "Annual Report",
        "ANTILLES GOLD LIMITED FOR THE YEAR ENDED 31 DECEMBER 2024",
    )
    assert evidence["period_type"] == "A"
    assert evidence["period_end"] == "2024-12-31"

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = "2024-12-31"
    payload["source_period_evidence"] = {"period_type": None, "reason": "ambiguous"}
    payload["source_period_type"] = None
    payload["source_period_end_evidence"] = evidence

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == (
        "validation_gate:period_source_mismatch:"
        "payload=H:source=A:year_ended_explicit_date"
    )


def test_explicit_source_period_end_detection_refuses_ambiguous_or_loose_dates():
    from app.services.multipass_extraction import _detect_source_period_end_evidence

    loose = _detect_source_period_end_evidence(
        "Annual Report",
        "Released to the market on 31 December 2025.",
    )
    assert loose["period_end"] is None
    assert loose["reason"] == "not_detected"

    ambiguous = _detect_source_period_end_evidence(
        "Annual Report",
        (
            "Financial statements for the year ended 31 December 2025. "
            "Comparatives are also discussed for the year ended 31 December 2024."
        ),
    )
    assert ambiguous["period_end"] is None
    assert ambiguous["reason"] == "ambiguous"


def test_hub_explicit_source_period_end_overrides_announcement_date():
    from app.services.multipass_extraction import (
        _bind_explicit_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
        _has_source_text_period_end_hit,
        _validate_gate,
    )

    document_title = (
        "2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_"
        "419bcca8-213e-4706-8962-8e3bd8adf091.pdf"
    )
    evidence = _detect_source_period_end_evidence(
        document_title,
        (
            "Appendix 4D. Half-year ended 31 December 2023. "
            "Current period: 1 July 2023 to 31 December 2023."
        ),
    )
    assert evidence["period_type"] == "H"
    assert evidence["period_end"] == "2023-12-31"
    assert any(hit["source"] == "source_text" for hit in evidence["hits"])
    assert _has_source_text_period_end_hit(evidence) is True
    assert (
        _has_source_text_period_end_hit(
            evidence,
            reason="half_year_ended_explicit_date",
        )
        is True
    )

    pass1 = {"report_type": "H", "period_end": "2024-02-20"}
    changed = _bind_explicit_source_period_end_over_announcement_date(
        pass1,
        evidence,
        document_title,
    )

    assert changed is True
    assert pass1["period_end"] == "2023-12-31"
    assert pass1["_source_period_end_binding"] == {
        "reason": "explicit_source_half_year_period_end_over_announcement_title_date",
        "from_period_end": "2024-02-20",
        "to_period_end": "2023-12-31",
        "source_period_end_reason": "half_year_ended_explicit_date",
    }

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = pass1["period_end"]
    payload["source_period_end_evidence"] = evidence
    payload["source_bound"] = {
        "period_end": payload["period_end"],
        "period_type": payload["period_type"],
        "scale": payload["scale"],
        "currency": payload["currency"],
        "document_title": document_title,
    }

    status, error = _validate_gate(payload)

    assert status == "ok"
    assert error is None


def test_hub_current_period_line_beats_comparative_prior_half_year_source_date():
    from app.services.multipass_extraction import (
        _bind_explicit_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
        _validate_gate,
    )

    document_title = (
        "2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_"
        "419bcca8-213e-4706-8962-8e3bd8adf091.pdf"
    )
    early_text = (
        "Appendix 4D - Half-Year Ended 31 December 2023\n"
        "Current period: 1 July 2023 to 31 December 2023\n"
        "Prior corresponding period: 1 July 2022 to 31 December 2022\n"
        "Comparatives are presented for the half-year ended 31 December 2022."
    )

    evidence = _detect_source_period_end_evidence(document_title, early_text)

    assert evidence["period_type"] == "H"
    assert evidence["period_end"] == "2023-12-31"
    assert evidence["reason"] == "half_year_ended_explicit_date"
    assert evidence["selection_rule"] == (
        "current_period_source_text_over_comparative_period_end"
    )

    pass1 = {"report_type": "H", "period_end": "2024-02-20"}
    changed = _bind_explicit_source_period_end_over_announcement_date(
        pass1,
        evidence,
        document_title,
    )

    assert changed is True
    assert pass1["period_end"] == "2023-12-31"

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = pass1["period_end"]
    payload["source_period_end_evidence"] = evidence

    status, error = _validate_gate(payload)

    assert status == "ok"
    assert error is None

    true_conflict = _detect_source_period_end_evidence(
        document_title,
        (
            "Appendix 4D - Half-Year Ended 31 December 2024\n"
            "Current period: 1 July 2023 to 31 December 2023."
        ),
    )
    assert true_conflict["period_end"] is None
    assert true_conflict["reason"] == "ambiguous"


def test_hub_title_date_only_period_end_remains_fail_closed():
    from app.services.multipass_extraction import (
        _bind_explicit_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
        _has_source_text_period_end_hit,
        _validate_gate,
    )

    document_title = (
        "2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_"
        "419bcca8-213e-4706-8962-8e3bd8adf091.pdf"
    )
    evidence = _detect_source_period_end_evidence(
        document_title,
        "Appendix 4D interim financial report without an exact period-end date.",
    )
    assert evidence["period_end"] is None
    assert evidence["reason"] == "not_detected"
    assert _has_source_text_period_end_hit(evidence) is False

    pass1 = {"report_type": "H", "period_end": "2024-02-20"}
    changed = _bind_explicit_source_period_end_over_announcement_date(
        pass1,
        evidence,
        document_title,
    )
    assert changed is False
    assert pass1["period_end"] == "2024-02-20"

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = pass1["period_end"]
    payload["source_period_end_evidence"] = evidence
    payload["source_bound"] = {
        "period_end": payload["period_end"],
        "period_type": payload["period_type"],
        "scale": payload["scale"],
        "currency": payload["currency"],
        "document_title": document_title,
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == (
        "validation_gate:announcement_date_period_end:"
        "period_type=H:period_end=2024-02-20:"
        "title_date=2024-02-20:leading_title_date"
    )


def test_lbl_1h_fy26_label_only_period_end_remains_fail_closed():
    from app.services.multipass_extraction import (
        _bind_explicit_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
        _has_source_text_period_end_hit,
        _validate_gate,
    )

    document_title = (
        "2026-02-20_1h-fy26-results-presentation_"
        "551c6b84-1053-405c-a833-4ecc018e2045.pdf"
    )
    evidence = _detect_source_period_end_evidence(
        document_title,
        "1H FY26 Results Presentation. Half-Year. Five-Year Earnings A$000 1H FY26.",
    )
    assert evidence["period_end"] is None
    assert evidence["reason"] == "not_detected"
    assert _has_source_text_period_end_hit(evidence) is False

    pass1 = {"report_type": "H", "period_end": "2026-02-20"}
    changed = _bind_explicit_source_period_end_over_announcement_date(
        pass1,
        evidence,
        document_title,
    )
    assert changed is False
    assert pass1["period_end"] == "2026-02-20"

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = pass1["period_end"]
    payload["source_period_end_evidence"] = evidence
    payload["source_bound"] = {
        "period_end": payload["period_end"],
        "period_type": payload["period_type"],
        "scale": payload["scale"],
        "currency": payload["currency"],
        "document_title": document_title,
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == (
        "validation_gate:announcement_date_period_end:"
        "period_type=H:period_end=2026-02-20:"
        "title_date=2026-02-20:leading_title_date"
    )


def test_lbl_companion_appendix_period_binds_with_cross_document_provenance():
    from app.services.multipass_extraction import (
        _bind_companion_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
        _validate_gate,
    )

    target_path = (
        "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/"
        "financial_performance/"
        "2026-02-20_1h-fy26-results-presentation_"
        "551c6b84-1053-405c-a833-4ecc018e2045.pdf"
    )
    appendix_path = (
        "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/"
        "financial_performance/"
        "2026-02-20_fy26-half-year-appendix-4d-financial-statements_"
        "d63cbfaf-cc41-448b-90fa-9f66e55f3993.pdf"
    )
    announcement_path = (
        "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/"
        "financial_performance/"
        "2026-02-20_1h-fy26-results-announcement_"
        "989d03d6-9ba6-4ec6-84cc-fbf930dc120a.pdf"
    )
    target_title = target_path.rsplit("/", 1)[-1]
    target_evidence = _detect_source_period_end_evidence(
        target_title,
        "1H FY26 Results Presentation. Half-Year. Five-Year Earnings A$000 1H FY26.",
    )
    appendix_evidence = _detect_source_period_end_evidence(
        appendix_path.rsplit("/", 1)[-1],
        "Appendix 4D. For the half-year ended 31st December 2025.",
    )
    announcement_evidence = _detect_source_period_end_evidence(
        announcement_path.rsplit("/", 1)[-1],
        "Results for the six months ended 31 December 2025.",
    )

    pass1 = {"report_type": "H", "period_end": "2026-02-20", "scale": "millions"}
    changed = _bind_companion_source_period_end_over_announcement_date(
        pass1,
        target_evidence,
        target_title,
        target_source_path=target_path,
        companion_sources=[
            {
                "source_path": announcement_path,
                "period_end_evidence": announcement_evidence,
                "source_role": "results_announcement",
                "scale": "millions",
            },
            {
                "source_path": appendix_path,
                "period_end_evidence": appendix_evidence,
                "source_role": "appendix4d",
                "scale": "thousands",
            },
        ],
    )

    assert changed is True
    assert pass1["period_end"] == "2025-12-31"
    assert pass1["scale"] == "millions"
    assert pass1["_source_period_end_binding"] == {
        "reason": "explicit_companion_source_half_year_period_end_over_announcement_title_date",
        "from_period_end": "2026-02-20",
        "to_period_end": "2025-12-31",
        "source_period_end_reason": "half_year_ended_explicit_date",
        "target_document_title": target_title,
        "target_source_path": target_path,
        "period_source_path": appendix_path,
        "period_source_role": "appendix4d",
        "selection_rule": "same_day_same_ticker_companion_period_source",
        "target_title_announcement_date": "2026-02-20",
        "corroborating_source_paths": [announcement_path],
    }

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = pass1["period_end"]
    payload["source_period_end_evidence"] = appendix_evidence
    payload["source_period_end_binding"] = pass1["_source_period_end_binding"]
    payload["source_bound"] = {
        "period_end": payload["period_end"],
        "period_type": payload["period_type"],
        "scale": payload["scale"],
        "currency": payload["currency"],
        "document_title": target_title,
    }

    status, error = _validate_gate(payload)

    assert status == "ok"
    assert error is None


def test_companion_period_binding_fails_closed_when_sources_disagree():
    from app.services.multipass_extraction import (
        _bind_companion_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
    )

    target_path = (
        "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/"
        "financial_performance/"
        "2026-02-20_1h-fy26-results-presentation_"
        "551c6b84-1053-405c-a833-4ecc018e2045.pdf"
    )
    target_title = target_path.rsplit("/", 1)[-1]
    target_evidence = _detect_source_period_end_evidence(
        target_title,
        "1H FY26 Results Presentation. Half-Year. Five-Year Earnings A$000 1H FY26.",
    )
    appendix_evidence = _detect_source_period_end_evidence(
        "2026-02-20_fy26-half-year-appendix-4d-financial-statements.pdf",
        "Appendix 4D. For the half-year ended 31st December 2025.",
    )
    conflicting_announcement = _detect_source_period_end_evidence(
        "2026-02-20_1h-fy26-results-announcement.pdf",
        "Results for the six months ended 30 June 2025.",
    )

    pass1 = {"report_type": "H", "period_end": "2026-02-20"}
    changed = _bind_companion_source_period_end_over_announcement_date(
        pass1,
        target_evidence,
        target_title,
        target_source_path=target_path,
        companion_sources=[
            {
                "source_path": target_path.replace("presentation", "appendix-4d"),
                "period_end_evidence": appendix_evidence,
                "source_role": "appendix4d",
            },
            {
                "source_path": target_path.replace("presentation", "announcement"),
                "period_end_evidence": conflicting_announcement,
                "source_role": "results_announcement",
            },
        ],
    )

    assert changed is False
    assert pass1["period_end"] == "2026-02-20"
    assert pass1["_companion_source_period_end_binding_error"] == (
        "companion_period_end_conflict"
    )


def test_companion_period_binding_overrides_unsupported_pass1_period_end():
    from app.services.multipass_extraction import (
        _bind_companion_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
    )

    target_path = (
        "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/"
        "financial_performance/"
        "2026-02-20_1h-fy26-results-presentation_"
        "551c6b84-1053-405c-a833-4ecc018e2045.pdf"
    )
    appendix_path = (
        "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/"
        "financial_performance/"
        "2026-02-20_fy26-half-year-appendix-4d-financial-statements_"
        "d63cbfaf-cc41-448b-90fa-9f66e55f3993.pdf"
    )
    target_title = target_path.rsplit("/", 1)[-1]
    target_evidence = _detect_source_period_end_evidence(
        target_title,
        "1H FY26 Results Presentation. Half-Year. Five-Year Earnings A$000 1H FY26.",
    )
    appendix_evidence = _detect_source_period_end_evidence(
        appendix_path.rsplit("/", 1)[-1],
        "Appendix 4D. For the half-year ended 31st December 2025.",
    )

    pass1 = {"report_type": "H", "period_end": "2026-01-31", "scale": "thousands"}
    changed = _bind_companion_source_period_end_over_announcement_date(
        pass1,
        target_evidence,
        target_title,
        target_source_path=target_path,
        companion_sources=[
            {
                "source_path": appendix_path,
                "period_end_evidence": appendix_evidence,
                "source_role": "appendix4d",
            },
        ],
    )

    assert changed is True
    assert pass1["period_end"] == "2025-12-31"
    assert pass1["_source_period_end_binding"]["reason"] == (
        "explicit_companion_source_half_year_period_end_over_unsupported_pass1_period_end"
    )
    assert pass1["_source_period_end_binding"]["from_period_end"] == "2026-01-31"
    assert pass1["_source_period_end_binding"]["target_title_announcement_date"] == (
        "2026-02-20"
    )


def test_companion_source_discovery_scans_same_day_same_ticker_roles(
    tmp_path, monkeypatch
):
    from app.services import multipass_extraction as mp

    doc_dir = tmp_path / "data" / "asx" / "docs" / "LBL" / "financial_performance"
    doc_dir.mkdir(parents=True)
    target_path = (
        doc_dir
        / "2026-02-20_1h-fy26-results-presentation_"
        "551c6b84-1053-405c-a833-4ecc018e2045.pdf"
    )
    appendix_path = (
        doc_dir
        / "2026-02-20_fy26-half-year-appendix-4d-financial-statements_"
        "d63cbfaf-cc41-448b-90fa-9f66e55f3993.pdf"
    )
    announcement_path = (
        doc_dir
        / "2026-02-20_1h-fy26-results-announcement_"
        "989d03d6-9ba6-4ec6-84cc-fbf930dc120a.pdf"
    )
    off_date_path = (
        doc_dir
        / "2026-02-21_fy26-half-year-appendix-4d-financial-statements_"
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.pdf"
    )
    generic_path = (
        doc_dir
        / "2026-02-20_investor-update_"
        "bbbbbbbb-cccc-dddd-eeee-ffffffffffff.pdf"
    )
    for path in (
        target_path,
        appendix_path,
        announcement_path,
        off_date_path,
        generic_path,
    ):
        path.write_bytes(b"%PDF-1.4\n")

    read_names = []

    def fake_read_pdf_text(source_path):
        name = str(source_path).rsplit("/", 1)[-1]
        read_names.append(name)
        if "appendix-4d" in name:
            return "Appendix 4D. For the half-year ended 31st December 2025."
        if "results-announcement" in name:
            return "Results for the six months ended 31 December 2025."
        return ""

    monkeypatch.setattr(
        mp,
        "_read_pdf_text_for_companion_period_source",
        fake_read_pdf_text,
    )

    sources = mp._discover_same_day_companion_period_sources(str(target_path))

    assert {
        (source["source_role"], source["period_end_evidence"]["period_end"])
        for source in sources
    } == {
        ("appendix4d", "2025-12-31"),
        ("results_announcement", "2025-12-31"),
    }
    assert sorted(read_names) == sorted(
        [appendix_path.name, announcement_path.name]
    )


def test_title_only_explicit_period_end_does_not_override_announcement_date():
    from app.services.multipass_extraction import (
        _bind_explicit_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
        _has_source_text_period_end_hit,
        _validate_gate,
    )

    document_title = "2024-02-20 Half-year ended 31 December 2023 HUB.pdf"
    evidence = _detect_source_period_end_evidence(
        document_title,
        "Appendix 4D with no source-text period-end phrase.",
    )
    assert evidence["period_type"] == "H"
    assert evidence["period_end"] == "2023-12-31"
    assert all(hit["source"] == "title" for hit in evidence["hits"])
    assert _has_source_text_period_end_hit(evidence) is False

    pass1 = {"report_type": "H", "period_end": "2024-02-20"}
    changed = _bind_explicit_source_period_end_over_announcement_date(
        pass1,
        evidence,
        document_title,
    )

    assert changed is False
    assert pass1["period_end"] == "2024-02-20"

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = pass1["period_end"]
    payload["source_period_end_evidence"] = evidence

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == (
        "validation_gate:period_end_source_mismatch:"
        "payload=2024-02-20:source=2023-12-31:half_year_ended_explicit_date"
    )


def test_exact_source_period_end_does_not_override_non_announcement_date_conflict():
    from app.services.multipass_extraction import (
        _bind_explicit_source_period_end_over_announcement_date,
        _detect_source_period_end_evidence,
        _validate_gate,
    )

    document_title = (
        "2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_"
        "419bcca8-213e-4706-8962-8e3bd8adf091.pdf"
    )
    evidence = _detect_source_period_end_evidence(
        document_title,
        "Appendix 4D. Half-year ended 31 December 2023.",
    )
    pass1 = {"report_type": "H", "period_end": "2024-01-31"}

    changed = _bind_explicit_source_period_end_over_announcement_date(
        pass1,
        evidence,
        document_title,
    )

    assert changed is False
    assert pass1["period_end"] == "2024-01-31"

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = pass1["period_end"]
    payload["source_period_end_evidence"] = evidence

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == (
        "validation_gate:period_end_source_mismatch:"
        "payload=2024-01-31:source=2023-12-31:half_year_ended_explicit_date"
    )


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
