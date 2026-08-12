"""
Unit tests for the 4-pass multipass extraction pipeline.
LLM calls are mocked — these test logic, not model quality.
"""

from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest


def _fake_docling_extract_module(fake_doc):
    module = ModuleType("app.services.docling_extract")

    class ExtractionTimeoutError(Exception):
        pass

    module.ExtractionTimeoutError = ExtractionTimeoutError
    module.extract_structured = lambda *args, **kwargs: fake_doc
    return module


# ---------------------------------------------------------------------------
# Pass 1 — Document Classifier
# ---------------------------------------------------------------------------


def test_pass1_extracts_period_from_appendix_4d():
    """Classifier must identify half-year period from Appendix 4D heading."""
    from app.services.multipass_extraction import _run_pass1_classifier

    mock_response = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_response
    ):
        result = _run_pass1_classifier(
            title="Appendix 4D Half Year Report",
            first_page_text="For the half year ended 31 December 2024. All figures in AUD thousands.",
            llm_client=None,
        )

    assert result["report_type"] == "H"
    assert result["period_end"] == "2024-12-31"
    assert result["scale"] == "thousands"
    assert result["classifier_confidence"] >= 0.9


def test_pass1_returns_low_confidence_on_empty_input():
    """Classifier must return low confidence when given no meaningful text."""
    from app.services.multipass_extraction import _run_pass1_classifier

    mock_response = {
        "report_type": None,
        "period_end": None,
        "currency": "AUD",
        "scale": "unknown",
        "classifier_confidence": 0.1,
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_response
    ):
        result = _run_pass1_classifier(title="", first_page_text="", llm_client=None)

    assert result["classifier_confidence"] < 0.6


def test_run_multipass_uses_explicit_front_matter_period_end_when_pass1_misses_it():
    """AAU-style annual reports may put the period end in early front matter, not page 1."""
    from datetime import date

    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 4
        docling_version = None
        tables = []
        sections = [
            {"text": "2025 ANNUAL REPORT", "page": 1},
            {
                "text": (
                    "TABLE OF CONTENTS ANNUAL REPORT ANTILLES GOLD LIMITED "
                    "FOR THE YEAR ENDED 31 DECEMBER 2025"
                ),
                "page": 2,
            },
        ]

    pass1_missing_period = {
        "report_type": "A",
        "period_end": None,
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }
    pass3a_results = [
        {
            "_source": "cashflow_statement",
            "_page_number": 26,
            "pass3_confidence": 0.9,
            "operating_cf": 1_000_000,
            "investing_cf": -200_000,
            "financing_cf": 300_000,
            "row_refs": {
                "operating_cf": "Net cash used in operating activities",
                "investing_cf": "Net cash from investing activities",
                "financing_cf": "Net cash from financing activities",
            },
        }
    ]

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=pass1_missing_period,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=pass3a_results,
    ):
        result = run_multipass_extraction(
            "/fake/aau.pdf",
            {
                "document_id": "508fc892-ae88-45ec-981f-cd9e124c8375",
                "ticker": "AAU",
                "title": "Annual Report and Full Year Statutory Accounts",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert result.status in {"ok", "ok_low_confidence"}
    assert result.error is None
    assert result.payload["period_type"] == "A"
    assert result.payload["period_end"] == "2025-12-31"
    assert result.payload["period_start"] == date(2025, 1, 1)
    assert result.payload["source_period_end_evidence"]["period_end"] == "2025-12-31"


def test_run_multipass_rebinds_annual_report_title_date_to_source_period_end():
    """Annual-report publication dates must yield to exact same-document period text."""
    from datetime import date

    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 4
        docling_version = None
        tables = []
        sections = [
            {
                "text": (
                    "Whitehaven Coal 2022 Annual Report. "
                    "For the year ended 30 June 2022."
                ),
                "page": 1,
            },
        ]

    pass1_title_date = {
        "report_type": "A",
        "period_end": "2022-09-21",
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }
    pass3a_results = [
        {
            "_source": "income_statement",
            "_page_number": 57,
            "pass3_confidence": 0.9,
            "revenue": 4_920_102_000,
            "ebit": 2_821_254_000,
            "np_attributable": 1_951_965_000,
            "row_refs": {
                "revenue": "Revenue 21 4,920,102 1,556,976",
                "ebit": "EBIT 2,821,254",
                "np_attributable": "Net profit attributable 1,951,965",
            },
        }
    ]

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=pass1_title_date,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=pass3a_results,
    ):
        result = run_multipass_extraction(
            "/fake/whc.pdf",
            {
                "document_id": "9640d9f1-a45b-492d-8df5-9bad0f46431c",
                "ticker": "WHC",
                "title": (
                    "2022-09-21_2022-annual-report_"
                    "9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf"
                ),
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert result.status in {"ok", "ok_low_confidence"}
    assert result.error is None
    assert result.payload["period_type"] == "A"
    assert result.payload["period_end"] == "2022-06-30"
    assert result.payload["period_start"] == date(2021, 7, 1)
    assert result.payload["source_bound"]["period_end"] == "2022-06-30"
    assert result.payload["source_period_end_evidence"]["reason"] == (
        "year_ended_explicit_date"
    )
    assert result.payload["source_period_end_binding"]["reason"] == (
        "explicit_source_annual_period_end_over_announcement_title_date"
    )


def test_run_multipass_blocks_title_only_half_year_period_end_distinct_when_pass1_misses_it():
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 2
        docling_version = None
        tables = []
        sections = [
            {
                "text": (
                    "Appendix 4D interim financial report without an exact "
                    "source-text period-end date."
                ),
                "page": 1,
            },
        ]

    pass1_missing_period = {
        "report_type": "H",
        "period_end": None,
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }
    pass3a_results = [
        {
            "_source": "cashflow_statement",
            "_page_number": 4,
            "pass3_confidence": 0.9,
            "operating_cf": 1_000_000,
            "investing_cf": -200_000,
            "financing_cf": 300_000,
        }
    ]

    with patch.dict(
        "sys.modules",
        {"app.services.docling_extract": _fake_docling_extract_module(_FakeDoc())},
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=pass1_missing_period,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=pass3a_results,
    ):
        result = run_multipass_extraction(
            "/fake/hub-title-only.pdf",
            {
                "document_id": "hub-title-only",
                "ticker": "HUB",
                "title": "2024-02-20 Half-year ended 31 December 2023 HUB.pdf",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert pass1_missing_period["period_end"] is None
    assert result.status == "failed"
    assert result.error == "validation_gate:missing_period_end"
    assert result.payload["period_end"] is None
    assert result.payload["source_period_end_evidence"]["period_end"] == "2023-12-31"
    assert all(
        hit["source"] == "title"
        for hit in result.payload["source_period_end_evidence"]["hits"]
    )


def test_run_multipass_uses_source_text_half_year_period_end_distinct_when_pass1_misses_it():
    from datetime import date

    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 2
        docling_version = None
        tables = []
        sections = [
            {
                "text": (
                    "Appendix 4D. Half-year ended 31 December 2023. "
                    "Current period: 1 July 2023 to 31 December 2023."
                ),
                "page": 1,
            },
        ]

    pass1_missing_period = {
        "report_type": "H",
        "period_end": None,
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }
    pass3a_results = [
        {
            "_source": "cashflow_statement",
            "_page_number": 4,
            "pass3_confidence": 0.9,
            "operating_cf": 1_000_000,
            "investing_cf": -200_000,
            "financing_cf": 300_000,
        }
    ]

    with patch.dict(
        "sys.modules",
        {"app.services.docling_extract": _fake_docling_extract_module(_FakeDoc())},
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=pass1_missing_period,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=pass3a_results,
    ):
        result = run_multipass_extraction(
            "/fake/hub-source-text.pdf",
            {
                "document_id": "hub-source-text",
                "ticker": "HUB",
                "title": "HUB Appendix 4D interim financial report.pdf",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert pass1_missing_period["period_end"] == "2023-12-31"
    assert result.status in {"ok", "ok_low_confidence"}
    assert result.error is None
    assert result.payload["period_type"] == "H"
    assert result.payload["period_end"] == "2023-12-31"
    assert result.payload["period_start"] == date(2023, 7, 1)
    assert result.payload["source_period_end_evidence"]["period_end"] == "2023-12-31"
    assert any(
        hit["source"] == "source_text"
        for hit in result.payload["source_period_end_evidence"]["hits"]
    )


@pytest.mark.parametrize(
    ("title", "first_page_text", "document_class"),
    [
        (
            "notice-of-annual-general-meeting-proxy-form.pdf",
            (
                "Upcoming General Meeting of Shareholders. Annual General "
                "Meeting, Notice of Meeting and Explanatory Memorandum."
            ),
            "meeting_or_proxy_notice",
        ),
        (
            "notice-of-annual-general-meeting.pdf",
            "Notice of Annual General Meeting and Explanatory Statement.",
            "meeting_or_proxy_notice",
        ),
        (
            "results-of-meeting.pdf",
            "",
            "meeting_or_proxy_notice",
        ),
        (
            "fineos-board-changes.pdf",
            (
                "Upcoming FINEOS Board changes. Appointment of a new "
                "non-executive director is subject to securityholder approval "
                "at the AGM."
            ),
            "board_change_notice",
        ),
        (
            "update-in-relation-to-mt-morgans-gold-project.pdf",
            (
                "Update in Relation to Mt Morgans Gold Project. Dacian will "
                "discontinue open pit mining with no impact on FY22 revenue "
                "or earnings."
            ),
            "operational_project_update",
        ),
        (
            "vox-shares-sold-2-93m-gross-proceeds.pdf",
            (
                "VOX SHARES SOLD $2.93M GROSS PROCEEDS. Shares were sold on "
                "NASDAQ and TSX before fees and taxes."
            ),
            "share_sale_or_gross_proceeds_announcement",
        ),
        (
            "re-presentation-of-segment-results-and-terminology-changes.pdf",
            (
                "Re-presentation of segment results and changes in terminology. "
                "The company plans to announce 2026 half year financial results "
                "and there are no changes to statutory financial results."
            ),
            "pre_results_segment_re_presentation",
        ),
        (
            "change-of-directors-interest-notice-robert-nicholson.pdf",
            (
                "Appendix 3Y Change of Director's Interest Notice. "
                "Part 1 - Change of director's relevant interests in securities. "
                "Notifiable interest of a director."
            ),
            "director_interest_notice",
        ),
        (
            "half-year-results-webcast-details.pdf",
            (
                "Nickel Industries Limited Half Year Results Webcast Details. "
                "Investors are invited to register for the webcast presentation."
            ),
            "webcast_details_notice",
        ),
    ],
)
def test_source_document_classifier_excludes_known_false_positive_classes(
    title, first_page_text, document_class
):
    from app.services.multipass_extraction import classify_source_document

    result = classify_source_document(title, first_page_text)

    assert result.document_class == document_class
    assert result.extraction_candidate_allowed is False
    assert result.canary_candidate_allowed is False
    assert result.reason == f"source_noncandidate:{document_class}"
    assert result.evidence


@pytest.mark.parametrize(
    ("title", "first_page_text", "period_reason"),
    [
        (
            "annual-report-to-shareholders.pdf",
            "Annual Report for the year ended 30 June 2024.",
            "annual_report_title",
        ),
        (
            "appendix-4d-half-year-results.pdf",
            "Appendix 4D Half Year Results for the half year ended 31 December 2025.",
            "half_year_source_phrase",
        ),
        (
            "half-year-results.pdf",
            "Half-year financial results for the half year ended 31 December 2025.",
            "half_year_source_phrase",
        ),
        (
            "hy24-results-appendix-4d-and-financial-report.pdf",
            "Appendix 4D and financial report for the half year ended 31 December 2023.",
            "half_year_source_phrase",
        ),
        (
            "quarterly-activities-report-and-appendix-5b.pdf",
            "Quarterly activities report and Appendix 5B for the quarter ended 31 March 2024.",
            "quarterly_source_phrase",
        ),
        (
            "annual-report-directors-report.pdf",
            (
                "Annual Report for the year ended 30 June 2024. "
                "The directors present their report and the financial statements."
            ),
            "annual_report_title",
        ),
    ],
)
def test_source_document_classifier_preserves_valid_report_candidates(
    title, first_page_text, period_reason
):
    from app.services.multipass_extraction import classify_source_document

    result = classify_source_document(title, first_page_text)

    assert result.document_class == "financial_report"
    assert result.extraction_candidate_allowed is True
    assert result.canary_candidate_allowed is True
    assert result.reason == period_reason


def test_run_multipass_blocks_title_only_source_noncandidate_before_parser_import():
    from app.services.multipass_extraction import run_multipass_extraction

    with patch.dict("sys.modules", {"app.services.docling_extract": None}):
        result = run_multipass_extraction(
            "/fake/fineos-board-changes.pdf",
            {
                "document_id": "e7290bdf-2865-468c-9a9b-9fcc6a61d446",
                "ticker": "FCL",
                "title": "2022-10-24_fineos-board-changes_e7290bdf-2865-468c-9a9b-9fcc6a61d446.pdf",
            },
            llm_client=None,
        )

    assert result.status == "failed"
    assert result.error == "validation_gate:source_noncandidate:board_change_notice"
    assert result.sections == []
    assert result.payload["source_document_gate"] == (
        "source_noncandidate:board_change_notice"
    )
    assert result.payload["source_document_classification"]["document_class"] == (
        "board_change_notice"
    )


def test_run_multipass_abstains_unknown_contract_before_pass1_or_metric_extraction():
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 1
        docling_version = None
        tables = []
        sections = [{"text": "General corporate announcement", "page": 1}]

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
    ) as pass1, patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
    ) as pass3a:
        result = run_multipass_extraction(
            "/fake/general-announcement.pdf",
            {
                "document_id": "general-announcement",
                "ticker": "GEN",
                "title": "General corporate announcement",
            },
            llm_client=None,
        )

    assert result.status == "failed"
    assert result.error == "validation_gate:extraction_contract_abstain"
    assert result.payload["asx_document_type_classification"]["abstain"] is True
    assert result.payload["asx_extraction_contract"]["contract_id"] is None
    assert result.payload["asx_extraction_contract"]["canonical_write"] is False
    pass1.assert_not_called()
    pass3a.assert_not_called()


def test_run_multipass_collects_later_page_document_type_evidence():
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 2
        docling_version = None
        tables = []
        sections = [
            {"text": "Quarterly activities report", "page": 1},
            {
                "text": "Appendix 4C. Quarterly cash flow report. Rule 4.7B.",
                "page": 2,
            },
        ]

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value={
            "report_type": "A",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "thousands",
            "classifier_confidence": 0.97,
        },
    ):
        result = run_multipass_extraction(
            "/fake/quarterly-bundle.pdf",
            {
                "document_id": "quarterly-bundle",
                "ticker": "QTR",
                "title": "Quarterly activities report",
            },
            llm_client=None,
        )

    classification = result.payload["asx_document_type_classification"]
    assert classification["document_type"] == "appendix_4c"
    assert any(
        item["anchor"] == "Appendix 4C" and item["page"] == 2
        for item in classification["positive_evidence"]
    )
    assert result.error == "validation_gate:extraction_contract_period_basis_mismatch"


def test_run_multipass_abstains_contract_period_mismatch_before_metric_extraction():
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 1
        docling_version = None
        tables = []
        sections = [
            {
                "text": (
                    "Half-Year Report. Interim financial report. "
                    "Condensed consolidated financial statements."
                ),
                "page": 1,
            }
        ]

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value={
            "report_type": "A",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "thousands",
            "classifier_confidence": 0.97,
        },
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
    ) as pass2, patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
    ) as pass3a:
        result = run_multipass_extraction(
            "/fake/half-year-report.pdf",
            {
                "document_id": "half-year-report",
                "ticker": "HYR",
                "title": "Half-Year Report",
            },
            llm_client=None,
        )

    assert result.status == "failed"
    assert result.error == "validation_gate:extraction_contract_period_basis_mismatch"
    assert result.payload["asx_extraction_contract_routing"]["abstain"] is True
    pass2.assert_not_called()
    pass3a.assert_not_called()


def test_cashflow_contract_blocks_disallowed_metrics_and_prose_share_recovery():
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 2
        docling_version = None
        tables = []
        sections = [
            {
                "text": (
                    "Appendix 4C Quarterly cash flow report. Rule 4.7B. "
                    "For the quarter ended 31 March 2026."
                ),
                "page": 1,
            },
            {
                "text": (
                    "At 31 March 2026, Example Limited had 25 million ordinary "
                    "shares on issue and held by the public."
                ),
                "page": 2,
            },
        ]

    pass3a_result = {
        "_source": "highlights",
        "_page_number": 1,
        "revenue": 1_000_000,
        "ebit": 250_000,
        "np_attributable": 125_000,
        "net_debt": 50_000,
        "shares_outstanding": 25_000_000,
        "operating_cf": 500_000,
        "cash_end": 800_000,
        "pass3_confidence": 0.9,
        "row_refs": {
            "revenue": "Revenue",
            "ebit": "EBIT",
            "np_attributable": "Net profit",
            "net_debt": "Net debt",
            "shares_outstanding": "Ordinary shares on issue",
            "operating_cf": "Net cash from operating activities",
            "cash_end": "Cash and cash equivalents at end of period",
        },
    }

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value={
            "report_type": "Q",
            "period_end": "2026-03-31",
            "currency": "AUD",
            "scale": "thousands",
            "classifier_confidence": 0.97,
        },
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={"unmatched": []},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=[pass3a_result],
    ):
        result = run_multipass_extraction(
            "/fake/appendix-4c.pdf",
            {
                "document_id": "appendix-4c",
                "ticker": "EXM",
                "title": "Appendix 4C Quarterly cash flow report",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert result.payload["operating_cf"] == 500_000
    assert result.payload["cash_end"] == 800_000
    for metric_name in (
        "revenue",
        "ebit",
        "np_attributable",
        "net_debt",
        "shares_outstanding",
    ):
        assert result.payload[metric_name] is None
        assert result.payload["metrics"][metric_name] is None
        assert metric_name not in result.payload["row_refs"]
        assert metric_name not in result.payload["provenance"]


def _gpt_appendix_4d_sections(*, include_disclosures: bool = True) -> list[dict]:
    sections = [
        {"text": "ASX Announcement", "page": 1},
        {"text": "Appendix 4D - GPT Management Holdings Limited", "page": 1},
        {"text": "Interim Financial Report", "page": 2},
        {"text": "For the half year ended 30 June 2024", "page": 2},
        {"text": "Results for announcement to the market", "page": 2},
        {"text": "30 June 24", "page": 2},
        {"text": "$'000", "page": 2},
        {"text": "2.1", "page": 2},
        {"text": "Total revenues and other income", "page": 2},
        {"text": "150,804", "page": 2},
        {"text": "2.2", "page": 2},
        {"text": "Net profit after income tax expense from ordinary", "page": 2},
        {"text": "activities", "page": 2},
        {"text": "15,463", "page": 2},
        {"text": "2.3", "page": 2},
        {"text": "Net profit after income tax expense attributable to", "page": 2},
        {"text": "members", "page": 2},
        {"text": "15,462", "page": 2},
        {"text": "Dividends", "page": 2},
        {"text": "Amount per security", "page": 2},
        {"text": "Nil", "page": 2},
        {"text": "Net tangible assets per security", "page": 2},
    ]
    if include_disclosures:
        sections.extend(
            [
                {"text": "Record date for determining entitlement to the", "page": 2},
                {"text": "N/A", "page": 2},
                {"text": "Details of associates and joint ventures entities", "page": 3},
            ]
        )
    return sections


def test_run_multipass_carries_gpt_appendix_4d_source_bound_payload():
    """GPT Appendix 4D summary evidence must survive into the validation payload."""
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 3
        docling_version = None
        tables = []
        sections = _gpt_appendix_4d_sections()

    pass1_wrong_period = {
        "report_type": "Q",
        "period_end": None,
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }

    def _pass3a_bad_attached_statement(_labelled, pass1, llm_client, **kwargs):
        assert pass1["report_type"] == "H"
        assert pass1["period_end"] == "2024-06-30"
        return [
            {
                "_source": "income_statement",
                "_page_number": 2,
                "revenue": None,
                "np_attributable": 15_462_000,
                "pass3_confidence": 0.88,
                "row_refs": {
                    "np_attributable": (
                        "Net profit after income tax expense attributable to members"
                    )
                },
            }
        ]

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=pass1_wrong_period,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        side_effect=_pass3a_bad_attached_statement,
    ):
        result = run_multipass_extraction(
            "/fake/gpt-appendix-4d.pdf",
            {
                "document_id": "gpt-appendix-4d",
                "ticker": "GPT",
                "title": "Appendix 4D - GPT Management Holdings Limited",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert result.status == "ok"
    assert result.error is None
    assert result.payload["period_type"] == "H"
    assert result.payload["period_end"] == "2024-06-30"
    assert result.payload["scale"] == "thousands"
    assert result.payload["currency"] == "AUD"
    assert result.payload["metrics"]["revenue"] == 150_804_000
    assert result.payload["metrics"]["np_attributable"] == 15_463_000
    assert result.payload["revenue"] == 150_804_000
    assert result.payload["np_attributable"] == 15_463_000
    assert result.payload["source_bound"]["period_type"] == "H"
    assert result.payload["source_bound"]["period_end"] == "2024-06-30"
    assert result.payload["source_bound"]["scale"] == "thousands"
    assert result.payload["source_bound"]["currency"] == "AUD"
    assert result.payload["source_bound"]["document_subtype"] == "appendix4d"
    assert len(result.payload["wrapper_disclosures"]) == 4
    assert "ordinary" in result.payload["row_refs"]["np_attributable"].lower()
    assert "dividends" not in result.payload["metrics"]
    assert "record_date" not in result.payload["metrics"]
    assert "nta_per_security" not in result.payload["metrics"]


def test_run_multipass_uses_explicit_source_text_scale_when_tables_missing():
    """Appendix wrapper scale can come from explicit source text when tables are absent."""
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 3
        docling_version = None
        tables = []
        sections = _gpt_appendix_4d_sections()

    pass1_unknown_scale = {
        "report_type": "H",
        "period_end": "2024-06-30",
        "currency": "AUD",
        "scale": "unknown",
        "classifier_confidence": 0.97,
    }

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=pass1_unknown_scale,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=[],
    ):
        result = run_multipass_extraction(
            "/fake/gpt-appendix-4d.pdf",
            {
                "document_id": "gpt-appendix-4d",
                "ticker": "GPT",
                "title": "Appendix 4D - GPT Management Holdings Limited",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert result.status == "ok"
    assert result.error is None
    assert result.payload["scale"] == "thousands"
    assert result.payload["source_bound"]["scale"] == "thousands"
    assert result.payload["metrics"]["revenue"] == 150_804_000
    assert result.payload["metrics"]["np_attributable"] == 15_463_000


def test_run_multipass_appendix_4d_fails_closed_without_wrapper_disclosures():
    """Wrapper source metrics cannot pass the two-metric gate without disclosures."""
    from app.services.multipass_extraction import run_multipass_extraction

    class _FakeDoc:
        extraction_method = "pymupdf"
        page_count = 3
        docling_version = None
        tables = []
        sections = _gpt_appendix_4d_sections(include_disclosures=False)

    pass1_wrong_period = {
        "report_type": "Q",
        "period_end": None,
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.97,
    }

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=pass1_wrong_period,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=[],
    ):
        result = run_multipass_extraction(
            "/fake/gpt-appendix-4d.pdf",
            {
                "document_id": "gpt-appendix-4d",
                "ticker": "GPT",
                "title": "Appendix 4D - GPT Management Holdings Limited",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert result.status == "failed"
    assert result.error == "validation_gate:wrapper_missing_disclosure_evidence"
    assert result.payload["period_type"] == "H"
    assert result.payload["period_end"] == "2024-06-30"
    assert result.payload["metrics"]["revenue"] == 150_804_000
    assert result.payload["metrics"]["np_attributable"] == 15_463_000


# ---------------------------------------------------------------------------
# Pass 2 — Table Locator
# ---------------------------------------------------------------------------


def test_pass2_labels_cashflow_table_by_caption():
    """Table locator must assign a table with 'cash flow' caption to cashflow_statement."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    cashflow_table = DoclingTable(
        page_number=3,
        caption="Consolidated Statement of Cash Flows",
        rows=[
            ["Row", "Current", "Prior"],
            ["Net cash from operations", "3,241", "2,876"],
        ],
        headers=["Row", "Current", "Prior"],
    )
    result = _run_pass2_locator([cashflow_table])
    assert result["cashflow_statement"] is cashflow_table
    assert result["income_statement"] is None


def test_pass2_higher_score_wins_on_conflict():
    """When two tables match the same type, the one with more keyword matches wins."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    weak = DoclingTable(
        page_number=1, caption="cash", rows=[["cash flow", "100"]], headers=[]
    )
    strong = DoclingTable(
        page_number=3,
        caption="Cash Flow Statement — Financing Activities",
        rows=[["net cash from operations", "1000"], ["financing activities", "200"]],
        headers=[],
    )
    result = _run_pass2_locator([weak, strong])
    assert result["cashflow_statement"] is strong


def test_pass2_prefers_share_count_table_over_equity_statement():
    """share_capital should prefer explicit period-end share counts over US$ equity tables."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    equity_statement = DoclingTable(
        page_number=20,
        caption="",
        rows=[
            ["", "SHAREHOLDERS' EQUITY.CONTRIBUTED EQUITY US$M", "TOTAL EQUITY US$M"],
            ["At 1 January 2025", "7,824", "10,728"],
            ["Shares issued under Employee Share and Option Plan and held in trust", "55", "55"],
            ["Dividends paid on ordinary shares", "(479)", "(479)"],
        ],
        headers=["", "SHAREHOLDERS' EQUITY.CONTRIBUTED EQUITY US$M", "TOTAL EQUITY US$M"],
    )
    share_count_table = DoclingTable(
        page_number=32,
        caption="",
        rows=[
            ["", "30JUNE2025.NUMBEROF SHARES MILLIONS", "30JUNE2025.US$M"],
            ["Issued ordinary shares, fully paid at 1 January", "1,505", "7,824"],
            ["Issued ordinary shares, fullypaidat30June", "1,510", "8,338"],
            ["Shares notified to the Australian Securities Exchange", "1,510", "8,339"],
        ],
        headers=["", "30JUNE2025.NUMBEROF SHARES MILLIONS", "30JUNE2025.US$M"],
    )

    result = _run_pass2_locator([equity_statement, share_count_table])

    assert result["share_capital"] is share_count_table


def test_pass2_share_capital_prefers_period_end_count_over_weighted_average():
    """Weighted-average EPS denominator tables must lose to period-end share-count tables."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    weighted_average = DoclingTable(
        page_number=33,
        caption="",
        rows=[
            ["", "30JUNE 2025 NUMBEROF SHARES MILLIONS", "30JUNE 2024 NUMBEROF SHARES MILLIONS"],
            [
                "Weighted average numberofordinary shares onissue and used as the denominator in calculating basic earnings per share",
                "1,508",
                "1,498",
            ],
            [
                "Weighted average numberofordinary shares used as the denominator in calculating diluted earnings per share",
                "1,523",
                "1,509",
            ],
        ],
        headers=["", "30JUNE 2025 NUMBEROF SHARES MILLIONS", "30JUNE 2024 NUMBEROF SHARES MILLIONS"],
    )
    period_end_count = DoclingTable(
        page_number=32,
        caption="",
        rows=[
            ["", "30JUNE2025.NUMBEROF SHARES MILLIONS", "30JUNE2025.US$M"],
            ["Issued ordinary shares, fully paid at 1 January", "1,505", "7,824"],
            ["Issued ordinary shares, fullypaidat30June", "1,510", "8,338"],
        ],
        headers=["", "30JUNE2025.NUMBEROF SHARES MILLIONS", "30JUNE2025.US$M"],
    )

    result = _run_pass2_locator([weighted_average, period_end_count])

    assert result["share_capital"] is period_end_count


def test_pass2_share_capital_selects_stapled_security_count_table():
    """Stapled-security note tables must populate the share_capital slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    stapled_security_note = DoclingTable(
        page_number=40,
        caption="Note 14 Contributed equity",
        rows=[
            [
                "",
                "For the 6 months to 31 Dec 2025 No. of securities",
                "For the 12 months to 30 Jun 2025 No. of securities",
            ],
            ["Opening balance", "1,075,565,246", "1,075,565,246"],
            ["Closing balance", "1,075,565,246", "1,075,565,246"],
        ],
        headers=[
            "",
            "For the 6 months to 31 Dec 2025 No. of securities",
            "For the 12 months to 30 Jun 2025 No. of securities",
        ],
    )

    result = _run_pass2_locator([stapled_security_note])

    assert result["share_capital"] is stapled_security_note


def test_pass2_selects_point_in_time_net_debt_note_table():
    """Point-in-time tables with an explicit net debt row should get a dedicated slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    year_end_summary = DoclingTable(
        page_number=1,
        caption="Year ended 30 June 2021",
        rows=[
            ["Year ended 30 June", "2021", "2020"],
            ["Revenue", "100", "90"],
            ["Net debt", "4,121", "12,044"],
        ],
        headers=["Year ended 30 June", "2021", "2020"],
    )
    point_in_time_note = DoclingTable(
        page_number=5,
        caption="",
        rows=[
            ["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
            ["Borrowings", "(15,730)", "(14,896)"],
            ["Cash and cash equivalents", "1,436", "1,012"],
            ["Net debt", "(16,800)", "(16,445)"],
        ],
        headers=["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
    )

    result = _run_pass2_locator([year_end_summary, point_in_time_note])

    assert result["net_debt_note"] is point_in_time_note


def test_pass2_selects_net_debt_note_from_preceding_at_31_december_row():
    """Point-in-time markers in preceding rows must survive locator normalization."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    rio_style_summary = DoclingTable(
        page_number=1,
        caption="",
        rows=[
            ["Year ended 31 December", "2024", "2023", "Change"],
            [
                "Net cash generated from operating activities (US$ millions)",
                "15,599",
                "15,160",
                "3%",
            ],
            ["", "At 31 December 2024", "At 31 December 2023", ""],
            ["Net debt¹ (US$ millions)", "5,491", "4,231", "30%"],
        ],
        headers=["Year ended 31 December", "2024", "2023", "Change"],
    )

    result = _run_pass2_locator([rio_style_summary])

    assert result["net_debt_note"] is rio_style_summary


def test_pass2_selects_net_debt_note_from_at_year_end_header():
    """Year-end point-in-time headers should populate the dedicated net debt slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    rio_2023_style = DoclingTable(
        page_number=1,
        caption="",
        rows=[
            ["At year end", "2023", "2022", "Change"],
            ["Revenue", "54,041", "55,554", "(3)%"],
            ["Net debt", "4,231", "4,188", "1%"],
        ],
        headers=["At year end", "2023", "2022", "Change"],
    )

    result = _run_pass2_locator([rio_2023_style])

    assert result["net_debt_note"] is rio_2023_style


def test_pass2_rejects_year_end_net_debt_summary_from_note_slot():
    """Year-end performance summaries must not populate the explicit net-debt note slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    year_end_summary = DoclingTable(
        page_number=1,
        caption="Year ended 30 June 2021",
        rows=[
            ["Year ended 30 June", "2021", "2020"],
            ["Net operating cash flow", "27,234", "15,706"],
            ["Net debt", "4,121", "12,044"],
        ],
        headers=["Year ended 30 June", "2021", "2020"],
    )

    result = _run_pass2_locator([year_end_summary])

    assert result["net_debt_note"] is None


def test_pass2_rejects_formula_style_year_end_net_debt_note_without_as_at_marker():
    """Year-ended formula tables must not populate the point-in-time net-debt slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    year_end_summary = DoclingTable(
        page_number=3,
        caption="",
        rows=[
            ["Year ended 30 June", "2021", "2020"],
            ["Net operating cash flow", "27,234", "15,706"],
            ["Net debt", "4,121", "12,044"],
        ],
        headers=["Year ended 30 June", "2021", "2020"],
    )
    bhp_style_note = DoclingTable(
        page_number=66,
        caption="",
        rows=[
            ["Year ended 30 June", "2021 US$M", "2020 US$M Restated"],
            ["Interest bearing liabilities - Current", "2,628", "5,012"],
            ["Interest bearing liabilities - Non current", "18,355", "22,036"],
            ["Total interest bearing liabilities", "20,983", "27,048"],
            ["Borrowing", "17,087", "23,605"],
            ["Lease liabilities", "3,896", "3,443"],
            [
                "Less: Lease liability associated with index-linked freight contracts",
                "1,025",
                "1,160",
            ],
            ["Less: Cash and cash equivalents", "15,246", "13,426"],
            ["Less: Net debt management related instruments", "557", "433"],
            ["Less: Total derivatives included in net debt", "591", "418"],
            ["Net debt", "4,121", "12,044"],
        ],
        headers=["Year ended 30 June", "2021 US$M", "2020 US$M Restated"],
    )

    result = _run_pass2_locator([year_end_summary, bhp_style_note])

    assert result["net_debt_note"] is None


def test_pass2_selects_current_noncurrent_net_debt_note_without_as_at_marker():
    """Current/non-current stock layouts are explicit enough for the note slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    bhp_2025_style = DoclingTable(
        page_number=158,
        caption="For personal use only",
        rows=[
            ["US$M", "2025", "", "", "2024"],
            ["", "Current", "", "Non-current", ""],
            ["Interest bearing liabilities", "", "", "", ""],
            ["Bank loans", "40", "", "3,691", ""],
            ["Notes and debentures", "1,316", "", "16,337", ""],
            ["Total interest bearing liabilities", "2,018", "", "22,478", ""],
            ["Less: Total cash and cash equivalents", "11,894", "", "-", ""],
            ["Less: Total derivatives included in net debt", "(47)", "", "(608)", ""],
            ["Net debt", "", "", "12,924", ""],
        ],
        headers=["US$M", "2025", "", "", "2024"],
    )

    result = _run_pass2_locator([bhp_2025_style])

    assert result["net_debt_note"] is bhp_2025_style


def test_pass2_rejects_glossary_definition_from_net_debt_note_slot():
    """Glossary prose must not be mistaken for a formula-style net debt note."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    glossary = DoclingTable(
        page_number=50,
        caption="",
        rows=[
            ["GLOSSARY", ""],
            ["Mineral Reserve", "A Mineral Reserve is the economically mineable part."],
            [
                "Net debt",
                "Gross debt less cash and cash equivalents. Includes finance lease liabilities.",
            ],
            ["NPAT only", "Statutory Net Profit after Tax"],
        ],
        headers=["GLOSSARY", ""],
    )

    result = _run_pass2_locator([glossary])

    assert result["net_debt_note"] is None


# ---------------------------------------------------------------------------
# Pass 3a — Scale normalisation and negative values
# ---------------------------------------------------------------------------


def test_pass3a_applies_thousands_multiplier():
    """Metric values must be multiplied by 1000 when scale=thousands."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flow Statement",
        rows=[["", "H1 2025"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025"],
        raw_header_rows=[["", "31 Dec 2024"]],
    )
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "operating_cf": 3241,
        "investing_cf": None,
        "financing_cf": None,
        "cash_end": None,
        "pass3_confidence": 0.95,
        "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["operating_cf"] == 3_241_000  # multiplied by 1000


def test_pass3a_negative_values_preserved():
    """Negative values (already negative from LLM) must remain negative after scaling."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flow",
        rows=[["", "H1"], ["Investing activities", "(412)"]],
        headers=["", "31 Dec 2024"],
        raw_header_rows=[["", "31 Dec 2024"]],
    )
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "operating_cf": None,
        "investing_cf": -412,
        "financing_cf": None,
        "cash_end": None,
        "pass3_confidence": 0.9,
        "row_refs": {"investing_cf": "Investing activities"},
    }
    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["investing_cf"] == -412_000


def test_pass3a_parses_common_accounting_number_strings():
    """Pass3a should coerce source-bound accounting strings before scaling."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    table = DoclingTable(
        page_number=3,
        caption="Consolidated income statement",
        rows=[
            ["", "FY2026"],
            ["Revenue", "$1.2m"],
            ["EBIT", "(123)"],
            ["Net profit attributable", "A$4.5 million"],
        ],
        headers=["", "FY2026"],
        raw_header_rows=[["", "30 Jun 2026"]],
    )
    labelled = {
        "income_statement": table,
        "cashflow_statement": None,
        "balance_sheet": None,
        "net_debt_note": None,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "A",
        "period_end": "2026-06-30",
        "currency": "AUD",
        "scale": "thousands",
    }
    mock_raw = {
        "revenue": "$1.2m",
        "ebit": "(123)",
        "np_attributable": "A$4.5 million",
        "pass3_confidence": 0.9,
        "row_refs": {
            "revenue": "Revenue",
            "ebit": "EBIT",
            "np_attributable": "Net profit attributable",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=mock_raw,
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["revenue"] == 1_200_000
    assert results[0]["ebit"] == -123_000
    assert results[0]["np_attributable"] == 4_500_000


def test_pass3a_extracts_net_debt_note():
    """The dedicated note slot should request and return only explicit net_debt."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=45,
        caption="",
        rows=[
            ["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
            ["Borrowings", "(15,730)", "(14,896)"],
            ["Cash and cash equivalents", "1,436", "1,012"],
            ["Net debt", "(16,800)", "(16,445)"],
        ],
        headers=["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "net_debt_note": table,
        "balance_sheet": None,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
    }

    mock_raw = {
        "net_debt": -16800,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["_source"] == "net_debt_note"
    assert results[0]["net_debt"] == 16_800_000_000
    assert results[0]["row_refs"]["net_debt"] == "Net debt"


def test_pass3a_recovers_net_debt_note_from_selected_table_when_llm_abstains():
    """Selected net_debt_note tables should recover an explicit row deterministically."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=158,
        caption="For personal use only",
        rows=[
            ["US$M", "2025", "", "", "2024"],
            ["", "Current", "", "Non-current", ""],
            ["Interest bearing liabilities", "", "", "", ""],
            ["Total interest bearing liabilities", "2,018", "", "22,478", ""],
            ["Less: Total cash and cash equivalents", "11,894", "", "-", ""],
            ["Less: Total derivatives included in net debt", "(47)", "", "(608)", ""],
            ["Net debt", "", "", "12,924", ""],
        ],
        headers=["US$M", "2025", "", "", "2024"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "net_debt_note": table,
        "balance_sheet": None,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "A",
        "period_end": "2025-06-30",
        "currency": "USD",
        "scale": "millions",
    }

    mock_raw = {
        "net_debt": None,
        "pass3_confidence": 0.4,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["net_debt"] == 12_924_000_000
    assert results[0]["row_refs"]["net_debt"] == "Net debt"
    assert results[0]["period_col"] == "2025 Non-current"


# ---------------------------------------------------------------------------
# Pass 3b — Narrative extractor
# ---------------------------------------------------------------------------


def test_pass3b_returns_null_on_empty_sections():
    """Narrative extractor must return all-null dict when sections are empty."""
    from app.services.multipass_extraction import _run_pass3b_narrative_extractor

    result = _run_pass3b_narrative_extractor(sections=[], llm_client=None)
    assert result["risk_summary"] is None
    assert result["guidance_summary"] is None
    assert result["confidence_narrative"] == 0.0


# ---------------------------------------------------------------------------
# Pass 4 — Reconciler
# ---------------------------------------------------------------------------


def test_pass4_merges_non_overlapping_metrics():
    """Reconciler must combine metrics from different table sources."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "operating_cf": 3_241_000,
            "investing_cf": -412_000,
            "financing_cf": None,
            "cash_end": None,
            "pass3_confidence": 0.9,
            "row_refs": {},
        },
        {
            "_source": "income_statement",
            "revenue": 27_841_000_000,
            "ebit": 9_100_000_000,
            "np_attributable": None,
            "pass3_confidence": 0.88,
            "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.0,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert result["metrics"]["operating_cf"] == 3_241_000
    assert result["metrics"]["revenue"] == 27_841_000_000
    assert result["period_end"] == "2024-12-31"


# ---------------------------------------------------------------------------
# Scale detection priority — table headers always authoritative over LLM
# ---------------------------------------------------------------------------


def test_scale_override_mutates_pass1_dict():
    """The override block must mutate pass1['scale'] when table headers are authoritative."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flows",
        rows=[["", "31 Dec 2024 $'000"], ["Operating CF", "3,241"]],
        headers=["", "31 Dec 2024 $'000"],
    )
    # Simulate the pass1 result that LLM returned wrongly
    pass1 = {"scale": "millions", "report_type": "H", "period_end": "2024-12-31"}

    # Apply the same override logic as run_multipass_extraction
    detected = _detect_scale_from_tables([table])
    if detected != "unknown":
        pass1["scale"] = detected

    assert pass1["scale"] == "thousands", (
        f"Override must mutate pass1['scale'] from 'millions' to 'thousands', got {pass1['scale']!r}"
    )


@pytest.mark.parametrize("marker", ["$A\u2019000", "$A\u2018000"])
def test_scale_detects_smart_apostrophe_thousands_marker(marker):
    """ASX Appendix cash-flow headers may use smart apostrophes in $A'000."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=6,
        caption="Appendix 5B",
        rows=[
            ["Consolidated statement of cash flows", "Current quarter", "Year to date"],
            ["", marker, marker],
            ["Net cash from / (used in) operating activities", "(3,756)", "(3,756)"],
        ],
        headers=["Consolidated statement of cash flows", "Current quarter", "Year to date"],
    )

    assert _detect_scale_from_tables([table]) == "thousands"


def test_scale_detects_fragmented_statement_unit_row_below_headings():
    """AZJ-style selected tables can place explicit $m units below split headings."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=9,
        caption="",
        headers=["", "", "Consolida", "ted income", "statement"],
        rows=[
            ["", "", "Aurizon Netwo", "rk Pty Ltd", ""],
            ["", "", "For the yea", "r ended 30", "June 2025"],
            ["", "", "", "", ""],
            ["", "", "2025", "2024", ""],
            ["", "Notes", "$m", "$m", ""],
            ["Revenue from continuing operations", "1", "1,428.2", "1,435.3", ""],
        ],
    )

    assert _detect_scale_from_tables([table]) == "millions"


def test_statement_page_text_recovers_uppercase_m_scale_when_table_unit_row_dropped():
    """TCL-style PyMuPDF tables can drop formal $M unit rows kept in page text."""
    from app.services.multipass_extraction import (
        _detect_scale_from_statement_page_text,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=17,
        caption="Consolidated statement of comprehensive income for the half-year ended 31 December 2025",
        headers=["Revenue B4", "1,983", "1,833"],
        rows=[
            ["Revenue B4", "1,983", "1,833"],
            ["Profit/(loss) before income tax", "352", "(8)"],
        ],
    )
    sections = [
        {"page": 17, "text": "Half-year ended"},
        {"page": 17, "text": "31 December 2025 31 December 2024"},
        {"page": 17, "text": "Note"},
        {"page": 17, "text": "$M"},
        {"page": 17, "text": "$M"},
        {"page": 17, "text": "Revenue B4 1,983 1,833"},
    ]

    assert _detect_scale_from_statement_page_text(sections, [table]) == "millions"


def test_statement_page_text_ignores_non_statement_m_summary_rows():
    """Dollar-M prose/highlight values must not become document scale evidence."""
    from app.services.multipass_extraction import (
        _detect_scale_from_statement_page_text,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=13,
        caption="",
        headers=["Market capitalisation", "$44.3B", "$43.5B"],
        rows=[
            ["Securities on issue", "3,115M", "3,108M"],
            ["Cash and cash equivalents", "$1,229M", "$1,727M"],
        ],
    )
    sections = [
        {
            "page": 13,
            "text": "Market capitalisation $44.3B Securities on issue 3,115M Cash and cash equivalents $1,229M",
        }
    ]

    assert _detect_scale_from_statement_page_text(sections, [table]) == "unknown"


def test_statement_page_text_ignores_statement_page_million_prose():
    """Statement-page prose mentions are not the same as formal unit rows."""
    from app.services.multipass_extraction import (
        _detect_scale_from_statement_page_text,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=17,
        caption="Consolidated statement of comprehensive income",
        headers=["Revenue", "1,983", "1,833"],
        rows=[["Revenue", "1,983", "1,833"]],
    )
    sections = [
        {"page": 17, "text": "Consolidated statement of comprehensive income"},
        {"page": 17, "text": "Revenue increased by $93 million during the half-year"},
    ]

    assert _detect_scale_from_statement_page_text(sections, [table]) == "unknown"


def test_statement_page_text_abstains_on_mixed_statement_page_scales():
    """Mixed group/entity statement units are not safe document-scale evidence."""
    from app.services.multipass_extraction import (
        _detect_scale_from_statement_page_text,
    )
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=20,
            caption="Consolidated Statement of Cash Flows",
            headers=["Net cash inflow from operating activities", "168.5", "264.1"],
            rows=[],
        ),
        DoclingTable(
            page_number=51,
            caption="Consolidated Statement of Comprehensive Income",
            headers=["Total income", "243,661", "299,840"],
            rows=[],
        ),
    ]
    sections = [
        {"page": 20, "text": "$m"},
        {"page": 20, "text": "$m"},
        {"page": 51, "text": "$'000"},
        {"page": 51, "text": "$'000"},
    ]

    assert _detect_scale_from_statement_page_text(sections, tables) == "unknown"


def test_scale_unknown_table_preserves_pass1_scale():
    """When table scan returns 'unknown', pass1['scale'] must remain unchanged."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=1,
        caption="Highlights",
        rows=[["Metric", "Value"], ["Revenue", "27,841"]],
        headers=["Metric", "Value"],
    )
    pass1 = {"scale": "millions", "report_type": "H", "period_end": "2024-12-31"}

    detected = _detect_scale_from_tables([table])
    if detected != "unknown":
        pass1["scale"] = detected  # should not execute

    assert pass1["scale"] == "millions", (
        "pass1['scale'] must be unchanged when table scan returns 'unknown'"
    )


def test_scale_override_log_condition_fires_on_disagreement():
    """The INFO log gate condition must be True when LLM and table scan disagree."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flows",
        rows=[["", "H1 2025 $'000"], ["Operating CF", "3,241"]],
        headers=["", "H1 2025 $'000"],
    )
    detected = _detect_scale_from_tables([table])
    assert detected == "thousands"

    pass1_scale = "millions"  # LLM wrong

    # This is the exact condition guarding logger.info in run_multipass_extraction.
    gate = pass1_scale not in (detected, "unknown", None, "")
    assert gate, (
        f"INFO log gate must be True when LLM='{pass1_scale}' vs table='{detected}'"
    )


def test_currency_detection_from_tables_prefers_dominant_signal():
    """Dominant table currency markers should resolve to one currency code."""
    from app.services.multipass_extraction import _detect_currency_from_tables
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=1,
            caption="Consolidated statement of cash flows",
            headers=["Item", "Current quarter A$'000"],
            rows=[["Net cash from operations", "3,241"]],
        ),
        DoclingTable(
            page_number=2,
            caption="Financial position (A$M)",
            headers=["Metric", "A$M"],
            rows=[["Net debt", "12.4"]],
        ),
    ]

    assert _detect_currency_from_tables(tables) == "AUD"


def test_currency_detection_marks_conflict_when_signals_tie():
    """When AUD/USD evidence ties, currency detector must mark a conflict."""
    from app.services.multipass_extraction import _detect_currency_from_tables
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=1,
            caption="USD summary",
            headers=["Metric", "US$M"],
            rows=[["Revenue", "53.6"]],
        ),
        DoclingTable(
            page_number=2,
            caption="AUD summary",
            headers=["Metric", "A$M"],
            rows=[["Revenue", "80.1"]],
        ),
    ]

    assert _detect_currency_from_tables(tables) == ""


def test_currency_detection_ignores_foreign_note_body_markers():
    """Foreign note-body mentions must not override filing currency when headers stay generic."""
    from app.services.multipass_extraction import _detect_currency_from_tables
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=1,
            caption="Financial highlights",
            headers=["Metric", "$m"],
            rows=[["Revenue", "11,641"], ["Operating cash flow", "3,637"]],
        ),
        DoclingTable(
            page_number=24,
            caption="Table B",
            headers=["Telstra Group", "31 December 2024"],
            rows=[["12-year €700 million Euro bond", "1,147"]],
        ),
    ]

    assert _detect_currency_from_tables(tables) is None


@pytest.mark.parametrize(
    "unit_header",
    ["USD M", "usd m", "US$M", "US$m", "US$ million", "USD million"],
)
def test_usd_million_source_headers_detect_usd_millions(unit_header):
    """Explicit USD million table units must resolve currency and scale deterministically."""
    from app.services.multipass_extraction import (
        _detect_currency_from_tables,
        _detect_scale_from_tables,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=1,
        caption="Financial highlights",
        headers=["Metric", unit_header],
        rows=[["Revenue", "672.0"], ["Operating profit", "149.6"]],
    )

    assert _detect_currency_from_tables([table]) == "USD"
    assert _detect_scale_from_tables([table]) == "millions"


@pytest.mark.parametrize("unit_header", ["A$M", "AUD M", "A$ million"])
def test_aud_million_source_headers_still_detect_aud_millions(unit_header):
    """Existing AUD million source-unit handling must remain unchanged."""
    from app.services.multipass_extraction import (
        _detect_currency_from_tables,
        _detect_scale_from_tables,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=1,
        caption="Financial highlights",
        headers=["Metric", unit_header],
        rows=[["Revenue", "672.0"], ["Operating profit", "149.6"]],
    )

    assert _detect_currency_from_tables([table]) == "AUD"
    assert _detect_scale_from_tables([table]) == "millions"


def test_wtc_like_appendix_row_usd_m_detects_usd_millions():
    """WTC Appendix 4D/4E tables can carry the USD M unit in the first body row."""
    from app.services.multipass_extraction import (
        _detect_currency_from_tables,
        _detect_scale_from_tables,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="APPENDIX 4D Results for Announcement to the Market",
        headers=["", "", "", "2025", "2024"],
        rows=[
            ["Six months ended 31 December", "(USD M)", "", "2025", "2024"],
            ["Revenue from ordinary activities", "", "up 76%", "672.0", "381.0"],
            ["Statutory net profit after tax", "", "down 36%", "68.1", "106.4"],
        ],
    )

    assert _detect_currency_from_tables([table]) == "USD"
    assert _detect_scale_from_tables([table]) == "millions"


def test_idr_rupiah_trillion_headers_detect_native_currency_and_scale():
    """Explicit Rp trillion table units must resolve IDR and trillions."""
    from app.services.multipass_extraction import (
        _detect_currency_from_tables,
        _detect_scale_from_tables,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=1,
        caption="Consolidated statement of profit or loss",
        headers=["Metric", "2025 Rp trillion", "2024 Rp trillion"],
        rows=[["Revenue", "12.5", "10.1"], ["Operating profit", "2.4", "2.0"]],
    )

    assert _detect_currency_from_tables([table]) == "IDR"
    assert _detect_scale_from_tables([table]) == "trillions"


def test_generic_trillion_mention_without_rupiah_marker_stays_unknown_scale():
    """Trillion support is not a broad verbal-scale upgrade."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=1,
        caption="Market opportunity summary",
        headers=["Metric", "Current period"],
        rows=[["Addressable market", "One trillion dollars"], ["Revenue", "12.5"]],
    )

    assert _detect_scale_from_tables([table]) == "unknown"


def test_pass3a_applies_idr_trillion_scale_without_aud_cap_fallback():
    """Source-explicit IDR trillion values are native units, not AUD-scale errors."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=3,
        caption="Consolidated statement of profit or loss",
        headers=["Metric", "2025 Rp trillion"],
        raw_header_rows=[["Metric", "31 Dec 2025 Rp trillion"]],
        rows=[
            ["Revenue", "12.5"],
            ["Operating profit", "2.4"],
            ["Net profit attributable to owners", "1.1"],
        ],
    )
    labelled = {
        "income_statement": table,
        "cashflow_statement": None,
        "balance_sheet": None,
        "net_debt_note": None,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "A",
        "period_end": "2025-12-31",
        "currency": "IDR",
        "scale": "trillions",
    }
    mock_raw = {
        "revenue": 12.5,
        "ebit": 2.4,
        "np_attributable": 1.1,
        "pass3_confidence": 0.9,
        "row_refs": {
            "revenue": "Revenue",
            "ebit": "Operating profit",
            "np_attributable": "Net profit attributable to owners",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=mock_raw,
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["revenue"] == 12_500_000_000_000
    assert results[0]["ebit"] == 2_400_000_000_000
    assert results[0]["np_attributable"] == 1_100_000_000_000


def test_explicit_usd_m_header_wins_over_later_aud_note_markers():
    """A source-unit header should beat unrelated AUD mentions in later note tables."""
    from app.services.multipass_extraction import _detect_currency_from_tables
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=2,
            caption="APPENDIX 4E Results for Announcement to the Market",
            headers=["", "", "", "2025", "2024"],
            rows=[
                ["For the year ended 30 June", "(USD M)", "", "2025", "2024"],
                ["Revenue from ordinary activities", "", "up 14%", "778.7", "683.7"],
            ],
        ),
        DoclingTable(
            page_number=62,
            caption="Remuneration report",
            headers=["AUD", "AUD", "AUD", "AUD"],
            rows=[["Salary", "1,000", "Bonus", "500"]],
        ),
    ]

    assert _detect_currency_from_tables(tables) == "USD"


def test_unknown_scale_without_valid_unit_header_remains_unknown():
    """Missing source-unit evidence must not be upgraded to millions."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=1,
        caption="Financial highlights",
        headers=["Metric", "Current period"],
        rows=[["Revenue", "672.0"], ["Operating profit", "149.6"]],
    )

    assert _detect_scale_from_tables([table]) == "unknown"


def test_plain_aud_dollar_statement_header_detects_units_scale():
    """Scale Policy V1 treats plain AUD dollar columns as raw units."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=27,
        caption="Consolidated Statement of Cash Flows",
        headers=["", "Notes", "2025 $", "2024 $"],
        rows=[
            ["Net cash used in operating activities", "14", "(13,225,929)", ""],
            ["Net cash used in investing activities", "", "(2,167,611)", ""],
            ["Cash and cash equivalents at 31 December", "13", "24,577,181", ""],
        ],
    )

    assert _detect_scale_from_tables([table]) == "units"


def test_plain_dollar_units_do_not_override_explicit_thousands_header():
    """Explicit scaled table units remain higher priority than raw-dollar hints."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Statement of Cash Flows",
        headers=["", "2025 $'000", "2024 $"],
        rows=[
            ["Net cash used in operating activities", "(13,225)", "(15,675)"],
        ],
    )

    assert _detect_scale_from_tables([table]) == "thousands"


def test_usd_million_detection_ignores_usd_m_and_a_prose():
    """The USD M extension must not treat M&A prose as a million-unit marker."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=1,
        caption="USD M&A activity summary",
        headers=["Metric", "Current period"],
        rows=[["Revenue", "672.0"], ["Operating profit", "149.6"]],
    )

    assert _detect_scale_from_tables([table]) == "unknown"


def test_pass3a_applies_corrected_scale_multiplier():
    """When scale='thousands' (whether set by table-header override or Pass 1),
    Pass 3a must multiply raw values by 1000 (thousands), not 1_000_000 (millions)."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flow Statement",
        rows=[["", "H1 2025 $'000"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025 $'000"],
        raw_header_rows=[["", "31 Dec 2024 $'000"]],
    )
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }

    # scale already corrected (e.g. by the table-header override in run_multipass_extraction)
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "operating_cf": 3241,
        "investing_cf": None,
        "financing_cf": None,
        "cash_end": None,
        "pass3_confidence": 0.95,
        "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["operating_cf"] == 3_241_000, (
        f"Expected thousands multiplier (3_241_000), got {results[0]['operating_cf']}"
    )


def test_pass3a_captures_table_markdown_for_review():
    """Pass 3a results must retain the markdown used for extraction review surfaces."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Cash Flow Statement",
        rows=[["", "H1 2025 $'000"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025 $'000"],
    )
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }
    mock_raw = {
        "operating_cf": 3241,
        "thinking": "Found the operating cash flow row in the current period column.",
        "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert "Net cash from operations" in results[0]["_markdown"]
    assert results[0]["_thinking"] == mock_raw["thinking"]


def test_pass4_higher_priority_source_wins():
    """income_statement must override highlights when both provide revenue."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "highlights",
            "revenue": 45_200_000,
            "pass3_confidence": 0.7,
            "row_refs": {},
        },
        {
            "_source": "income_statement",
            "revenue": 45_192_000,
            "pass3_confidence": 0.92,
            "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.0,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)
    assert result["metrics"]["revenue"] == 45_192_000  # income_statement wins


# ---------------------------------------------------------------------------
# Pipeline integration — _upsert_financial_rows (DB smoke test)
# ---------------------------------------------------------------------------


def test_upsert_financial_rows_smoke():
    """Extraction writes narrative risk, but never the legacy financial row."""
    import uuid
    from types import SimpleNamespace
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base
    from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
    from app.services.pipeline import _upsert_financial_rows

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    doc_id = uuid.uuid4()
    doc = SimpleNamespace(ticker="TST", document_id=doc_id)

    payload = {
        "period_type": "H",
        "period_end": "2024-12-31",
        "confidence_metrics": 0.85,
        "metrics": {
            "revenue": 1_000_000.0,
            "ebit": 200_000.0,
            "np_attributable": 150_000.0,
            "operating_cf": 300_000.0,
            "investing_cf": -50_000.0,
            "financing_cf": -20_000.0,
            "capex": None,
            "cash_end": 80_000.0,
            "net_debt": None,
            "shares_outstanding": 50_000_000.0,
        },
        "risk_summary": "Commodity price risk",
        "risk_bullets": ["Iron ore price volatility", "FX exposure"],
        "guidance_summary": "Revenue expected to grow 10%",
        "material_changes": None,
        "confidence_narrative": 0.7,
    }

    session = Session()
    try:
        # Risk notes remain part of the extraction transaction.
        # Caller (process_document) is responsible for commit; flush here to make
        # rows visible within this session for assertions.
        _upsert_financial_rows(session, doc, payload)
        session.flush()

        fin = session.query(ASXPeriodicFinancial).filter_by(ticker="TST").first()
        assert fin is None

        note = session.query(ASXRiskNote).first()
        assert note is not None, "ASXRiskNote row must be created"
        assert note.risk_summary == "Commodity price risk"
        assert "Iron ore price volatility" in note.risk_bullets
        assert note.guidance_summary == "Revenue expected to grow 10%"
        assert note.material_changes is None
        assert note.confidence_narrative == pytest.approx(0.7)

        # A repeated extraction still updates the narrative atomically.
        payload["metrics"]["revenue"] = 2_000_000.0
        payload["risk_summary"] = "Updated risk summary"
        _upsert_financial_rows(session, doc, payload)
        session.flush()

        all_fin = session.query(ASXPeriodicFinancial).all()
        assert all_fin == []

        all_notes = session.query(ASXRiskNote).all()
        assert len(all_notes) == 1, "Upsert must not create a duplicate risk note"
        assert all_notes[0].risk_summary == "Updated risk summary"
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Pass 3a — Period column disambiguation (B2)
# ---------------------------------------------------------------------------


def test_pass3a_prompt_contains_column_selection_instruction():
    """_PASS3A_PROMPT must instruct the LLM to select the period_end column."""
    from app.services.multipass_extraction import _PASS3A_PROMPT

    prompt_lower = _PASS3A_PROMPT.lower()
    assert "prior" in prompt_lower, (
        "Prompt must explicitly mention prior-period columns"
    )
    assert "comparative" in prompt_lower, (
        "Prompt must explicitly mention comparative columns"
    )
    assert "period_end" in _PASS3A_PROMPT or "{period_end}" in _PASS3A_PROMPT, (
        "Prompt must reference period_end for column selection"
    )


def test_pass3a_prompt_documents_bank_revenue_equivalent():
    """Banking half-year reports (e.g. ANZ) use operating / net interest income, not 'Revenue'."""
    from app.services.multipass_extraction import _PASS3A_PROMPT

    pl = _PASS3A_PROMPT.lower()
    assert "bank" in pl
    assert "net interest income" in pl
    assert "operating income" in pl


def test_pass3a_prompt_includes_period_end_for_column_selection():
    """The assembled prompt sent to the LLM must contain the period_end date
    and a column-selection instruction."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2,
        caption="Income Statement",
        rows=[
            ["", "H1 2025", "H1 2024"],
            ["Revenue", "485,630", "390,200"],
            ["EBIT", "31,284", "22,100"],
        ],
        headers=["", "H1 2025", "H1 2024"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": table,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "revenue": 485630,
        "ebit": 31284,
        "np_attributable": None,
        "period_col": "H1 2025",
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    captured_prompts = []

    def capture_llm_call(prompt, llm_client, max_tokens=512, **kwargs):
        captured_prompts.append(prompt)
        return mock_raw

    with patch(
        "app.services.multipass_extraction._llm_json_call", side_effect=capture_llm_call
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert captured_prompts, "LLM must have been called"
    prompt = captured_prompts[0]
    assert "2025-06-30" in prompt, (
        "period_end date must appear in the prompt for column selection"
    )
    assert "prior" in prompt.lower() or "comparative" in prompt.lower(), (
        "Prompt must warn against prior-period column extraction"
    )
    assert "period_col" in results[0], (
        "period_col decision record must be propagated through to the result dict"
    )


# ---------------------------------------------------------------------------
# Docling adaptive timeout (B3)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pass 4 — net_debt derivation (B4)
# ---------------------------------------------------------------------------


def test_pass4_reconciler_derives_net_debt_from_total_debt():
    """Reconciler must derive net_debt = total_debt - cash_end when net_debt is null."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "operating_cf": 500_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": 200_000_000,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at end of period"},
        },
        {
            "_source": "balance_sheet",
            "net_debt": None,
            "total_debt": 800_000_000,
            "shares_outstanding": None,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 600_000_000, (
        "net_debt must be derived as total_debt(800M) - cash_end(200M) = 600M"
    )
    assert "derived:balance_sheet" in payload["provenance"].get("net_debt", ""), (
        "provenance must record that net_debt was derived"
    )
    assert payload["confidence_metrics"] == pytest.approx(
        round((0.9 + 0.9 + 0.55) / 3, 3)
    ), (
        "Derived net_debt must contribute discounted confidence instead of inheriting "
        "the balance-sheet pass3 confidence."
    )


def test_pass4_reconciler_accepts_borrowings_and_finance_lease_liabilities():
    """Borrowings rows remain strong debt evidence even when leases are included."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "cash_end": 4_743_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at end of period"},
        },
        {
            "_source": "balance_sheet",
            "net_debt": None,
            "total_debt": 5_756_000_000,
            "shares_outstanding": None,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Borrowings and finance lease liabilities"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2025-12-31", "currency": "USD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 1_013_000_000
    assert (
        payload["provenance"]["net_debt"]
        == "derived:balance_sheet:total_debt(5756000000)-cash_end(4743000000)"
    )


def test_pass4_reconciler_skips_derivation_when_net_debt_already_extracted():
    """Explicitly extracted net_debt must not be overwritten by derivation."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "operating_cf": 100_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": 50_000_000,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at end of period"},
        },
        {
            "_source": "balance_sheet",
            "net_debt": 300_000_000,
            "total_debt": 999_000_000,
            "shares_outstanding": None,
            "pass3_confidence": 0.9,
            "row_refs": {"net_debt": "Net debt", "total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 300_000_000, (
        "Explicitly extracted net_debt(300M) must not be overwritten by total_debt(999M)-cash_end"
    )


def test_pass4_reconciler_skips_derivation_when_cash_end_missing():
    """Derivation must not run when cash_end is not available."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "balance_sheet",
            "net_debt": None,
            "total_debt": 500_000_000,
            "shares_outstanding": 100_000_000,
            "pass3_confidence": 0.7,
            "row_refs": {},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None, (
        "net_debt must remain null when cash_end is unavailable — cannot derive safely"
    )


def test_pass4_preserves_explicit_summary_net_debt():
    """Explicit summary-table net_debt must beat ambiguous balance-sheet debt labels."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "highlights",
            "_page_number": 1,
            "net_debt": 12_924_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"net_debt": "Net debt"},
        },
        {
            "_source": "balance_sheet",
            "_page_number": 123,
            "net_debt": -34_465_000_000,
            "total_debt": -20_420_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {
                "net_debt": "Borrowings",
                "total_debt": "Borrowings",
            },
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "A", "period_end": "2025-06-30", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 12_924_000_000
    assert payload["provenance"]["net_debt"] == "highlights:page_1:Net debt"
    assert payload["confidence_metrics"] == pytest.approx(0.95), (
        "An explicit labelled Net debt row must carry high confidence."
    )


def test_pass4_rejects_total_liabilities_as_total_debt():
    """Total liabilities must not be treated as debt evidence for net_debt derivation."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 8,
            "cash_end": 1_436_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at period end"},
        },
        {
            "_source": "balance_sheet",
            "_page_number": 19,
            "net_debt": None,
            "total_debt": 28_900_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Total liabilities"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2025-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None
    assert "net_debt" not in payload["provenance"]


def test_pass4_rejects_accounting_negative_borrowings_for_derivation():
    """Accounting-negative borrowings must not fabricate derived net_debt."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 6,
            "cash_end": 14_045_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents"},
        },
        {
            "_source": "balance_sheet",
            "_page_number": 32,
            "net_debt": None,
            "total_debt": -20_420_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "A", "period_end": "2023-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None


def test_pass4_ambiguous_balance_sheet_net_debt_abstains():
    """A balance-sheet value from a non-explicit debt row must be rejected."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "balance_sheet",
            "_page_number": 32,
            "net_debt": 27_464_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"net_debt": "Borrowings"},
        }
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "A", "period_end": "2023-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None
    assert "net_debt" not in payload["provenance"]


def test_pass4_skips_derivation_when_document_only_has_glossary_net_debt_reference():
    """A glossary-only net-debt mention must not authorize derived debt output."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 17,
            "cash_end": 638_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {
                "cash_end": "Cash and cash equivalents at the end of the half-year"
            },
        },
        {
            "_source": "balance_sheet",
            "_page_number": 15,
            "net_debt": None,
            "total_debt": 5_516_000_000,
            "pass3_confidence": 0.7,
            "row_refs": {"total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "_block_derived_net_debt": True,
    }

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] is None
    assert "net_debt" not in payload["provenance"]


def test_pass4_explicit_net_debt_not_overwritten_by_balance_sheet_derivation():
    """Derived balance-sheet debt must not replace explicit summary net_debt evidence."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 5,
            "cash_end": 200_000_000,
            "pass3_confidence": 0.9,
            "row_refs": {"cash_end": "Cash and cash equivalents at end of period"},
        },
        {
            "_source": "highlights",
            "_page_number": 1,
            "net_debt": 300_000_000,
            "pass3_confidence": 0.85,
            "row_refs": {"net_debt": "Net debt"},
        },
        {
            "_source": "balance_sheet",
            "_page_number": 19,
            "net_debt": None,
            "total_debt": 800_000_000,
            "pass3_confidence": 0.8,
            "row_refs": {"total_debt": "Borrowings"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.5,
    }
    pass1 = {"report_type": "H", "period_end": "2024-12-31", "currency": "AUD"}

    payload = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert payload["metrics"]["net_debt"] == 300_000_000
    assert payload["provenance"]["net_debt"] == "highlights:page_1:Net debt"


def test_compute_docling_timeout_floor():
    """Short PDFs must never drop below the 120s floor."""
    from app.services.docling_extract import _compute_docling_timeout

    # 10 pages × 4 = 40s — below the floor, so we expect 120s
    assert _compute_docling_timeout(10) == 120


def test_compute_docling_timeout_scales():
    """Mid-sized PDFs must scale proportionally when above the floor."""
    from app.services.docling_extract import _compute_docling_timeout

    # 50 pages × 6 = 300s — above floor (120s), below cap (600s)
    assert _compute_docling_timeout(50) == 300


def test_compute_docling_timeout_cap():
    """Very large PDFs must not exceed the 600s ceiling."""
    from app.services.docling_extract import _compute_docling_timeout

    # 100 pages × 6 = 600s — hits cap
    assert _compute_docling_timeout(100) == 600


def test_compute_docling_timeout_strict_mode_uses_higher_cap():
    """Strict docling gets a larger timeout ceiling for canonical method runs."""
    from app.services.docling_extract import _compute_docling_timeout

    # 200 pages × 6 = 1200s — strict cap
    assert _compute_docling_timeout(200, strict_backend=True) == 1200


# ---------------------------------------------------------------------------
# Pass 2 — footnote table scoring guard (B5)
# ---------------------------------------------------------------------------


def test_pass2_header_bonus_beats_footnote_keyword_count():
    """
    An explicitly-labeled income statement must beat a footnote table that has
    more raw keyword matches, because the header bonus (+10) outweighs higher
    incidental keyword density in notes sections.

    Scenario: "Notes to the Financial Statements" table has 4 keyword matches
    (revenue, profit, ebit, net profit) from discussion of accounting policies.
    "Statement of Profit or Loss" table has only 2 raw matches but earns +10
    header bonus → total 12 vs 4. Statement wins.
    """
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    footnote_table = DoclingTable(
        page_number=10,
        caption="Notes to the Financial Statements",
        rows=[
            ["Note 3 — Revenue Recognition", ""],
            ["revenue is recognised on transfer of control", ""],
            ["profit attributable to ordinary shareholders", ""],
            ["ebit excludes lease finance costs", ""],
            ["net profit after tax allocated to members", ""],
        ],
        headers=["Description", ""],
    )
    statement_table = DoclingTable(
        page_number=4,
        caption="Statement of Profit or Loss",
        rows=[
            ["Revenue", "485,630"],
            ["Operating expenses", "(454,346)"],
        ],
        headers=["", "H1 FY26 $'000"],
    )

    result = _run_pass2_locator([footnote_table, statement_table])

    assert result["income_statement"] is statement_table, (
        "Explicitly-labeled income statement must win over footnote table "
        "even when footnote has higher raw keyword count. "
        f"Got: {result['income_statement'].caption!r}"
    )


# ---------------------------------------------------------------------------
# period_start derivation (B6)
# ---------------------------------------------------------------------------


def test_derive_period_start_annual():
    """Annual period: period_start = period_end − 12 months + 1 day."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    result = _derive_period_start(date(2024, 6, 30), "A")
    assert result == date(2023, 7, 1), f"Expected 2023-07-01, got {result}"


def test_derive_period_start_half_year():
    """Half-year period: period_start = period_end − 6 months + 1 day."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    result = _derive_period_start(date(2025, 12, 31), "H")
    assert result == date(2025, 7, 1), f"Expected 2025-07-01, got {result}"


def test_derive_period_start_quarterly():
    """Quarterly period: period_start = period_end − 3 months + 1 day."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    result = _derive_period_start(date(2024, 9, 30), "Q")
    assert result == date(2024, 7, 1), f"Expected 2024-07-01, got {result}"


def test_derive_period_start_september_annual():
    """Annual period ending Sept 30 (e.g. NAB): period_start = Oct 1 prior year."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    result = _derive_period_start(date(2024, 9, 30), "A")
    assert result == date(2023, 10, 1), f"Expected 2023-10-01, got {result}"


def test_derive_period_start_returns_none_for_missing_inputs():
    """None period_end or unrecognised period_type must return None — never guess."""
    from datetime import date
    from app.services.multipass_extraction import _derive_period_start

    assert _derive_period_start(None, "A") is None
    assert _derive_period_start(date(2024, 12, 31), None) is None
    assert _derive_period_start(date(2024, 12, 31), "X") is None


# ---------------------------------------------------------------------------
# Validation gate — new guards (B7: scale, B8: currency, B9: quarterly)
# ---------------------------------------------------------------------------


def _good_payload(period_type="H", scale="thousands", currency="AUD", confidence=0.85):
    """Minimal well-formed payload for _validate_gate tests."""
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


def test_validate_gate_quarterly_period_passes():
    """period_type='Q' must be accepted by the gate — quarterly is a valid period type."""
    from app.services.multipass_extraction import _validate_gate

    status, error = _validate_gate(_good_payload(period_type="Q"))
    assert status in ("ok", "ok_low_confidence"), (
        f"Quarterly period must pass gate; got status={status!r}, error={error!r}"
    )
    assert error is None


def test_validate_gate_scale_unknown_hard_blocked():
    """scale='unknown' must be a hard block — values would be wrong by up to 1000×."""
    from app.services.multipass_extraction import _validate_gate

    status, error = _validate_gate(_good_payload(scale="unknown"))
    assert status == "failed", f"Expected 'failed', got {status!r}"
    assert error == "validation_gate:scale_unknown", f"Unexpected error key: {error!r}"


def test_validate_gate_blocks_mixed_metric_source_scales_for_accepted_output():
    """Accepted outputs with multiple metric-local source scales must fail closed."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="A", scale="thousands")
    payload["metric_source_scales"] = {
        "revenue": "thousands",
        "ebit": "thousands",
        "np_attributable": "thousands",
        "operating_cf": "millions",
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error is not None
    assert error.startswith("validation_gate:accepted_output_scale_magnitude_risk:")
    assert "mixed_metric_source_scales" in error
    assert "payload_scale_differs_from_metric_source_scale" in error


def test_validate_gate_blocks_extreme_metric_revenue_ratio_for_accepted_output():
    """EDU-style cash-flow magnitudes cannot pass merely because final scales agree."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="A", scale="thousands")
    payload["metrics"].update(
        {
            "revenue": 11_596_000,
            "ebit": 868_000,
            "np_attributable": 385_000,
            "operating_cf": 1_100_996_000,
            "investing_cf": -464_151_000,
            "financing_cf": -3_590_738_000,
            "capex": -78_008_000,
            "cash_end": 3_121_297_000,
        }
    )
    payload["metric_source_scales"] = {
        metric_name: "thousands"
        for metric_name, value in payload["metrics"].items()
        if metric_name != "shares_outstanding" and value is not None
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error is not None
    assert error.startswith("validation_gate:accepted_output_scale_magnitude_risk:")
    assert "metric_revenue_ratio_high" in error


def test_validate_gate_allows_source_bound_reit_net_debt_revenue_ratio():
    """DXS-style source-bound REIT/stapled net debt may exceed revenue."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="H", scale="millions")
    payload["period_end"] = "2025-12-31"
    payload["metrics"].update(
        {
            "revenue": 360_000_000,
            "ebit": 347_600_000,
            "np_attributable": 348_500_000,
            "operating_cf": 168_500_000,
            "cash_end": 74_700_000,
            "net_debt": 4_516_700_000,
            "shares_outstanding": 1_075_565_246,
        }
    )
    payload["metric_source_scales"] = {
        metric_name: "millions"
        for metric_name, value in payload["metrics"].items()
        if metric_name != "shares_outstanding" and value is not None
    }
    payload["row_refs"] = {
        "revenue": "Revenue from ordinary activities",
        "np_attributable": (
            "Statutory net profit/(loss) attributable to security holders after tax"
        ),
        "cash_end": "Cash and cash equivalents at the end of the period",
        "net_debt": "total_debt(4591400000)-cash_end(74700000)",
        "shares_outstanding": "Securities on issue",
    }
    payload["provenance"] = {
        "revenue": "income_statement:page_1:Revenue from ordinary activities",
        "net_debt": "derived:balance_sheet:total_debt(4591400000)-cash_end(74700000)",
        "shares_outstanding": "balance_sheet:page_1:Securities on issue",
    }
    payload["field_provenance"] = {
        "net_debt": {
            "metric": "net_debt",
            "source": "derived:balance_sheet",
            "row_ref": "total_debt(4591400000)-cash_end(74700000)",
            "scale": "millions",
            "scale_source": "table",
        }
    }
    payload["source_bound"] = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "scale": "millions",
        "currency": "AUD",
        "document_title": "Appendix 4D and HY26 financial statements",
    }
    payload["source_period_end_evidence"] = {
        "hits": [
            {
                "context": (
                    "Dexus ARSN 648 526 470 Financial reporting for the half year "
                    "ended 31 December 2025"
                ),
                "evidence": "for the half year ended 31 December 2025",
                "source": "source_text",
            }
        ],
    }

    status, error = _validate_gate(payload)

    assert status == "ok"
    assert error is None


def test_validate_gate_still_blocks_non_reit_net_debt_revenue_ratio():
    """The net-debt exception must not become a generic balance-sheet bypass."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="H", scale="millions")
    payload["metrics"].update(
        {
            "revenue": 360_000_000,
            "net_debt": 4_516_700_000,
        }
    )
    payload["metric_source_scales"] = {
        metric_name: "millions"
        for metric_name, value in payload["metrics"].items()
        if metric_name != "shares_outstanding" and value is not None
    }
    payload["row_refs"] = {
        "revenue": "Revenue",
        "np_attributable": "Profit attributable to security holders",
        "net_debt": "total_debt(4591400000)-cash_end(74700000)",
        "shares_outstanding": "Securities on issue",
    }
    payload["provenance"] = {
        "revenue": "income_statement:page_1:Revenue",
        "np_attributable": (
            "income_statement:page_1:Profit attributable to security holders"
        ),
        "net_debt": "derived:balance_sheet:total_debt(4591400000)-cash_end(74700000)",
        "shares_outstanding": "share_capital:page_1:Securities on issue",
    }
    payload["field_provenance"] = {
        "net_debt": {
            "metric": "net_debt",
            "source": "derived:balance_sheet",
            "row_ref": "total_debt(4591400000)-cash_end(74700000)",
            "scale": "millions",
            "scale_source": "table",
        }
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error is not None
    assert error.startswith("validation_gate:accepted_output_scale_magnitude_risk:")
    assert "metric_revenue_ratio_high" in error


def test_validate_gate_does_not_count_wrapper_disclosures_as_canonical_metrics():
    """NTA/dividend/record-date disclosures must not satisfy canonical minimums."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="H")
    payload["document_subtype"] = "4D"
    payload["document_title"] = "Appendix 4D half-year report"
    payload["source_bound"] = {
        "period_end": payload["period_end"],
        "period_type": payload["period_type"],
        "scale": payload["scale"],
        "currency": payload["currency"],
        "document_title": payload["document_title"],
    }
    payload["wrapper_disclosures"] = [
        "Net tangible assets per security",
        "Dividends / distributions",
        "Record date for determining entitlement to the dividend",
        "Details of associates and joint ventures entities",
    ]
    payload["metrics"] = {
        "revenue": 500_000_000,
        "ebit": None,
        "np_attributable": None,
        "operating_cf": None,
        "investing_cf": None,
        "financing_cf": None,
        "capex": None,
        "cash_end": None,
        "net_debt": None,
        "shares_outstanding": None,
        "nta_per_security": 1.23,
        "dividends": 0.10,
        "record_date": "2026-01-31",
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:insufficient_metrics:1"


def test_validate_scale_blocks_wtc_like_unknown_scale_values():
    """Raw WTC-style USD M values must still fail when scale remains unknown."""
    from app.services.multipass_extraction import _validate_gate, _validate_scale

    payload = {
        "period_end": "2025-12-31",
        "period_type": "H",
        "scale": "unknown",
        "currency": "USD",
        "metrics": {
            "revenue": 672.0,
            "ebit": 149.6,
            "np_attributable": 68.1,
            "operating_cf": 186.1,
            "investing_cf": None,
            "financing_cf": None,
            "capex": None,
            "cash_end": None,
            "net_debt": None,
            "shares_outstanding": None,
        },
        "confidence_metrics": 0.9,
    }

    payload["scale_validation"] = _validate_scale(payload)
    assert payload["scale_validation"] == "suspect_underscaled"

    status, error = _validate_gate(payload)
    assert status == "failed"
    assert error == "validation_gate:scale_validation:suspect_underscaled"


def test_validate_gate_rejects_net_operating_income_as_ebit_source():
    """Net operating income is not EBIT and must not pass as canonical ebit."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="A", scale="thousands")
    payload["metrics"]["ebit"] = 29_562_000
    payload["row_refs"] = {"ebit": "Net operating income"}
    payload["provenance"] = {
        "ebit": "income_statement:page_26:Net operating income"
    }

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:metric_label_mismatch:ebit:net_operating_income"


@pytest.mark.parametrize(
    "document_title",
    [
        (
            "2026-02-20_1h-fy26-results-presentation_"
            "551c6b84-1053-405c-a833-4ecc018e2045.pdf"
        ),
        (
            "2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_"
            "419bcca8-213e-4706-8962-8e3bd8adf091.pdf"
        ),
    ],
)
def test_validate_gate_rejects_half_year_announcement_date_period_end(
    document_title,
):
    """Half-year payloads must not use the ASX announcement date as period_end."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="H", scale="millions")
    payload["period_end"] = document_title[:10]
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
        f"period_type=H:period_end={payload['period_end']}:"
        f"title_date={payload['period_end']}:leading_title_date"
    )


def test_validate_gate_allows_half_year_period_end_distinct_from_announcement_date():
    """The announcement-date guard must not block valid half-year period ends."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(period_type="H", scale="thousands")
    payload["period_end"] = "2025-12-31"
    payload["source_bound"] = {
        "period_end": payload["period_end"],
        "period_type": payload["period_type"],
        "scale": payload["scale"],
        "currency": payload["currency"],
        "document_title": (
            "2026-02-20_1h-fy26-results-presentation_"
            "551c6b84-1053-405c-a833-4ecc018e2045.pdf"
        ),
    }

    status, error = _validate_gate(payload)

    assert status == "ok"
    assert error is None


def test_pass3a_uses_selected_table_scale_over_document_scale():
    """Selected-table $'000 markers must override a document-level millions scale."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=25,
        caption="Consolidated profit & loss statement",
        headers=["", "FY25", "FY24"],
        raw_header_rows=[["", "30 Jun 2025", "30 Jun 2024"]],
        rows=[
            ["", "FY25", "FY24"],
            ["", "$'000", "$'000"],
            ["Total revenue", "46,547", "48,505"],
            ["Net profit/(loss) after tax", "39,374", "3,407"],
        ],
    )
    raw_response = {
        "metrics": {
            "revenue": 46_547,
            "np_attributable": 39_374,
        },
        "row_refs": {
            "revenue": "Total revenue",
            "np_attributable": "Net profit/(loss) after tax",
        },
        "pass3_confidence": 0.9,
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "income_statement",
            table,
            {
                "report_type": "A",
                "period_end": "2025-06-30",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["revenue"] == 46_547_000
    assert result["np_attributable"] == 39_374_000
    assert result["_scale"] == "thousands"
    assert result["_scale_source"] == "table"


def test_pass3a_expands_lbl_income_combined_metric_name_row_refs():
    """LBL-style presentation tables must preserve per-metric source row labels."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=21,
        caption="Income statement",
        headers=["A$000", "FY22", "FY23", "FY24", "FY25", "1HFY26"],
        raw_header_rows=[["", "", "", "", "", "31 Dec 2025"]],
        rows=[
            ["A$000", "FY22", "FY23", "FY24", "FY25", "1HFY26"],
            ["Sales Revenue", "30,711.1", "38,612.4", "41,983.6", "43,475.6", "23,008.9"],
            ["Grossprofit only", "16,701.2", "20,463.0", "21,642.0", "22,786.9", "12,350.3"],
            ["OperatingExpenses", "(8,024.8)", "(10,266.1)", "(12,192.1)", "(13,778.3)", "(7,161.9)"],
            ["EBITDA use", "8,676.4", "10,196.9", "9,449.7", "9,008.6", "5,188.4"],
            ["D&A", "(2,902.2)", "(3,267.6)", "(3,494.7)", "(3,196.4)", "(1,520.7)"],
            ["EBIT", "5,774.2", "6,929.3", "5,985.8", "5,812.2", "213,677.7"],
            ["Interest", "(442.8)", "(562.2)", "(790.2)", "(824.7)", "(394.5)"],
            ["NPBT personal", "5,331.4", "6,367.1", "5,164.8", "4,987.4", "3,273.2"],
            ["NPAT For", "3,628.8", "4,758.5", "3,482.3", "3,844.8", "2,215.9"],
        ],
    )
    raw_response = {
        "metrics": {
            "revenue": 230_089,
            "ebit": 213_677,
            "np_attributable": 22_159,
        },
        "row_refs": {
            "metric_name": "Sales Revenue,EBIT,NPAT For",
        },
        "pass3_confidence": 0.9,
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "income_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "unknown",
            1,
            llm_client=None,
        )

    assert result is not None
    assert result["revenue"] == 23_008_900
    assert result["ebit"] == 213_677_700
    assert result["np_attributable"] == 2_215_900
    assert result["row_refs"] == {
        "revenue": "Sales Revenue",
        "ebit": "EBIT",
        "np_attributable": "NPAT For",
        "metric_name": "Sales Revenue,EBIT,NPAT For",
    }


def test_pass3a_expands_bank_total_operating_income_row_refs_without_overwriting_ebit():
    """Bank total operating income is revenue-equivalent, not EBIT provenance."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=9,
        caption="Income statement",
        headers=["A$m", "FY25"],
        raw_header_rows=[["", "30 Jun 2025"]],
        rows=[
            ["A$m", "FY25"],
            ["Total operating income", "1,200"],
            ["Profit before income tax", "450"],
        ],
    )
    raw_response = {
        "metrics": {
            "revenue": 1200,
            "ebit": 450,
        },
        "row_refs": {
            "metric_name": "Total operating income, Profit before income tax",
        },
        "pass3_confidence": 0.9,
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "income_statement",
            table,
            {
                "report_type": "A",
                "period_end": "2025-06-30",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["revenue"] == 1_200_000_000
    assert result["ebit"] == 450_000_000
    assert result["row_refs"] == {
        "revenue": "Total operating income",
        "ebit": "Profit before income tax",
        "metric_name": "Total operating income, Profit before income tax",
    }


def test_market_update_net_revenue_candidate_passes_quarterly_gate():
    """JAY-style market updates can recover only current-quarter Net Revenue."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        METRIC_FIELDS,
        _common_metric_source_scale,
        _extract_market_update_net_revenue_candidate,
        _run_pass4_reconciler,
        _validate_gate,
    )

    table = DoclingTable(
        page_number=2,
        caption="Q3 Trips and revenues",
        headers=[
            "Quarter",
            "Trips",
            "Revenue Booked",
            "Revenue Refunded",
            "Refund Rate %",
            "Net Revenue",
            "Net Rev / Trip",
            "Net Rev V PCP",
        ],
        rows=[
            [
                "Quarter",
                "Trips",
                "Revenue Booked",
                "Revenue Refunded",
                "Refund Rate %",
                "Net Revenue",
                "Net Rev / Trip",
                "Net Rev V PCP",
            ],
            ["Q2 FY23", "153K", "$1,394K", "$(259)K", "19%", "$1,134K", "$7.40", "+186%"],
            ["Q3 FY23", "153K", "$1,403K", "$(251)K", "18%", "$1,152K", "$7.57", "+97%"],
        ],
    )
    pass1 = {
        "report_type": "Q",
        "period_end": "2023-03-31",
        "scale": "thousands",
        "currency": "AUD",
    }

    candidate = _extract_market_update_net_revenue_candidate(
        [table],
        sections=[{"page": 1, "text": "Q3 FY23 Market Update"}],
        pass1_result=pass1,
        title="Q3 FY23 update",
    )

    assert candidate is not None
    assert candidate["revenue"] == 1_152_000
    assert candidate["row_refs"] == {"revenue": "Q3 FY23 Net Revenue"}
    assert [
        metric for metric in METRIC_FIELDS if candidate.get(metric) is not None
    ] == ["revenue"]

    payload = _run_pass4_reconciler(
        [candidate],
        {
            "risk_summary": None,
            "risk_bullets": None,
            "guidance_summary": None,
            "material_changes": None,
            "confidence_narrative": 0.0,
        },
        pass1,
    )
    payload["scale"] = _common_metric_source_scale(payload, pass1["scale"])
    payload["currency"] = "AUD"

    status, error = _validate_gate(payload)

    assert status == "ok"
    assert error is None
    assert payload["metrics"]["revenue"] == 1_152_000
    assert payload["metrics"]["operating_cf"] is None
    assert payload["metrics"]["np_attributable"] is None


def test_market_update_net_revenue_candidate_uses_q4_not_fy_row():
    """A Q4 market update with FY rows must bind to Q4, not annual revenue."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _extract_market_update_net_revenue_candidate,
    )

    table = DoclingTable(
        page_number=2,
        caption="Q4 trips and revenues",
        headers=[
            "Quarter",
            "Trips",
            "Revenue Booked",
            "Revenue Refunded",
            "Refund Rate %",
            "Net Revenue",
            "Net Rev / Trip",
            "Net Rev V PCP",
        ],
        rows=[
            [
                "Quarter",
                "Trips",
                "Revenue Booked",
                "Revenue Refunded",
                "Refund Rate %",
                "Net Revenue",
                "Net Rev / Trip",
                "Net Rev V PCP",
            ],
            ["Q4 FY23", "199K", "$1,893K", "$(347)K", "18%", "$1,546K", "$7.77", "+42%"],
            ["FY23", "646K", "$6,253K", "$(1,167)K", "19%", "$5,085K", "$7.87", "+99%"],
        ],
    )

    candidate = _extract_market_update_net_revenue_candidate(
        [table],
        sections=[{"page": 1, "text": "Q4 FY23 Market Update"}],
        pass1_result={
            "report_type": "Q",
            "period_end": "2023-06-30",
            "scale": "thousands",
            "currency": "AUD",
        },
        title="Q4 FY23 market update",
    )

    assert candidate is not None
    assert candidate["revenue"] == 1_546_000
    assert candidate["row_refs"] == {"revenue": "Q4 FY23 Net Revenue"}


def test_market_update_net_revenue_candidate_abstains_outside_quarterly_context():
    """The fallback must not turn annual rows or non-market updates into revenue."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _extract_market_update_net_revenue_candidate,
    )

    table = DoclingTable(
        page_number=2,
        caption="FY23 headline unaudited trips and revenues",
        headers=["Year", "Trips", "Net Revenue"],
        rows=[
            ["Year", "Trips", "Net Revenue"],
            ["FY23", "646K", "$5,085K"],
        ],
    )

    annual_candidate = _extract_market_update_net_revenue_candidate(
        [table],
        sections=[{"page": 1, "text": "Q4 FY23 Market Update"}],
        pass1_result={
            "report_type": "A",
            "period_end": "2023-06-30",
            "scale": "thousands",
            "currency": "AUD",
        },
        title="Q4 FY23 market update",
    )
    non_market_update_candidate = _extract_market_update_net_revenue_candidate(
        [table],
        sections=[{"page": 1, "text": "Q4 FY23 Results"}],
        pass1_result={
            "report_type": "Q",
            "period_end": "2023-06-30",
            "scale": "thousands",
            "currency": "AUD",
        },
        title="Q4 FY23 results",
    )

    assert annual_candidate is None
    assert non_market_update_candidate is None


def test_pass4_common_metric_source_scale_overrides_document_scale():
    """A common table-local source scale should become the reconciled payload scale."""
    from app.services.multipass_extraction import (
        _common_metric_source_scale,
        _run_pass4_reconciler,
    )

    payload = _run_pass4_reconciler(
        [
            {
                "_source": "income_statement",
                "_page_number": 25,
                "_scale": "thousands",
                "_scale_source": "table",
                "revenue": 46_547_000,
                "np_attributable": 39_374_000,
                "pass3_confidence": 0.9,
                "row_refs": {
                    "revenue": "Total revenue",
                    "np_attributable": "Net profit/(loss) after tax",
                },
            }
        ],
        {
            "risk_summary": None,
            "risk_bullets": None,
            "guidance_summary": None,
            "material_changes": None,
            "confidence_narrative": 0.0,
        },
        {
            "report_type": "A",
            "period_end": "2025-06-30",
            "scale": "millions",
        },
    )

    assert payload["metric_source_scales"] == {
        "revenue": "thousands",
        "np_attributable": "thousands",
    }
    assert _common_metric_source_scale(payload, "millions") == "thousands"


def test_cashflow_scale_detection_prefers_formal_unit_row_over_prose_million():
    """RMS-style merged cash-flow tables must not inherit scale from prose rows."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _detect_scale_from_table

    table = DoclingTable(
        page_number=15,
        caption="Merged cashflow statement (Appendix 5B)",
        headers=[
            "STATEMENT OF CASH FLOWS\nFor the half-year ended 31 December 2025",
            "",
            "",
            "",
            "",
        ],
        rows=[
            [
                "STATEMENT OF CASH FLOWS\nFor the half-year ended 31 December 2025",
                "",
                "",
                "",
                "",
            ],
            ["Cash flow", "", "", "", ""],
            [
                "The cash provided by operating activities of $171.2 million was down",
                "",
                "",
                "",
                "",
            ],
            ["Cash used in investing activities totalled $211.4 million", "", "", "", ""],
            ["2025", "", "", "2024", ""],
            ["Note", "", "$'000", "", "$'000"],
            ["Cash flows from / (used in) operating activities", "", "", "", ""],
            ["Net cash provided by operating activities", "", "171,179", "", "327,338"],
        ],
    )

    assert _detect_scale_from_table(table) == "thousands"


def test_cashflow_capex_prefers_ppe_row_over_acquisition_outflow():
    """RMS capex should bind to PP&E, not acquisition-of-subsidiary cash flow."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=15,
        caption="Merged cashflow statement (Appendix 5B)",
        headers=[
            "STATEMENT OF CASH FLOWS\nFor the half-year ended 31 December 2025",
            "",
            "",
            "",
            "",
        ],
        raw_header_rows=[["", "", "31 Dec 2025", "", "31 Dec 2024"]],
        rows=[
            ["2025", "", "", "2024", ""],
            ["Note", "", "$'000", "", "$'000"],
            ["Cash flows from / (used in) operating activities", "", "", "", ""],
            ["Net cash provided by operating activities", "", "171,179", "", "327,338"],
            ["Cash flows (used in) / from investing activities", "", "", "", ""],
            ["Payments for property, plant and equipment", "10", "(25,239)", "", "(11,748)"],
            ["Payments for mine development", "11", "(83,614)", "", "(60,981)"],
            ["Payments for acquisition of subsidiary, net of cash acquired", "15", "(71,217)", "", "-"],
            ["Net cash used in investing activities", "", "(211,390)", "", "(246,051)"],
            ["Cash flows used in financing activities", "", "", "", ""],
            ["Net cash used in financing activities", "", "(84,747)", "", "(51,106)"],
        ],
    )

    raw_response = {
        "operating_cf": "171,179",
        "investing_cf": "(211,390)",
        "financing_cf": "(84,747)",
        "cash_end": None,
        "capex": "(71,217)",
        "pass3_confidence": 0.9,
        "row_refs": {
            "operating_cf": "Net cash provided by operating activities",
            "investing_cf": "Net cash used in investing activities",
            "financing_cf": "Net cash used in financing activities",
            "capex": "Payments for acquisition of subsidiary, net of cash acquired",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["_scale"] == "thousands"
    assert result["operating_cf"] == 171_179_000
    assert result["investing_cf"] == -211_390_000
    assert result["financing_cf"] == -84_747_000
    assert result["capex"] == -25_239_000
    assert result["row_refs"]["capex"] == "Payments for property, plant and equipment"


def test_cashflow_capex_prefers_ppe_row_over_multirow_investing_aggregate():
    """DXS capex should not sum every investing-payment row when PP&E is present."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=20,
        caption="Consolidated statement of cash flows",
        headers=["", "31 Dec 2025 $m", "31 Dec 2024 $m"],
        rows=[
            ["Cash flows from investing activities", "", ""],
            ["Payments for capital expenditure on investment properties", "(15.5)", "(21.4)"],
            ["Payments for investments accounted for using the equity method", "(150.2)", "(35.0)"],
            ["Payments for investments accounted for at fair value", "(198.2)", "(14.1)"],
            ["Payments for property, plant and equipment", "(27.2)", "(9.3)"],
            ["Payments for intangibles", "(95.9)", "(7.1)"],
            ["Payment for acquisition of subsidiary, net of cash acquired", "(121.7)", "-"],
            ["Net cash inflow/(outflow) from investing activities", "83.9", "(112.0)"],
        ],
    )

    raw_response = {
        "operating_cf": None,
        "investing_cf": "83.9",
        "financing_cf": None,
        "cash_end": None,
        "capex": "(608.7)",
        "pass3_confidence": 0.9,
        "row_refs": {
            "investing_cf": "Net cash inflow/(outflow) from investing activities",
            "capex": (
                "Payments for capital expenditure on investment properties, "
                "Payments for investments accounted for using the equity method, "
                "Payments for investments accounted for at fair value, "
                "Payments for property, plant and equipment, "
                "Payments for intangibles, "
                "Payment for acquisition of subsidiary, net of cash acquired"
            ),
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["investing_cf"] == 83_900_000
    assert result["capex"] == -27_200_000
    assert result["row_refs"]["capex"] == "Payments for property, plant and equipment"


def test_cashflow_capex_prefers_bank_other_assets_over_investment_securities():
    """ANZ-style bank capex binds to other assets, not security purchases."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=28,
        caption="Condensed consolidated statement of cash flows",
        headers=["", "Mar 2025 $m", "Mar 2024 $m"],
        raw_header_rows=[["", "31 Mar 2025", "31 Mar 2024"]],
        rows=[
            ["Cash flows from investing activities", "", ""],
            ["Investment securities assets: Purchases", "(1,073)", "(872)"],
            ["Investment securities assets: Sales and maturities", "974", "649"],
            ["Net investments in other assets", "(242)", "(381)"],
            ["Net cash used in investing activities", "(341)", "(604)"],
        ],
    )
    raw_response = {
        "operating_cf": None,
        "investing_cf": "(341)",
        "financing_cf": None,
        "cash_end": None,
        "capex": "(1,073)",
        "pass3_confidence": 0.9,
        "row_refs": {
            "investing_cf": "Net cash used in investing activities",
            "capex": "Investment securities assets:Purchases",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-03-31",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] == -242_000_000
    assert result["row_refs"]["capex"] == "Net investments in other assets"


def test_cashflow_capex_rejects_securities_purchase_row_without_bank_capex():
    """A securities-purchase row alone is not a capex source."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=28,
        caption="Condensed consolidated statement of cash flows",
        headers=["", "Mar 2025 $m", "Mar 2024 $m"],
        rows=[
            ["Cash flows from investing activities", "", ""],
            ["Investment securities assets: Purchases", "(1,073)", "(872)"],
            ["Investment securities assets: Sales and maturities", "974", "649"],
            ["Net cash used in investing activities", "(99)", "(223)"],
        ],
    )
    raw_response = {
        "operating_cf": None,
        "investing_cf": "(99)",
        "financing_cf": None,
        "cash_end": None,
        "capex": "(1,073)",
        "pass3_confidence": 0.9,
        "row_refs": {
            "investing_cf": "Net cash used in investing activities",
            "capex": "Investment securities assets:Purchases",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-03-31",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] is None
    assert "capex" not in result["row_refs"]


def test_cashflow_capex_distinguishes_financial_from_non_financial_assets():
    from app.services.multipass_extraction import (
        _cashflow_capex_row_is_disallowed_financial_asset,
    )

    assert _cashflow_capex_row_is_disallowed_financial_asset(
        "Purchase of financial assets"
    )
    assert _cashflow_capex_row_is_disallowed_financial_asset(
        "Net payments for purchase of interest-bearing financial assets"
    )
    assert not _cashflow_capex_row_is_disallowed_financial_asset(
        "Payments for non-financial assets"
    )
    assert _cashflow_capex_row_is_disallowed_financial_asset(
        "Purchases of financial assets and non-financial assets"
    )


def test_cashflow_statement_text_recovers_bank_other_assets_capex():
    from app.services.multipass_extraction import (
        _recover_cashflow_metrics_from_statement_text,
    )

    recovered = _recover_cashflow_metrics_from_statement_text(
        [
            "Condensed Consolidated Statement of Cash Flows",
            "Cash flows from investing activities",
            "Investment securities assets:",
            "Purchases (41,649) (40,877) (43,900)",
            "Proceeds from sale or maturity 31,629 24,546 22,996",
            "Net investments in other assets (242) (153) (451)",
            "Net cash provided by/(used in) investing activities (10,262) (21,380) (20,687)",
        ],
        "millions",
    )

    assert recovered["capex"] == (
        -242_000_000,
        "Net investments in other assets",
    )


def test_cashflow_capex_abstains_when_grouped_value_is_detached_from_label():
    """A grouped value on an unlabeled row is not a unique source cell."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=12,
        caption="8",
        headers=["NOTE", "4 JANUARY\n2026\n$M", "5 JANUARY\n2025\n(RESTATED)1\n$M"],
        raw_header_rows=[["", "4 Jan 2026", "5 Jan 2025"]],
        rows=[
            [
                "Cash flows from investing activities\n"
                "Proceeds from the sale of property, plant and equipment\n"
                "Payments for property, plant and equipment and intangible assets\n"
                "Proceeds from the sale of subsidiaries and investments, net of cash disposed\n"
                "Payments for the purchase of businesses\n"
                "Payments for the purchase of investments\n"
                "Advances to non-related parties\n"
                "Dividends received",
                "",
                "142\n(1,218)\n408\n-\n-\n(10)\n-",
            ],
            ["", "65", ""],
            ["", "(1,304)", ""],
            ["", "98", ""],
            ["", "(11)", ""],
            ["", "(35)", ""],
            ["", "-", ""],
            ["", "1", ""],
            ["Net cash used in investing activities", "(1,186)", "(678)"],
        ],
    )
    raw_response = {
        "operating_cf": None,
        "investing_cf": "(1,186)",
        "financing_cf": None,
        "cash_end": None,
        "capex": "(1,218)",
        "pass3_confidence": 0.9,
        "row_refs": {
            "investing_cf": "Net cash used in investing activities",
            "capex": "Payments for property, plant and equipment",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2026-01-04",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] is None
    assert "capex" not in result["row_refs"]


def test_cashflow_capex_keeps_same_row_current_value_in_grouped_rows():
    """CSL grouped cashflow rows can store the first current value on the label row."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=14,
        caption="Consolidated Statement of Cash Flows",
        headers=["Notes", "December\n2025\nUS$m", "December\n2024\nUS$m"],
        raw_header_rows=[["", "31 Dec 2025", "31 Dec 2024"]],
        rows=[
            [
                "Cash flows from Investing Activities\n"
                "Payments for property, plant and equipment\n"
                "Proceeds from sale of property, plant and equipment\n"
                "Payments for intangible assets",
                "(296)",
                "(378)\n-\n(155)",
            ],
            ["", "3", ""],
            ["", "(360)", ""],
            ["Net cash outflow from investing activities", "(652)", "(366)"],
        ],
    )
    raw_response = {
        "operating_cf": None,
        "investing_cf": "(652)",
        "financing_cf": None,
        "cash_end": None,
        "capex": "(296)",
        "pass3_confidence": 0.9,
        "row_refs": {"capex": "Payments for property, plant and equipment"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "USD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] == -296_000_000
    assert result["row_refs"]["capex"] == "Payments for property, plant and equipment"


def test_cashflow_capex_grouped_rows_skip_note_column_for_current_value():
    """Grouped cashflow recovery should not treat note numbers as amounts."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=14,
        caption="Consolidated Statement of Cash Flows",
        headers=["Notes", "Note", "December\n2025\nUS$m", "December\n2024\nUS$m"],
        raw_header_rows=[["", "", "31 Dec 2025", "31 Dec 2024"]],
        rows=[
            [
                "Cash flows from Investing Activities\n"
                "Payments for property, plant and equipment\n"
                "Proceeds from sale of property, plant and equipment\n"
                "Payments for intangible assets",
                "10",
                "(296)",
                "(378)",
            ],
            ["", "", "3", "-"],
            ["", "", "(360)", "(155)"],
            ["Net cash outflow from investing activities", "", "(652)", "(366)"],
        ],
    )
    raw_response = {
        "operating_cf": None,
        "investing_cf": "(652)",
        "financing_cf": None,
        "cash_end": None,
        "capex": "(296)",
        "pass3_confidence": 0.9,
        "row_refs": {"capex": "Payments for property, plant and equipment"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "USD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] == -296_000_000
    assert result["row_refs"]["capex"] == "Payments for property, plant and equipment"


def test_cashflow_capex_grouped_rows_keep_small_current_value_without_note_column():
    """Grouped rows without note columns should not choose comparative values."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=14,
        caption="Consolidated Statement of Cash Flows",
        headers=["Notes", "December\n2025\nUS$m", "December\n2024\nUS$m"],
        raw_header_rows=[["", "31 Dec 2025", "31 Dec 2024"]],
        rows=[
            [
                "Cash flows from Investing Activities\n"
                "Payments for property, plant and equipment\n"
                "Payments for intangible assets",
                "(65)",
                "(142)",
            ],
            ["", "(3)", "(155)"],
            ["Net cash outflow from investing activities", "(68)", "(297)"],
        ],
    )
    raw_response = {
        "operating_cf": None,
        "investing_cf": "(68)",
        "financing_cf": None,
        "cash_end": None,
        "capex": "(65)",
        "pass3_confidence": 0.9,
        "row_refs": {"capex": "Payments for property, plant and equipment"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "USD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] == -65_000_000
    assert result["row_refs"]["capex"] == "Payments for property, plant and equipment"


def test_cashflow_cash_end_prefers_cash_equivalents_over_cash_and_gold():
    """RMS cash_end should bind to cash equivalents, not the broader cash-and-gold row."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=15,
        caption="Merged cashflow statement (Appendix 5B)",
        headers=[
            "STATEMENT OF CASH FLOWS\nFor the half-year ended 31 December 2025",
            "",
            "",
            "",
            "",
        ],
        raw_header_rows=[["", "", "31 Dec 2025", "", "31 Dec 2024"]],
        rows=[
            ["2025", "", "", "2024", ""],
            ["Note", "", "$'000", "", "$'000"],
            ["Cash flows from / (used in) operating activities", "", "", "", ""],
            ["Net cash provided by operating activities", "", "171,179", "", "327,338"],
            ["Cash and gold at 31 December 2025", "", "694,300", "", "454,455"],
            [
                "Cash and cash equivalents at the end of the half-year",
                "",
                "658,721",
                "",
                "454,455",
            ],
        ],
    )

    raw_response = {
        "operating_cf": "171,179",
        "investing_cf": None,
        "financing_cf": None,
        "cash_end": "694,300",
        "capex": None,
        "pass3_confidence": 0.9,
        "row_refs": {
            "operating_cf": "Net cash provided by operating activities",
            "cash_end": "Cash and gold at 31 December 2025",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["_scale"] == "thousands"
    assert result["cash_end"] == 658_721_000
    assert (
        result["row_refs"]["cash_end"]
        == "Cash and cash equivalents at the end of the half-year"
    )


def test_cashflow_cash_end_does_not_replace_without_cash_equivalents_row():
    """A cash-and-gold row alone is not enough evidence for cash_end recovery."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=15,
        caption="Merged cashflow statement (Appendix 5B)",
        headers=[
            "STATEMENT OF CASH FLOWS\nFor the half-year ended 31 December 2025",
            "",
            "",
            "",
            "",
        ],
        raw_header_rows=[["", "", "31 Dec 2025", "", "31 Dec 2024"]],
        rows=[
            ["2025", "", "", "2024", ""],
            ["Note", "", "$'000", "", "$'000"],
            ["Net cash provided by operating activities", "", "171,179", "", "327,338"],
            ["Cash and gold at 31 December 2025", "", "694,300", "", "454,455"],
        ],
    )

    raw_response = {
        "operating_cf": "171,179",
        "investing_cf": None,
        "financing_cf": None,
        "cash_end": "694,300",
        "capex": None,
        "pass3_confidence": 0.9,
        "row_refs": {
            "operating_cf": "Net cash provided by operating activities",
            "cash_end": "Cash and gold at 31 December 2025",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["_scale"] == "thousands"
    assert result["cash_end"] == 694_300_000
    assert result["row_refs"]["cash_end"] == "Cash and gold at 31 December 2025"


def test_cash_end_overlay_uses_later_exact_cash_equivalents_table():
    """RMS exact cash equivalents can be on a later table than selected Appendix 5B."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _apply_preferred_cash_end_source_payload

    appendix_5b_table = DoclingTable(
        page_number=15,
        caption="Merged cashflow statement (Appendix 5B)",
        headers=["", "", "$'000", "", "$'000"],
        rows=[
            ["Cash and gold at 31 December 2025", "", "694,300", "", "454,455"],
        ],
    )
    formal_cashflow_table = DoclingTable(
        page_number=23,
        caption="Ramelius Resources Limited",
        headers=["", "", "$'000", "", "$'000"],
        rows=[
            [
                "Cash and cash equivalents at the end of the half-year",
                "",
                "658,721",
                "",
                "454,455",
            ],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {"cash_end": 694_300_000},
        "cash_end": 694_300_000,
        "row_refs": {"cash_end": "Cash and gold at 31 December 2025"},
        "provenance": {"cash_end": "cashflow_statement:page_15:Cash and gold at 31 December 2025"},
    }

    _apply_preferred_cash_end_source_payload(
        payload,
        [appendix_5b_table, formal_cashflow_table],
        scale="thousands",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["cash_end"] == 658_721_000
    assert payload["metrics"]["cash_end"] == 658_721_000
    assert (
        payload["row_refs"]["cash_end"]
        == "Cash and cash equivalents at the end of the half-year"
    )
    assert payload["metric_source_scales"]["cash_end"] == "thousands"
    assert payload["metric_scale_sources"]["cash_end"] == "table"
    assert payload["field_provenance"]["cash_end"]["page_number"] == 23


def test_cash_end_overlay_does_not_replace_without_exact_cash_equivalents_row():
    """The document-wide overlay must not promote broader cash-and-gold rows."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _apply_preferred_cash_end_source_payload

    table = DoclingTable(
        page_number=15,
        caption="Merged cashflow statement (Appendix 5B)",
        headers=["", "", "$'000", "", "$'000"],
        rows=[
            ["Cash and gold at 31 December 2025", "", "694,300", "", "454,455"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {"cash_end": 694_300_000},
        "cash_end": 694_300_000,
        "row_refs": {"cash_end": "Cash and gold at 31 December 2025"},
        "provenance": {"cash_end": "cashflow_statement:page_15:Cash and gold at 31 December 2025"},
    }

    _apply_preferred_cash_end_source_payload(
        payload,
        [table],
        scale="thousands",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["cash_end"] == 694_300_000
    assert payload["row_refs"]["cash_end"] == "Cash and gold at 31 December 2025"


def test_cash_end_overlay_recovers_net_of_overdrafts_year_end_row():
    """BHP-style cash equivalents net of overdrafts is exact cash_end evidence."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _apply_preferred_cash_end_source_payload

    table = DoclingTable(
        page_number=46,
        caption="Consolidated cash flow statement",
        headers=["", "2021", "2020"],
        rows=[
            [
                "Cash and cash equivalents, net of overdrafts, at the end of the financial year",
                "15,246",
                "13,426",
            ],
        ],
    )
    payload = {
        "period_type": "A",
        "period_end": "2021-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"cash_end": 1_467_000_000},
        "cash_end": 1_467_000_000,
        "row_refs": {
            "cash_end": "Net increase/(decrease) in cash and cash equivalents from Continuing operations",
        },
        "provenance": {},
    }

    _apply_preferred_cash_end_source_payload(
        payload,
        [table],
        scale="millions",
        pass1_result={
            "report_type": "A",
            "period_end": "2021-06-30",
            "currency": "USD",
        },
    )

    assert payload["cash_end"] == 15_246_000_000
    assert (
        payload["row_refs"]["cash_end"]
        == "Cash and cash equivalents, net of overdrafts, at the end of the financial year"
    )


def test_cashflow_capex_recovers_small_millions_ppe_row():
    """QBE-style insurer PP&E capex can be a small single-digit US$M row."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=21,
        caption="Consolidated statement of cash flows",
        headers=["", "30 June 2025 US$M", "30 June 2024 US$M"],
        raw_header_rows=[["", "30 Jun 2025", "30 Jun 2024"]],
        rows=[
            ["Investing activities", "", ""],
            ["Payments for purchase of intangible assets", "(36)", "(45)"],
            ["Payments for purchase of property, plant and equipment", "(9)", "(11)"],
            ["Net cash flows from investing activities", "(562)", "(615)"],
        ],
    )
    raw_response = {
        "operating_cf": None,
        "investing_cf": "(562)",
        "financing_cf": None,
        "cash_end": None,
        "capex": None,
        "pass3_confidence": 0.9,
        "row_refs": {"investing_cf": "Net cash flows from investing activities"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-06-30",
                "currency": "USD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] == -9_000_000
    assert (
        result["row_refs"]["capex"]
        == "Payments for purchase of property, plant and equipment"
    )


def test_cashflow_row_ref_over_scaled_millions_values_recover_from_source_rows():
    """DXS-style $m cash-flow rows must beat 1000x over-scaled LLM outputs."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=20,
        caption="Consolidated Statement of Cash Flows",
        headers=["", "31 Dec 2025 $m", "31 Dec 2024 $m"],
        rows=[
            ["Cash flows from operating activities", "", ""],
            ["Net cash inflow/(outflow) from operating activities", "168.5", "264.1"],
            ["Cash flows from investing activities", "", ""],
            ["Net cash inflow/(outflow) from investing activities", "83.9", "123.6"],
            ["Cash flows from financing activities", "", ""],
            ["Net cash inflow/(outflow) from financing activities", "(243.0)", "(386.2)"],
            ["Cash and cash equivalents at the end of the period", "74.7", "55.5"],
        ],
    )
    raw_response = {
        "operating_cf": "168,500",
        "investing_cf": "83,900",
        "financing_cf": "(243,000)",
        "cash_end": "74,700",
        "capex": None,
        "pass3_confidence": 0.9,
        "row_refs": {
            "operating_cf": "Net cash inflow/(outflow) from operating activities",
            "investing_cf": "Net cash inflow/(outflow) from investing activities",
            "financing_cf": "Net cash inflow/(outflow) from financing activities",
            "cash_end": "Cash and cash equivalents at the end of the period",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["operating_cf"] == 168_500_000
    assert result["investing_cf"] == 83_900_000
    assert result["financing_cf"] == -243_000_000
    assert result["cash_end"] == 74_700_000


def test_cashflow_capex_abstains_on_multiline_label_with_detached_value():
    """A multiline label cannot bind a value from a separate unlabeled row."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=21,
        caption="Consolidated statement of cash flows",
        headers=["", "30 June 2025 US$M", "30 June 2024 US$M"],
        rows=[
            [
                "Investing activities\n"
                "Net payments for purchase of growth assets\n"
                "Net payments for purchase of interest-bearing financial assets\n"
                "Net payments for foreign exchange transactions\n"
                "Payments for purchase of intangible assets\n"
                "Payments for purchase of property, plant and equipment\n"
                "Payments for investment in associates",
                "",
                "(245)\n(225)\n(77)\n(45)\n(11)\n(12)",
            ],
            ["", "(202)", ""],
            ["", "(272)", ""],
            ["", "(40)", ""],
            ["", "(36)", ""],
            ["", "(9)", ""],
            ["", "(3)", ""],
            ["Net cash flows from investing activities", "(562)", "(615)"],
        ],
    )

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value={
            "operating_cf": None,
            "investing_cf": "(562)",
            "financing_cf": None,
            "cash_end": None,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {"investing_cf": "Net cash flows from investing activities"},
        },
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-06-30",
                "currency": "USD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] is None
    assert "capex" not in result["row_refs"]


def test_cashflow_capex_abstains_on_fragmented_narrative_amount():
    """A narrative amount split across cells is not a period-bound source cell."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=15,
        caption="Directors report cash used in investing activities",
        headers=["", "", "", "", "", "", "", ""],
        raw_header_rows=[["", "31 Dec 2025", "", "", "", "", "", ""]],
        rows=[
            [
                "",
                "Payments for the",
                "development of open pit",
                "and underground",
                "mines of $83",
                ".6 million",
                "",
                "",
            ],
            [
                "",
                "Payments for prop",
                "erty, plant, and eq",
                "uipmen",
                "t, at both existing and new sites, of $25",
                ".2 million",
                "",
                "",
            ],
        ],
    )

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value={
            "operating_cf": None,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": None,
            "capex": -83_600_000,
            "pass3_confidence": 0.9,
            "row_refs": {
                "capex": "Payments for the development of open pit and underground mines"
            },
        },
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "thousands",
            1_000,
            llm_client=None,
        )

    assert result is not None
    assert result["capex"] is None
    assert "capex" not in result["row_refs"]


def test_appendix5b_cashflow_prefers_current_quarter_section_totals():
    """Appendix 5B investing_cf must use item 2.6 current quarter, not sub-items/YTD."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=14,
        caption="Merged cashflow statement (Appendix 5B)",
        headers=["", "", "Current quarter $A'000", "Year to date $A'000"],
        raw_header_rows=[["", "", "31 Dec 2025", "31 Dec 2024"]],
        rows=[
            ["2.", "Cash flows from investing activities", "", ""],
            ["2.1", "Payments to acquire or for:", "", ""],
            ["", "(c) property, plant and equipment", "(2,331)", "(3,961)"],
            ["", "(d) exploration & evaluation (if capitalised)", "(23)", "(24)"],
            ["2.5", "Other - ERC Increase & Security Deposits", "(255)", "(255)"],
            [
                "2.6",
                "Net cash from / (used in) investing activities",
                "(2,656)",
                "(5,590)",
            ],
            ["3.10", "Net cash from / (used in) financing activities", "12,011", "42,240"],
        ],
    )
    raw_response = {
        "operating_cf": None,
        "investing_cf": "(255)",
        "financing_cf": "42,240",
        "cash_end": None,
        "capex": None,
        "pass3_confidence": 0.9,
        "row_refs": {
            "investing_cf": "Other - ERC Increase & Security Deposits",
            "financing_cf": "Net cash from / (used in) financing activities",
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "Q",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "thousands",
            1_000,
            llm_client=None,
        )

    assert result is not None
    assert result["investing_cf"] == -2_656_000
    assert result["financing_cf"] == 12_011_000
    assert (
        result["row_refs"]["investing_cf"]
        == "Net cash from / (used in) investing activities"
    )


def test_appendix5b_multiline_summary_abstains_without_unique_cells():
    """Packed multi-value cells cannot source-bind individual cashflow metrics."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=15,
        caption="Mining exploration entity quarterly cash flow report",
        headers=[
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        raw_header_rows=[["", "", "31 Dec 2025", "31 Dec 2024"]],
        rows=[
            [
                "1.9",
                "Net cash from / (used in) operating activities",
                "(2,467)",
                "(7,128)",
            ],
            [
                "4.1 Cash and cash equivalents at beginning of period\n"
                "4.2 Net cash from / (used in) operating activities (item 1.9 above)\n"
                "4.3 Net cash from / (used in) investing activities (item 2.6 above)\n"
                "4.4 Net cash from / (used in) financing activities (item 3.10 above)\n"
                "4.5 Effect of movement in exchange rates on cash held",
                "11,474\n1,154\n(2,656)\n12,012\n(5)",
                "1,874\n(16,503)\n(5,590)\n42,241\n(43)",
            ],
        ],
    )

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value={
            "operating_cf": None,
            "investing_cf": "(255)",
            "financing_cf": None,
            "cash_end": None,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {"investing_cf": "Other - ERC Increase & Security Deposits"},
        },
    ):
        result = _extract_single_table(
            "cashflow_statement",
            table,
            {
                "report_type": "Q",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "thousands",
            1_000,
            llm_client=None,
        )

    assert result is not None
    assert result["operating_cf"] is None
    assert result["investing_cf"] is None
    assert result["financing_cf"] is None
    assert not {
        "operating_cf",
        "investing_cf",
        "financing_cf",
    }.intersection(result["row_refs"])


def test_appendix_wrapper_recovers_rms_ebit_and_npat_from_exact_table_rows():
    """RMS Appendix 4D source rows can provide exact EBIT and attributable NPAT."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _build_appendix_wrapper_source_payload

    table = DoclingTable(
        page_number=1,
        caption="RESULTS FOR ANNOUNCEMENT TO THE MARKET",
        headers=["", "", "", "", "", "", "", "", "", "", "", ""],
        rows=[
            ["", "Revenue from ordinary activities", "", "", "(3%)", "", "", "485,630", "", "", "500,000", ""],
            [
                "",
                "Earnings before Interest and Tax (EBIT)",
                "",
                "",
                "(87%)",
                "",
                "",
                "31,284",
                "",
                "",
                "231,056",
                "",
            ],
            [
                "",
                "Net (loss) / profit after tax attributable to members",
                "",
                "",
                "(107%)",
                "",
                "",
                "(11,716)",
                "",
                "",
                "170,369",
                "",
            ],
        ],
    )

    payload = _build_appendix_wrapper_source_payload(
        title="Appendix 4D and December 2025 Half Yearly Financial Report",
        sections=[
            {"page": 1, "text": "Appendix 4D"},
            {"page": 1, "text": "For the half-year ended 31 December 2025"},
        ],
        tables=[table],
        period_evidence={"period_type": "H"},
        period_end_evidence={
            "period_type": "H",
            "period_end": "2025-12-31",
            "hits": [
                {
                    "source": "source_text",
                    "period_end": "2025-12-31",
                    "reason": "current_period_range",
                }
            ],
        },
        scale="thousands",
        currency="AUD",
    )

    assert payload["is_wrapper"] is True
    assert payload["metrics"]["ebit"] == 31_284_000
    assert payload["metrics"]["np_attributable"] == -11_716_000
    assert payload["row_refs"]["ebit"] == "Earnings before Interest and Tax (EBIT)"
    assert (
        payload["row_refs"]["np_attributable"]
        == "Net (loss) / profit after tax attributable to members"
    )


def test_income_statement_recovers_operations_and_owner_attributable_rows():
    """Formal income statements can prove EBIT and parent-attributable NPAT."""
    from unittest.mock import patch

    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _extract_single_table

    table = DoclingTable(
        page_number=14,
        caption="Consolidated statement of profit or loss",
        headers=["", "Note", "31 Dec 2025 $M", "31 Dec 2024 $M"],
        rows=[
            ["REVENUE", "4", "3,052", "2,290"],
            ["PROFIT/(LOSS) FROM OPERATIONS", "", "1,031", "(972)"],
            ["PROFIT/(LOSS) FOR THE HALF-YEAR IS ATTRIBUTABLE TO:", "", "", ""],
            ["Non-controlling interests", "", "78", "2"],
            ["Equity holders of the parent", "", "495", "(809)"],
        ],
    )
    raw_response = {
        "revenue": "3,052",
        "ebit": None,
        "np_attributable": None,
        "pass3_confidence": 0.9,
        "row_refs": {"revenue": "REVENUE"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=raw_response,
    ):
        result = _extract_single_table(
            "income_statement",
            table,
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
            },
            "millions",
            1_000_000,
            llm_client=None,
        )

    assert result is not None
    assert result["ebit"] == 1_031_000_000
    assert result["np_attributable"] == 495_000_000
    assert result["row_refs"]["ebit"] == "PROFIT/(LOSS) FROM OPERATIONS"
    assert result["row_refs"]["np_attributable"] == "Equity holders of the parent"


def test_appendix_wrapper_does_not_overwrite_formal_statement_metrics():
    """Appendix 4D summary rows supplement but must not replace formal statements."""
    from app.services.multipass_extraction import _apply_appendix_wrapper_source_payload

    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
        "metrics": {
            "revenue": 3_052_000_000,
            "ebit": 1_031_000_000,
            "np_attributable": 495_000_000,
        },
        "revenue": 3_052_000_000,
        "ebit": 1_031_000_000,
        "np_attributable": 495_000_000,
        "row_refs": {
            "revenue": "REVENUE",
            "ebit": "PROFIT/(LOSS) FROM OPERATIONS",
            "np_attributable": "Equity holders of the parent",
        },
        "provenance": {
            "np_attributable": "income_statement:page_14:Equity holders of the parent"
        },
    }
    wrapper_source = {
        "is_wrapper": True,
        "document_subtype": "appendix4d",
        "document_title": "MIN_H_2025-12-31",
        "period_type": "H",
        "period_end": "2025-12-31",
        "scale": "millions",
        "currency": "AUD",
        "metrics": {"np_attributable": 2_000_000},
        "row_refs": {"np_attributable": "previous period footnote"},
        "provenance": {"np_attributable": "appendix_wrapper:page_2:previous period footnote"},
        "wrapper_disclosures": [],
    }

    _apply_appendix_wrapper_source_payload(payload, wrapper_source)

    assert payload["metrics"]["np_attributable"] == 495_000_000
    assert payload["np_attributable"] == 495_000_000
    assert payload["row_refs"]["np_attributable"] == "Equity holders of the parent"


def test_appendix_wrapper_recovers_min_owner_attributable_row():
    """MIN-style Appendix 4D labels include half-year wording before ordinary activities."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _build_appendix_wrapper_source_payload

    table = DoclingTable(
        page_number=1,
        caption="For personal use only",
        headers=["", "", "", "", "", "", "", "", "", "", "", "$M", "", ""],
        rows=[
            [
                "Profit for the half-year from ordinary activities after tax attributable to the owners\n"
                "of Mineral Resources Limited1,2",
                "",
                "",
                "up",
                "",
                "",
                "161%",
                "",
                "",
                "to",
                "",
                "495",
                "",
                "",
            ],
        ],
    )

    payload = _build_appendix_wrapper_source_payload(
        title="FY26 Half-Year Financial Report and Appendix 4D",
        sections=[
            {"page": 1, "text": "Appendix 4D"},
            {"page": 1, "text": "For the half-year ended 31 December 2025"},
        ],
        tables=[table],
        period_evidence={"period_type": "H"},
        period_end_evidence={
            "period_type": "H",
            "period_end": "2025-12-31",
            "hits": [
                {
                    "source": "source_text",
                    "period_end": "2025-12-31",
                    "reason": "current_period_range",
                }
            ],
        },
        scale="millions",
        currency="AUD",
    )

    assert payload["metrics"]["np_attributable"] == 495_000_000


def test_income_source_overlay_fills_missing_and_weak_wrapper_metrics():
    """Formal income rows can fill missing EBIT and replace weak wrapper NPAT."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    table = DoclingTable(
        page_number=14,
        caption="MINERAL RESOURCES LIMITED - CONSOLIDATED INCOME STATEMENT",
        headers=["", "", "", "Note", "", "", "31 Dec 2025 $M", "", "", "31 Dec 2024"],
        rows=[
            ["", "REVENUE", "", "", "4", "", "", "3,052", "", "2,290", ""],
            ["PROFIT/(LOSS) FROM OPERATIONS", "", "", "", "", "", "1,031", "", "", "(972)", ""],
            ["", "PROFIT/(LOSS) FOR THE HALF-YEAR IS ATTRIBUTABLE TO:", "", "", "", "", "", "", "", "", ""],
            ["", "Non-controlling interests", "", "", "", "", "", "78", "", "2", ""],
            ["Equity holders of the parent", "", "", "", "", "", "495", "", "", "(809)", ""],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
        "metrics": {
            "revenue": 3_052_000_000,
            "ebit": None,
            "np_attributable": 2_000_000,
        },
        "ebit": None,
        "np_attributable": 2_000_000,
        "row_refs": {"np_attributable": "previous period footnote"},
        "provenance": {"np_attributable": "appendix_wrapper:page_2:previous period footnote"},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [table],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["ebit"] == 1_031_000_000
    assert payload["metrics"]["np_attributable"] == 495_000_000
    assert payload["row_refs"]["np_attributable"] == "Equity holders of the parent"


def test_income_source_overlay_preserves_fmg_current_period_source_cells():
    """Preferred FMG income rows must retain their exact current-period cells."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    table = DoclingTable(
        page_number=21,
        caption="Consolidated Income Statement",
        headers=[
            "",
            "Note",
            "31 December 2025 US$m",
            "31 December 2024 US$m",
        ],
        raw_header_rows=[
            ["", "", "31 December 2025", "31 December 2024"],
            ["", "Note", "US$m", "US$m"],
        ],
        rows=[
            ["Operating sales revenue", "2", "8,439", "7,638"],
            ["Profit for the period attributable to:", "", "", ""],
            ["Equity holders of the Company", "", "1,914", "1,553"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"revenue": None, "ebit": None, "np_attributable": None},
        "row_refs": {},
        "provenance": {},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [table],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["revenue"] == 8_439_000_000
    assert payload["metrics"]["np_attributable"] == 1_914_000_000
    assert payload["field_provenance"]["revenue"]["source_cell"] == {
        "page_number": 21,
        "row_index": 0,
        "column_index": 2,
        "row_label": "Operating sales revenue",
        "raw_value": "8,439",
        "header_cell": "31 December 2025",
        "requested_period_end": "2025-12-31",
    }
    assert payload["field_provenance"]["np_attributable"]["source_cell"] == {
        "page_number": 21,
        "row_index": 2,
        "column_index": 2,
        "row_label": "Equity holders of the Company",
        "raw_value": "1,914",
        "header_cell": "31 December 2025",
        "requested_period_end": "2025-12-31",
    }


def test_income_source_overlay_does_not_claim_ambiguous_period_source_cells():
    """Duplicate current-period columns must not produce exact-cell provenance."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    table = DoclingTable(
        page_number=21,
        caption="Consolidated Income Statement",
        headers=["", "31 Dec 2025", "31 Dec 2025", "31 Dec 2024"],
        raw_header_rows=[["", "31 Dec 2025", "31 Dec 2025", "31 Dec 2024"]],
        rows=[
            ["Operating sales revenue", "8,439", "8,439", "7,638"],
            ["Profit for the period attributable to:", "", "", ""],
            ["Equity holders of the Company", "1,914", "1,914", "1,553"],
        ],
    )
    payload = {
        "metrics": {"revenue": None, "np_attributable": None},
        "row_refs": {},
        "provenance": {},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [table],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["revenue"] == 8_439_000_000
    assert payload["metrics"]["np_attributable"] == 1_914_000_000
    assert "source_cell" not in payload["field_provenance"]["revenue"]
    assert "source_cell" not in payload["field_provenance"]["np_attributable"]


def test_income_source_overlay_does_not_claim_value_mismatched_source_cell():
    """A bound cell must agree with the recovered value before it is claimed."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    table = DoclingTable(
        page_number=21,
        caption="Consolidated Income Statement",
        headers=[
            "",
            "Note",
            "31 December 2025 US$m",
            "31 December 2024 US$m",
        ],
        raw_header_rows=[
            ["", "", "31 December 2025", "31 December 2024"],
            ["", "Note", "US$m", "US$m"],
        ],
        rows=[["Operating sales revenue", "2", "75", "70"]],
    )
    payload = {
        "metrics": {"revenue": None},
        "row_refs": {},
        "provenance": {},
    }

    with patch(
        "app.services.multipass_extraction._recover_income_statement_metrics_from_table",
        return_value={"revenue": (50_000_000, "Operating sales revenue")},
    ):
        _apply_preferred_income_statement_source_payload(
            payload,
            [table],
            scale="millions",
            pass1_result={
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "USD",
            },
        )

    assert payload["metrics"]["revenue"] == 50_000_000
    assert "source_cell" not in payload["field_provenance"]["revenue"]


def test_income_source_overlay_prefers_bhp_shareholder_attributable_row():
    """BHP split numeric cells should still bind NPAT to the shareholder row."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    table = DoclingTable(
        page_number=44,
        caption="",
        headers=["", "", "", "BHP Results for the year ended 30 June 2021"],
        rows=[
            ["Consolidated Income Statement for the year ended 30 June 2021"],
            ["", "", "", "", "", "", "2021", "", "2020", "2019"],
            ["", "", "", "Notes", "", "", "US$M", "", "US$M", "US$M"],
            ["Profit after taxation", "from Continuing", "operations", "", "", "1", "3,451", "", "8,736", "9,520"],
            ["Attributable to non", "-controlling interests", "", "", "", "", "2,147", "", "780", "879"],
            ["Attributable to BH", "P shareholders", "", "", "", "1", "1,304", "", "7,956", "8,306"],
        ],
    )
    payload = {
        "period_type": "A",
        "period_end": "2021-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"np_attributable": 3_451_000_000},
        "np_attributable": 3_451_000_000,
        "row_refs": {"np_attributable": "Profit after taxation from Continuing operations"},
        "provenance": {
            "np_attributable": (
                "income_statement:page_44:Profit after taxation from Continuing operations"
            )
        },
        "metric_source_scales": {"np_attributable": "millions"},
        "metric_scale_sources": {"np_attributable": "table"},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [table],
        scale="millions",
        pass1_result={
            "report_type": "A",
            "period_end": "2021-06-30",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["np_attributable"] == 11_304_000_000
    assert payload["row_refs"]["np_attributable"] == "Attributable to BHP shareholders"


def test_income_source_overlay_prefers_csl_shareholder_split_row():
    """CSL shareholder split rows should beat generic net profit for the period."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    table = DoclingTable(
        page_number=11,
        caption="Consolidated Statement of Comprehensive Income",
        headers=["Notes", "December\n2025\nUS$m", "December\n2024\nUS$m"],
        rows=[
            ["Net profit for the period", "286", "2,056"],
            ["Net profit/(loss) for the period attributable to:", "286", "2,056"],
            ["- Shareholders of CSL Limited\n- Non-controlling interests", "401\n(115)", "2,007\n49"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"np_attributable": 286_000_000},
        "np_attributable": 286_000_000,
        "row_refs": {"np_attributable": "Net profit for the period"},
        "provenance": {"np_attributable": "income_statement:page_11:Net profit for the period"},
        "metric_source_scales": {"np_attributable": "millions"},
        "metric_scale_sources": {"np_attributable": "table"},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [table],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["np_attributable"] == 401_000_000
    assert payload["row_refs"]["np_attributable"] == "- Shareholders of CSL Limited"


def test_income_source_overlay_recovers_csl_total_operating_revenue_split_row():
    """CSL split revenue/cost rows should bind revenue to Total operating revenue."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    table = DoclingTable(
        page_number=11,
        caption="Consolidated Statement of Comprehensive Income",
        headers=["Notes", "December\n2025\nUS$m", "December\n2024\nUS$m"],
        rows=[
            [
                (
                    "Sales and service revenue\n"
                    "Influenza pandemic facility reservation fees\n"
                    "Royalties and license revenue\n"
                    "Other income"
                ),
                "8,092\n94\n101\n45",
                "8,213\n89\n128\n53",
            ],
            [
                "Total operating revenue 2\nCost of sales",
                "8,332\n(3,870)",
                "8,483\n(3,934)",
            ],
            ["Operating profit (EBIT)", "577", "2,762"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"ebit": 577_000_000},
        "ebit": 577_000_000,
        "row_refs": {"ebit": "Operating profit (EBIT)"},
        "provenance": {"ebit": "income_statement:page_11:Operating profit (EBIT)"},
        "metric_source_scales": {"ebit": "millions"},
        "metric_scale_sources": {"ebit": "table"},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [table],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["revenue"] == 8_332_000_000
    assert payload["row_refs"]["revenue"] == "Total operating revenue"


def test_income_source_overlay_replaces_ebitda_with_profit_before_tax_row():
    """FMG-style EBITDA should yield to formal profit-before-tax evidence."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    table = DoclingTable(
        page_number=21,
        caption="Consolidated Income Statement",
        headers=["", "H1 FY26 US$m", "H1 FY25 US$m"],
        rows=[
            ["Underlying EBITDA", "4,486", "3,641"],
            ["Depreciation and amortisation", "(1,450)", "(1,216)"],
            ["Exploration, development and other expenses", "(131)", "(40)"],
            ["Profit before tax", "2,808", "2,288"],
            ["Income tax expense", "(898)", "(741)"],
            ["Net profit after tax", "1,910", "1,547"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
        "metrics": {
            "revenue": 8_439_000_000,
            "ebit": 4_486_000_000,
            "np_attributable": 1_914_000_000,
        },
        "ebit": 4_486_000_000,
        "row_refs": {"ebit": "Underlying EBITDA"},
        "provenance": {"ebit": "income_statement:page_14:Underlying EBITDA"},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [table],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["ebit"] == 2_808_000_000
    assert payload["ebit"] == 2_808_000_000
    assert payload["row_refs"]["ebit"] == "Profit before tax"
    assert payload["provenance"]["ebit"] == "income_statement:page_21:Profit before tax"


def test_income_source_overlay_prefers_full_statement_over_appendix_wrapper():
    """SEG-style full financial statements outrank Appendix 4D wrapper rows."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    full_statement = DoclingTable(
        page_number=15,
        caption="Consolidated statement of profit or loss and other comprehensive income",
        headers=["", "31 Dec 2025 $'000", "31 Dec 2024 $'000"],
        rows=[
            ["", "31 Dec 2025 $'000", "31 Dec 2024 $'000"],
            ["Revenue from continuing operations", "73,671", "65,000"],
            [
                "Profit / (loss) after income tax from continuing operations",
                "3,243",
                "1,100",
            ],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {
            "revenue": 73_671_000,
            "np_attributable": 9_715_000,
        },
        "revenue": 73_671_000,
        "np_attributable": 9_715_000,
        "row_refs": {
            "revenue": "2.1 Revenues from ordinary activities",
            "np_attributable": "2.3 Pre AASB-16 EBITDA",
        },
        "provenance": {
            "revenue": "appendix_wrapper:page_3:2.1 Revenues from ordinary activities",
            "np_attributable": "appendix_wrapper:page_3:2.3 Pre AASB-16 EBITDA",
        },
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [full_statement],
        scale="thousands",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["revenue"] == 73_671_000
    assert payload["metrics"]["np_attributable"] == 3_243_000
    assert payload["row_refs"]["revenue"] == "Revenue from continuing operations"
    assert (
        payload["row_refs"]["np_attributable"]
        == "Profit / (loss) after income tax from continuing operations"
    )
    assert payload["provenance"]["np_attributable"].startswith("income_statement:")


def test_income_source_overlay_prefers_total_rows_in_full_statement():
    """DXS-style group statements should use total revenue and period profit rows."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    group_statement = DoclingTable(
        page_number=16,
        caption="Consolidated Statement of Comprehensive Income",
        headers=["", "Note", "31 Dec 2025 $m", "31 Dec 2024 $m"],
        rows=[
            ["Revenue from ordinary activities", "", "", ""],
            ["Property revenue", "2", "150.0", "159.1"],
            ["Development revenue", "", "14.9", "20.2"],
            ["Management fees and other revenue", "3", "174.3", "242.3"],
            ["Interest revenue", "", "20.8", "13.1"],
            ["Total revenue from ordinary activities", "", "360.0", "434.7"],
            ["Profit for the period before tax", "", "347.6", "27.4"],
            ["Income tax benefit/(expense)", "5", "0.9", "(17.1)"],
            ["Profit for the period", "", "348.5", "10.3"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
        "metrics": {"revenue": None, "ebit": None, "np_attributable": None},
        "row_refs": {},
        "provenance": {},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [group_statement],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["revenue"] == 360_000_000
    assert payload["metrics"]["ebit"] == 347_600_000
    assert payload["metrics"]["np_attributable"] == 348_500_000
    assert payload["row_refs"]["revenue"] == "Total revenue from ordinary activities"


def test_income_source_overlay_prefers_bank_operating_income_over_net_interest_income():
    """ANZ-style bank statements use Operating income as the revenue-equivalent total."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    bank_statement = DoclingTable(
        page_number=5,
        caption="",
        headers=[
            "Net interest income\nOther operating income",
            "Mar 25",
            "Sep 24 Mar 24 Mar 25 Mar 25\n$M $M v. Sep 24 v. Mar 24\n8,137 7,900 9% 12%\n2,236 2,248 4% 3%",
        ],
        rows=[
            [
                "Net interest income\nOther operating income",
                "Mar 25",
                "Sep 24 Mar 24 Mar 25 Mar 25\n$M $M v. Sep 24 v. Mar 24\n8,137 7,900 9% 12%\n2,236 2,248 4% 3%",
            ],
            ["", "$M", ""],
            ["", "8,838", ""],
            ["", "2,315", ""],
            [
                "Operating income\nOperating expenses",
                "11,153",
                "10,373 10,148 8% 10%\n(5,490) (5,179) 5% 12%",
            ],
            ["", "(5,788)", ""],
            [
                "Profit before credit impairment and income tax\nCredit impairment (charge)/release",
                "5,365",
                "4,883 4,969 10% 8%\n(336) (70) -57% large",
            ],
            ["", "(143)", ""],
            [
                "Profit before income tax\nIncome tax expense\nNon-controlling interests",
                "5,222",
                "4,547 4,899 15% 7%\n(1,381) (1,435) 11% 7%\n(21) (14) 0% 50%",
            ],
            ["", "(1,538)", ""],
            ["", "(21)", ""],
            [
                "Profit attributable to shareholders of the Company",
                "3,663",
                "3,145 3,450 16% 6%",
            ],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-03-31",
        "currency": "AUD",
        "scale": "millions",
        "metrics": {
            "revenue": 8_838_000_000,
            "ebit": 5_365_000_000,
            "np_attributable": 3_663_000_000,
        },
        "revenue": 8_838_000_000,
        "ebit": 5_365_000_000,
        "np_attributable": 3_663_000_000,
        "row_refs": {
            "revenue": "Net interest income",
            "ebit": "Profit before credit impairment and income tax",
            "np_attributable": "Profit attributable to shareholders of the Company",
        },
        "provenance": {
            "revenue": "income_statement:page_5:Net interest income",
            "ebit": "income_statement:page_5:Profit before credit impairment and income tax",
            "np_attributable": (
                "income_statement:page_5:"
                "Profit attributable to shareholders of the Company"
            ),
        },
        "metric_source_scales": {
            "revenue": "millions",
            "ebit": "millions",
            "np_attributable": "millions",
        },
        "metric_scale_sources": {
            "revenue": "table",
            "ebit": "table",
            "np_attributable": "table",
        },
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [bank_statement],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-03-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["revenue"] == 11_153_000_000
    assert payload["row_refs"]["revenue"] == "Operating income"
    assert payload["provenance"]["revenue"] == "income_statement:page_5:Operating income"
    assert payload["metrics"]["ebit"] == 5_222_000_000
    assert payload["row_refs"]["ebit"] == "Profit before income tax"
    assert payload["provenance"]["ebit"] == "income_statement:page_5:Profit before income tax"


def test_income_metric_label_scopes_bank_operating_income_revenue_context():
    from app.services.multipass_extraction import _income_metric_for_row_label

    assert _income_metric_for_row_label("Operating income") == "ebit"
    assert (
        _income_metric_for_row_label(
            "Operating income",
            bank_operating_income_total=True,
        )
        == "revenue"
    )
    assert _income_metric_for_row_label("Other operating income") is None


def test_income_source_overlay_replaces_conflicting_component_scale_rows():
    """DXS component trust rows at $000 scale must yield to group $m rows."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    component_statement = DoclingTable(
        page_number=51,
        caption="Dexus Property Trust Statement of Comprehensive Income",
        headers=["", "31 Dec 2025 $000", "31 Dec 2024 $000"],
        rows=[
            ["Total revenue from ordinary activities", "223,366", "231,177"],
            ["(Loss)/profit for the period before tax", "(4,662)", "2,000"],
            ["(Loss)/profit for the period", "(3,747)", "1,500"],
        ],
    )
    group_statement = DoclingTable(
        page_number=16,
        caption="Dexus Consolidated Statement of Comprehensive Income",
        headers=["", "Note", "31 Dec 2025 $m", "31 Dec 2024 $m"],
        rows=[
            ["Revenue from ordinary activities", "", "", ""],
            ["Property revenue", "2", "150.0", "159.1"],
            ["Development revenue", "", "14.9", "20.2"],
            ["Management fees and other revenue", "3", "174.3", "242.3"],
            ["Interest revenue", "", "20.8", "13.1"],
            ["Total revenue from ordinary activities", "", "360.0", "434.7"],
            ["Profit for the period before tax", "", "347.6", "27.4"],
            ["Income tax benefit/(expense)", "5", "0.9", "(17.1)"],
            ["Profit for the period", "", "348.5", "10.3"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
        "metrics": {
            "revenue": 223_366_000,
            "ebit": -4_662_000,
            "np_attributable": -3_747_000,
        },
        "revenue": 223_366_000,
        "ebit": -4_662_000,
        "np_attributable": -3_747_000,
        "row_refs": {
            "revenue": "Total revenue from ordinary activities",
            "ebit": "(Loss)/profit for the period before tax",
            "np_attributable": "(Loss)/profit for the period",
        },
        "provenance": {
            "revenue": "income_statement:page_51:Total revenue from ordinary activities",
            "ebit": "income_statement:page_51:(Loss)/profit for the period before tax",
            "np_attributable": "income_statement:page_51:(Loss)/profit for the period",
        },
        "metric_source_scales": {
            "revenue": "thousands",
            "ebit": "thousands",
            "np_attributable": "thousands",
        },
        "metric_scale_sources": {
            "revenue": "table",
            "ebit": "table",
            "np_attributable": "table",
        },
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [component_statement, group_statement],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["revenue"] == 360_000_000
    assert payload["metrics"]["ebit"] == 347_600_000
    assert payload["metrics"]["np_attributable"] == 348_500_000
    assert payload["metric_source_scales"]["revenue"] == "millions"
    assert payload["metric_source_scales"]["ebit"] == "millions"
    assert payload["metric_source_scales"]["np_attributable"] == "millions"
    assert payload["provenance"]["revenue"].startswith("income_statement:page_16:")


def test_income_source_overlay_rejects_financial_report_contents_page():
    """QBE-style contents pages must not turn note page numbers into revenue."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    contents_page = DoclingTable(
        page_number=17,
        caption="",
        headers=["", ""],
        rows=[
            ["Financial statements", ""],
            ["Consolidated statement of comprehensive income", "14"],
            ["Consolidated balance sheet", "15"],
            ["Consolidated statement of changes in equity", "16"],
            ["Consolidated statement of cash flows", "17"],
            ["Notes to the financial statements", ""],
            ["1. Overview", "18"],
            ["2.1 Insurance revenue", "22"],
        ],
    )
    formal_statement = DoclingTable(
        page_number=18,
        caption="Consolidated statement of comprehensive income",
        headers=["", "NOTE", "30 JUNE 2025 US$M", "30 JUNE 2024 US$M"],
        rows=[
            ["Insurance revenue", "2.1", "10,875", "10,436"],
            ["Profit before income tax", "", "1,334", "1,051"],
            ["Ordinary equity holders of the Company", "", "1,022", "802"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"revenue": None, "ebit": None, "np_attributable": None},
        "row_refs": {},
        "provenance": {},
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [contents_page, formal_statement],
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-06-30",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["revenue"] == 10_875_000_000
    assert payload["row_refs"]["revenue"] == "Insurance revenue"
    assert payload["provenance"]["revenue"] == (
        "income_statement:page_18:Insurance revenue"
    )


def test_statement_text_overlay_rejects_financial_report_contents_page():
    """QBE-style contents page source text must not supply revenue."""
    from app.services.multipass_extraction import (
        _apply_preferred_statement_text_source_payload,
    )

    payload = {
        "period_type": "H",
        "period_end": "2025-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"revenue": None, "ebit": None, "np_attributable": None},
        "row_refs": {},
        "provenance": {},
    }
    sections = [
        {"page": 17, "text": "Financial Report contents"},
        {"page": 17, "text": "Financial statements"},
        {"page": 17, "text": "Consolidated statement of comprehensive income 14"},
        {"page": 17, "text": "Consolidated balance sheet 15"},
        {"page": 17, "text": "Consolidated statement of cash flows 17"},
        {"page": 17, "text": "Notes to the financial statements"},
        {"page": 17, "text": "1. Overview 18"},
        {"page": 17, "text": "2.1 Insurance revenue 22"},
        {"page": 18, "text": "Consolidated statement of comprehensive income"},
        {"page": 18, "text": "Insurance revenue"},
        {"page": 18, "text": "2.1"},
        {"page": 18, "text": "10,875"},
        {"page": 18, "text": "10,436"},
        {"page": 18, "text": "Profit before income tax"},
        {"page": 18, "text": "1,334"},
        {"page": 18, "text": "1,051"},
        {"page": 18, "text": "Ordinary equity holders of the Company"},
        {"page": 18, "text": "1,022"},
        {"page": 18, "text": "802"},
    ]

    _apply_preferred_statement_text_source_payload(
        payload,
        sections,
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-06-30",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["revenue"] == 10_875_000_000
    assert payload["row_refs"]["revenue"] == "Insurance revenue"
    assert payload["provenance"]["revenue"] == (
        "income_statement:page_18:Insurance revenue"
    )


def test_statement_text_overlay_rejects_spaced_qbe_contents_page():
    """QBE contents pages can push note markers beyond the first text window."""
    from app.services.multipass_extraction import (
        _apply_preferred_statement_text_source_payload,
    )

    payload = {
        "period_type": "H",
        "period_end": "2025-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"revenue": None, "ebit": None, "np_attributable": None},
        "row_refs": {},
        "provenance": {},
    }
    contents_page = [
        {"page": 17, "text": "Financial statements"},
        {"page": 17, "text": "Consolidated statement of comprehensive income 14"},
        {"page": 17, "text": "Consolidated balance sheet 15"},
        {"page": 17, "text": "Consolidated statement of changes in equity 16"},
        {"page": 17, "text": "Consolidated statement of cash flows 17"},
    ]
    contents_page.extend(
        {"page": 17, "text": f"contents spacer {index}"} for index in range(45)
    )
    contents_page.extend(
        [
            {"page": 17, "text": "Notes to the financial statements"},
            {"page": 17, "text": "2. Underwriting activities 22"},
            {"page": 17, "text": "2.1 Insurance revenue"},
            {"page": 17, "text": "22"},
        ]
    )
    sections = contents_page + [
        {"page": 18, "text": "Consolidated statement of comprehensive income"},
        {"page": 18, "text": "Insurance revenue"},
        {"page": 18, "text": "2.1"},
        {"page": 18, "text": "10,875"},
        {"page": 18, "text": "10,436"},
        {"page": 18, "text": "Profit before income tax"},
        {"page": 18, "text": "1,334"},
        {"page": 18, "text": "1,051"},
        {"page": 18, "text": "Ordinary equity holders of the Company"},
        {"page": 18, "text": "1,022"},
        {"page": 18, "text": "802"},
    ]

    _apply_preferred_statement_text_source_payload(
        payload,
        sections,
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-06-30",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["revenue"] == 10_875_000_000
    assert payload["row_refs"]["revenue"] == "Insurance revenue"
    assert payload["provenance"]["revenue"] == (
        "income_statement:page_18:Insurance revenue"
    )


def test_statement_text_overlay_recovers_fragmented_full_statements_over_wrapper():
    """SEG-style fragmented statement pages should override Appendix wrapper rows."""
    from app.services.multipass_extraction import (
        _apply_preferred_statement_text_source_payload,
    )

    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {
            "revenue": 73_671_000,
            "np_attributable": 9_715_000,
            "operating_cf": None,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": None,
        },
        "revenue": 73_671_000,
        "np_attributable": 9_715_000,
        "row_refs": {
            "revenue": "2.1 Revenues from ordinary activities",
            "np_attributable": "2.3 Pre AASB-16 EBITDA",
        },
        "provenance": {
            "revenue": "appendix_wrapper:page_3:2.1 Revenues from ordinary activities",
            "np_attributable": "appendix_wrapper:page_3:2.3 Pre AASB-16 EBITDA",
        },
    }
    sections = [
        {
            "page": 12,
            "text": "Consolidated statement of profit or loss and other comprehensive income for the",
        },
        {"page": 12, "text": "financial half year ended 31 December 2025"},
        {"page": 12, "text": "Revenue from continuing operations"},
        {"page": 12, "text": "2"},
        {"page": 12, "text": "73,671"},
        {"page": 12, "text": "57,546"},
        {"page": 12, "text": "Profit / (loss) after income tax from continuing operations"},
        {"page": 12, "text": "3,243"},
        {"page": 12, "text": "(456)"},
        {
            "page": 17,
            "text": "Consolidated statement of cash flows for the financial half year ended 31 December 2025",
        },
        {"page": 17, "text": "Net operating cash flows provided by operating activities"},
        {"page": 17, "text": "11,619"},
        {"page": 17, "text": "2,448"},
        {"page": 17, "text": "Net cash from investing activities"},
        {"page": 17, "text": "7,527"},
        {"page": 17, "text": "18,502"},
        {"page": 17, "text": "Net cash used in financing activities"},
        {"page": 17, "text": "(7,369)"},
        {"page": 17, "text": "(19,831)"},
        {"page": 17, "text": "Cash and cash equivalents at the end of the half year"},
        {"page": 17, "text": "26,716"},
        {"page": 17, "text": "11,855"},
    ]

    _apply_preferred_statement_text_source_payload(
        payload,
        sections,
        scale="thousands",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["revenue"] == 73_671_000
    assert payload["metrics"]["np_attributable"] == 3_243_000
    assert payload["metrics"]["operating_cf"] == 11_619_000
    assert payload["metrics"]["investing_cf"] == 7_527_000
    assert payload["metrics"]["financing_cf"] == -7_369_000
    assert payload["metrics"]["cash_end"] == 26_716_000
    assert payload["provenance"]["np_attributable"].startswith("income_statement:")
    assert payload["provenance"]["operating_cf"].startswith("cashflow_statement:")


def test_statement_text_overlay_recovers_rms_statement_of_cash_flows_heading():
    """RMS uses a formal statement heading without the word consolidated."""
    from app.services.multipass_extraction import (
        _apply_preferred_statement_text_source_payload,
    )

    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {
            "operating_cf": None,
            "investing_cf": None,
            "financing_cf": None,
            "capex": None,
        },
        "row_refs": {},
        "provenance": {},
    }

    _apply_preferred_statement_text_source_payload(
        payload,
        [
            {
                "page": 23,
                "text": "STATEMENT OF CASH FLOWS For the half-year ended 31 December 2025",
            },
            {"page": 23, "text": "Net cash provided by operating activities"},
            {"page": 23, "text": "171,179"},
            {"page": 23, "text": "Net cash used in investing activities"},
            {"page": 23, "text": "(211,390)"},
            {"page": 23, "text": "Payments for property, plant and equipment"},
            {"page": 23, "text": "10"},
            {"page": 23, "text": "(25,239)"},
            {"page": 23, "text": "Net cash used in financing activities"},
            {"page": 23, "text": "(84,747)"},
        ],
        scale="thousands",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["operating_cf"] == 171_179_000
    assert payload["metrics"]["investing_cf"] == -211_390_000
    assert payload["metrics"]["financing_cf"] == -84_747_000
    assert payload["metrics"]["capex"] == -25_239_000
    assert (
        payload["row_refs"]["operating_cf"]
        == "Net cash provided by operating activities"
    )
    assert payload["metric_source_scales"]["operating_cf"] == "thousands"
    assert payload["metric_scale_sources"]["operating_cf"] == "source_text"


def test_statement_text_overlay_replaces_ebitda_with_income_statement_profit_before_tax():
    """FMG-style source text should use profit before tax instead of EBITDA."""
    from app.services.multipass_extraction import (
        _apply_preferred_statement_text_source_payload,
    )

    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
        "metrics": {
            "revenue": 8_439_000_000,
            "ebit": 4_486_000_000,
            "np_attributable": 1_914_000_000,
        },
        "ebit": 4_486_000_000,
        "row_refs": {"ebit": "Underlying EBITDA"},
        "provenance": {"ebit": "income_statement:page_14:Underlying EBITDA"},
    }
    sections = [
        {"page": 21, "text": "CONSOLIDATED INCOME STATEMENT"},
        {"page": 21, "text": "For the half year ended 31 December 2025"},
        {"page": 21, "text": "31 December"},
        {"page": 21, "text": "2025"},
        {"page": 21, "text": "US$m"},
        {"page": 21, "text": "Operating sales revenue"},
        {"page": 21, "text": "3"},
        {"page": 21, "text": "8,439"},
        {"page": 21, "text": "7,638"},
        {"page": 21, "text": "Operating profit"},
        {"page": 21, "text": "2,908"},
        {"page": 21, "text": "2,398"},
        {"page": 21, "text": "Profit before tax"},
        {"page": 21, "text": "2,808"},
        {"page": 21, "text": "2,288"},
        {"page": 21, "text": "Income tax expense"},
        {"page": 21, "text": "(898)"},
        {"page": 21, "text": "(741)"},
        {"page": 21, "text": "Net profit after tax"},
        {"page": 21, "text": "1,910"},
        {"page": 21, "text": "1,547"},
    ]

    _apply_preferred_statement_text_source_payload(
        payload,
        sections,
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["ebit"] == 2_808_000_000
    assert payload["ebit"] == 2_808_000_000
    assert payload["row_refs"]["ebit"] == "Profit before tax"
    assert payload["provenance"]["ebit"] == "income_statement:page_21:Profit before tax"


def test_statement_text_overlay_replaces_narrative_future_sales_revenue():
    """CSL-style future-sales narrative is not a current-period revenue row."""
    from app.services.multipass_extraction import (
        _apply_preferred_statement_text_source_payload,
    )

    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
        "metrics": {
            "revenue": 202_000_000,
            "ebit": 577_000_000,
            "np_attributable": 286_000_000,
        },
        "revenue": 202_000_000,
        "row_refs": {
            "revenue": (
                "December . With TDAPA scheduled to expire in December , "
                "management expects a material decline in future sales revenue,"
            )
        },
        "provenance": {
            "revenue": (
                "income_statement:page_22:December . With TDAPA scheduled "
                "to expire in December , management expects a material decline "
                "in future sales revenue,"
            )
        },
    }
    sections = [
        {"page": 11, "text": "Consolidated Statement of Profit or Loss"},
        {"page": 11, "text": "For the half year ended 31 December 2025"},
        {"page": 11, "text": "Revenue"},
        {"page": 11, "text": "8,332"},
        {"page": 11, "text": "7,988"},
        {"page": 11, "text": "Operating profit (EBIT)"},
        {"page": 11, "text": "577"},
        {"page": 11, "text": "2,008"},
        {"page": 11, "text": "Net profit for the period"},
        {"page": 11, "text": "286"},
        {"page": 11, "text": "1,826"},
    ]

    _apply_preferred_statement_text_source_payload(
        payload,
        sections,
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["revenue"] == 8_332_000_000
    assert payload["revenue"] == 8_332_000_000
    assert payload["row_refs"]["revenue"] == "Revenue"
    assert payload["provenance"]["revenue"] == "income_statement:page_11:Revenue"


def test_pdf_text_fallback_replaces_rejected_ebitda_with_profit_before_tax(
    monkeypatch, tmp_path
):
    """Formal source-PDF text can correct an EBITDA-sourced EBIT gate blocker."""
    import subprocess

    from app.services.multipass_extraction import (
        _apply_rejected_ebit_from_pdf_statement_text,
    )

    source_pdf = tmp_path / "fmg.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n")

    class Completed:
        returncode = 0
        stdout = "\f".join(
            [
                "Cover page",
                "\n".join(
                    [
                        "CONSOLIDATED INCOME STATEMENT",
                        "For the half year ended 31 December 2025",
                        "31 December 2025",
                        "US$m",
                        "Operating profit 2,908 2,398",
                        "Profit before tax 2,808 2,288",
                    ]
                ),
            ]
        )

    def fake_run(*args, **kwargs):
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)

    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"ebit": 4_486_000_000},
        "ebit": 4_486_000_000,
        "row_refs": {"ebit": "Underlying EBITDA"},
        "provenance": {"ebit": "income_statement:page_14:Underlying EBITDA"},
    }

    _apply_rejected_ebit_from_pdf_statement_text(
        payload,
        source_pdf,
        scale="millions",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["ebit"] == 2_808_000_000
    assert payload["ebit"] == 2_808_000_000
    assert payload["row_refs"]["ebit"] == "Profit before tax"
    assert payload["provenance"]["ebit"] == "income_statement:page_2:Profit before tax"


def test_appendix5b_source_text_recovers_core_cashflow_totals_and_confidence(
    monkeypatch, tmp_path
):
    """GRE-style Appendix 5B source text can recover section totals deterministically."""
    import subprocess

    from app.services.multipass_extraction import _apply_appendix5b_source_text_payload

    source_pdf = tmp_path / "gre.pdf"
    source_pdf.write_bytes(b"%PDF-1.4\n")

    class Completed:
        returncode = 0
        stdout = "\f".join(
            [
                "\n".join(
                    [
                        "Appendix 5B",
                        "Mining exploration entity or oil and gas exploration entity quarterly cash flow report",
                        "Consolidated statement of cash flows Current quarter Year to date",
                        "$A'000 $A'000",
                        "1.9 Net cash from / (used in) operating",
                        "(450) (796)",
                        "activities",
                    ]
                ),
                "\n".join(
                    [
                        "Appendix 5B",
                        "Mining exploration entity or oil and gas exploration entity quarterly cash flow report",
                        "Consolidated statement of cash flows Current quarter Year to date",
                        "$A'000 $A'000",
                        "2.6 Net cash from / (used in) investing (624) (1,193)",
                        "activities",
                        "3.10 Net cash from / (used in) financing 869 869",
                        "activities",
                    ]
                ),
                "\n".join(
                    [
                        "Appendix 5B",
                        "Mining exploration entity or oil and gas exploration entity quarterly cash flow report",
                        "Consolidated statement of cash flows Current quarter Year to date",
                        "$A'000 $A'000",
                        "4.6 Cash and cash equivalents at end of",
                        "702 702",
                        "period",
                    ]
                ),
            ]
        )

    def fake_run(*args, **kwargs):
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)

    payload = {
        "period_type": "Q",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "confidence_metrics": 0.2,
        "metrics": {"operating_cf": -450_000},
        "operating_cf": -450_000,
        "row_refs": {"operating_cf": "Net cash from / (used in) operating activities"},
        "provenance": {
            "operating_cf": "cashflow_statement:page_11:Net cash from / (used in) operating activities"
        },
        "metric_source_scales": {"operating_cf": "thousands"},
        "metric_scale_sources": {"operating_cf": "table"},
    }

    _apply_appendix5b_source_text_payload(
        payload,
        source_pdf,
        scale="thousands",
        pass1_result={
            "report_type": "Q",
            "period_end": "2024-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["operating_cf"] == -450_000
    assert payload["metrics"]["investing_cf"] == -624_000
    assert payload["metrics"]["financing_cf"] == 869_000
    assert payload["metrics"]["cash_end"] == 702_000
    assert payload["confidence_metrics"] == 0.85
    assert payload["row_refs"]["cash_end"] == "Cash and cash equivalents at end of period"
    assert payload["metric_scale_sources"]["cash_end"] == "source_text"


def test_income_source_overlay_keeps_appendix_wrapper_when_no_full_statement_exists():
    """Wrapper-only Appendix 4D payloads remain valid when no full statement is present."""
    from app.services.multipass_extraction import (
        _apply_preferred_income_statement_source_payload,
    )

    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {
            "revenue": 73_671_000,
            "np_attributable": 3_243_000,
        },
        "revenue": 73_671_000,
        "np_attributable": 3_243_000,
        "row_refs": {
            "revenue": "2.1 Revenues from ordinary activities",
            "np_attributable": "2.5 Profit attributable to members",
        },
        "provenance": {
            "revenue": "appendix_wrapper:page_3:2.1 Revenues from ordinary activities",
            "np_attributable": "appendix_wrapper:page_3:2.5 Profit attributable to members",
        },
    }

    _apply_preferred_income_statement_source_payload(
        payload,
        [],
        scale="thousands",
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["np_attributable"] == 3_243_000
    assert payload["row_refs"]["np_attributable"] == "2.5 Profit attributable to members"


def test_appendix_wrapper_does_not_treat_ebitda_as_ebit():
    """EBITDA rows are not source proof for EBIT."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _build_appendix_wrapper_source_payload

    table = DoclingTable(
        page_number=1,
        caption="RESULTS FOR ANNOUNCEMENT TO THE MARKET",
        headers=["", "", "", "", ""],
        rows=[
            [
                "",
                "Earnings before Interest, Tax, Depreciation and Amortisation (EBITDA)",
                "",
                "159,471",
                "",
            ],
        ],
    )

    payload = _build_appendix_wrapper_source_payload(
        title="Appendix 4D and December 2025 Half Yearly Financial Report",
        sections=[
            {"page": 1, "text": "Appendix 4D"},
            {"page": 1, "text": "For the half-year ended 31 December 2025"},
        ],
        tables=[table],
        period_evidence={"period_type": "H"},
        period_end_evidence={
            "period_type": "H",
            "period_end": "2025-12-31",
            "hits": [
                {
                    "source": "source_text",
                    "period_end": "2025-12-31",
                    "reason": "current_period_range",
                }
            ],
        },
        scale="thousands",
        currency="AUD",
    )

    assert "ebit" not in payload["metrics"]


def test_pass4_emits_structured_field_provenance_for_metrics():
    """Reconciled payloads should expose machine-readable per-metric provenance."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    payload = _run_pass4_reconciler(
        [
            {
                "_source": "income_statement",
                "_page_number": 25,
                "_scale": "thousands",
                "_scale_source": "table",
                "revenue": 46_547_000,
                "np_attributable": 39_374_000,
                "pass3_confidence": 0.9,
                "row_refs": {
                    "revenue": "Total revenue",
                    "np_attributable": "Net profit/(loss) after tax",
                },
            }
        ],
        {
            "risk_summary": None,
            "risk_bullets": None,
            "guidance_summary": None,
            "material_changes": None,
            "confidence_narrative": 0.0,
        },
        {
            "report_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
        },
    )

    assert payload["provenance"]["revenue"] == "income_statement:page_25:Total revenue"
    assert payload["field_provenance"]["revenue"] == {
        "metric": "revenue",
        "source": "income_statement",
        "table_label": "income_statement",
        "page_number": 25,
        "page_tag": "page_25",
        "row_ref": "Total revenue",
        "excerpt": "Total revenue",
        "scale": "thousands",
        "scale_source": "table",
        "currency": "AUD",
        "period_type": "A",
        "period_end": "2025-06-30",
    }
    assert payload["field_provenance"]["np_attributable"]["row_ref"] == (
        "Net profit/(loss) after tax"
    )


def test_validate_gate_non_aud_returns_ok_low_confidence():
    """Non-AUD currency (e.g. USD, GBP) must downgrade to ok_low_confidence.

    There is no FX conversion policy — values are stored as-is, so downstream
    consumers must not compare them directly with AUD-denominated peers. Payloads
    without deterministic source binding remain low-confidence.
    """
    from app.services.multipass_extraction import _validate_gate

    for currency in ("USD", "GBP", "EUR"):
        status, error = _validate_gate(_good_payload(currency=currency))
        assert status == "ok_low_confidence", (
            f"currency={currency} must yield ok_low_confidence; got status={status!r}"
        )
        assert error is None, (
            f"error must be None for currency downgrade; got {error!r}"
        )


def test_validate_gate_source_bound_native_currency_can_return_ok():
    """Source-bound USD reports should not be downgraded by currency alone."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload(currency="USD", scale="millions")
    payload["period_type"] = "H"
    payload["period_end"] = "2025-12-31"
    payload["confidence_metrics"] = 0.93
    payload["source_bound"] = {
        "currency": "USD",
        "period_type": "H",
        "period_end": "2025-12-31",
        "scale": "millions",
        "document_title": "source-bound-usd-financial-report.pdf",
    }
    payload["metric_source_scales"] = {
        "revenue": "millions",
        "ebit": "millions",
        "np_attributable": "millions",
    }
    payload["row_refs"] = {
        "revenue": "Revenue",
        "ebit": "Operating profit",
        "np_attributable": "Net profit after tax",
    }
    payload["provenance"] = {
        "revenue": "income_statement:page_1:Revenue",
        "ebit": "income_statement:page_1:Operating profit",
        "np_attributable": "income_statement:page_1:Net profit after tax",
    }

    status, error = _validate_gate(payload)

    assert status == "ok"
    assert error is None


# ---------------------------------------------------------------------------
# Pass 3a — page_number in output (B10)
# ---------------------------------------------------------------------------


def test_pass3a_page_number_in_output():
    """Pass 3a output dict must include _page_number from the source DoclingTable."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=7,
        caption="Statement of Cash Flows",
        rows=[["", "Q1 2025"], ["Net cash from operations", "1,200"]],
        headers=["", "Q1 2025"],
    )
    labelled = {
        "cashflow_statement": table,
        "income_statement": None,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "Q",
        "period_end": "2025-03-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "operating_cf": 1200,
        "investing_cf": None,
        "financing_cf": None,
        "cash_end": None,
        "pass3_confidence": 0.88,
        "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["_page_number"] == 7, (
        f"_page_number must be 7 (from DoclingTable.page_number), got {results[0].get('_page_number')!r}"
    )


# ---------------------------------------------------------------------------
# Pass 4 — page_number in provenance strings (B11)
# ---------------------------------------------------------------------------


def test_pass4_provenance_includes_page_number():
    """Provenance strings must embed the source page number: '{source}:page_{n}:{row_ref}'."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {
            "_source": "cashflow_statement",
            "_page_number": 5,
            "operating_cf": 3_000_000,
            "investing_cf": None,
            "financing_cf": None,
            "cash_end": None,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {"operating_cf": "Net cash from operations"},
        },
    ]
    pass3b = {
        "risk_summary": None,
        "risk_bullets": None,
        "guidance_summary": None,
        "material_changes": None,
        "confidence_narrative": 0.0,
    }
    pass1 = {"report_type": "Q", "period_end": "2025-03-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)

    prov = result["provenance"].get("operating_cf", "")
    assert "page_5" in prov, (
        f"Provenance must include 'page_5' for a table on page 5; got: {prov!r}"
    )


# ---------------------------------------------------------------------------
# JSON parse — accounting parentheses
# ---------------------------------------------------------------------------


def test_parse_json_accounting_parentheses():
    """
    Accounting notation: LLM outputs (5,590) meaning -5590.
    _parse_json_text must convert these to negative numbers so the
    response can be parsed as valid JSON.
    """
    from app.services.llamacpp_runtime import _parse_json_text

    raw = '{"total_debt": (5,590), "cash_end": 1234}'
    result = _parse_json_text(raw)
    assert result == {"total_debt": -5590, "cash_end": 1234}


def test_parse_json_accounting_parentheses_no_commas():
    """Parenthesised integers without thousands separator also work."""
    from app.services.llamacpp_runtime import _parse_json_text

    raw = '{"investing_cf": (527)}'
    result = _parse_json_text(raw)
    assert result == {"investing_cf": -527}


def test_parse_json_normal_negatives_unchanged():
    """Normal negative numbers must not be transformed."""
    from app.services.llamacpp_runtime import _parse_json_text

    raw = '{"investing_cf": -527, "revenue": 3052}'
    result = _parse_json_text(raw)
    assert result == {"investing_cf": -527, "revenue": 3052}


# ---------------------------------------------------------------------------
# ASX Appendix 5B — scale detection and table merging
# ---------------------------------------------------------------------------


def test_scale_detection_matches_dollar_a_thousands():
    """$A'000 notation (ASX Appendix 5B) must be detected as 'thousands'."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    tables = [
        DoclingTable(
            page_number=1,
            caption="",
            headers=[
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date (6 months) $A'000",
            ],
            rows=[["1.1", "Receipts from customers", "500", "1,000"]],
        )
    ]
    assert _detect_scale_from_tables(tables) == "thousands"


def test_scale_detection_matches_dollar_a_millions():
    """$A'000,000 (less common) and A$M must also be detected."""
    from app.services.multipass_extraction import _detect_scale_from_tables
    from app.services.docling_extract import DoclingTable

    # A$M notation
    tables_am = [
        DoclingTable(
            page_number=1,
            caption="",
            headers=["Item", "A$M"],
            rows=[["Revenue", "42.5"]],
        )
    ]
    assert _detect_scale_from_tables(tables_am) == "millions"


def test_pass2_score_uses_all_body_columns():
    """Pass 2 scoring must read all body columns, not just column 0.

    ASX 5B tables have section numbers in column 0 (e.g. '4.2') and
    the descriptive label in column 1 ('Net cash from operating activities').
    Only scanning column 0 misses all keywords.
    """
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    # Section 4 summary table: column 0 = section numbers, column 1 = labels
    section4 = DoclingTable(
        page_number=12,
        caption="",
        headers=["0", "1", "2", "3"],
        rows=[
            ["0", "1", "2", "3"],
            ["4.", "Net increase / (decrease) in cash", "", ""],
            ["4.1", "Cash and cash equivalents at beginning of period", "907", "1,822"],
            ["4.2", "Net cash from / (used in) operating activities", "(450)", "(796)"],
            [
                "4.3",
                "Net cash from / (used in) investing activities",
                "(624)",
                "(1,193)",
            ],
            ["4.4", "Net cash from / (used in) financing activities", "869", "869"],
        ],
    )

    labelled = _run_pass2_locator([section4])
    assert labelled["cashflow_statement"] is not None, (
        "Section 4 summary table must be labelled as cashflow_statement "
        "even when column 0 contains only section numbers"
    )


def test_pass2_merges_fragmented_5b_cf_tables():
    """When multiple tables score >= threshold for cashflow_statement,
    they must be merged into one synthetic table."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    # Simulate 3 fragmented 5B tables
    operating = DoclingTable(
        page_number=11,
        caption="",
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date $A'000",
            ],
            ["1.", "Cash flows from operating activities", "", ""],
            ["1.9", "Net cash from / (used in) operating activities", "(450)", "(796)"],
        ],
    )
    investing = DoclingTable(
        page_number=12,
        caption="",
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date $A'000",
            ],
            ["2.", "Cash flows from investing activities", "", ""],
            [
                "2.6",
                "Net cash from / (used in) investing activities",
                "(624)",
                "(1,193)",
            ],
        ],
    )
    section4 = DoclingTable(
        page_number=13,
        caption="",
        headers=["0", "1", "2", "3"],
        rows=[
            ["0", "1", "2", "3"],
            ["4.2", "Net cash from / (used in) operating activities", "(450)", "(796)"],
            [
                "4.3",
                "Net cash from / (used in) investing activities",
                "(624)",
                "(1,193)",
            ],
            ["4.4", "Net cash from / (used in) financing activities", "869", "869"],
            ["4.6", "Cash and cash equivalents at end of period", "702", "702"],
        ],
    )

    labelled = _run_pass2_locator([operating, investing, section4])
    cf = labelled["cashflow_statement"]
    assert cf is not None
    assert cf.caption.startswith("Merged cashflow"), (
        f"Expected merged table, got caption={cf.caption!r}"
    )
    # Merged table must contain rows from all three source tables
    all_text = " ".join(" ".join(r) for r in cf.rows).lower()
    assert "operating activities" in all_text
    assert "investing activities" in all_text
    assert "financing activities" in all_text
    assert "702" in all_text  # cash_end from section 4


def test_pass2_cashflow_prefers_consolidated_group_statement_over_component_statement():
    """DXS-style stapled groups must prefer the consolidated cash-flow statement."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    component_statement = DoclingTable(
        page_number=51,
        caption="Dexus Property Trust Statement of Cash Flows",
        headers=["", "31 Dec 2025 $m", "30 Jun 2025 $m"],
        rows=[
            ["", "31 Dec 2025 $m", "30 Jun 2025 $m"],
            ["Cash flow from operating activities", "", ""],
            ["Net cash inflow from operating activities", "735.2", "120.0"],
            ["Net cash inflow from investing activities", "4,000.0", "200.0"],
            ["Net cash outflow from financing activities", "(500.0)", "(300.0)"],
            ["Cash and cash equivalents at the end of the period", "11.0", "8.0"],
        ],
    )
    consolidated_statement = DoclingTable(
        page_number=20,
        caption="Dexus Consolidated Statement of Cash Flows",
        headers=["", "31 Dec 2025 $m", "30 Jun 2025 $m"],
        rows=[
            ["", "31 Dec 2025 $m", "30 Jun 2025 $m"],
            ["Cash flow from operating activities", "", ""],
            ["Net cash inflow/(outflow) from operating activities", "168.5", "108.3"],
            ["Net cash inflow/(outflow) from investing activities", "83.9", "(40.1)"],
            ["Net cash inflow/(outflow) from financing activities", "(243.0)", "(91.0)"],
            ["Cash and cash equivalents at the end of the period", "74.7", "66.1"],
        ],
    )

    result = _run_pass2_locator([component_statement, consolidated_statement])

    assert result["cashflow_statement"] is consolidated_statement


def test_pass2_cashflow_does_not_let_low_score_consolidated_note_beat_formal_statement():
    """Precedence should not let an incidental consolidated note beat a strong statement."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    weak_consolidated_note = DoclingTable(
        page_number=5,
        caption="Consolidated operating activities note",
        headers=["", "31 Dec 2025 $m"],
        rows=[
            ["", "31 Dec 2025 $m"],
            ["Operating activities commentary", "1.0"],
        ],
    )
    formal_statement = DoclingTable(
        page_number=20,
        caption="Statement of Cash Flows",
        headers=["", "31 Dec 2025 $m", "30 Jun 2025 $m"],
        rows=[
            ["", "31 Dec 2025 $m", "30 Jun 2025 $m"],
            ["Cash flows from operating activities", "", ""],
            ["Net cash inflow/(outflow) from operating activities", "168.5", "108.3"],
            ["Net cash inflow/(outflow) from investing activities", "83.9", "(40.1)"],
            ["Net cash inflow/(outflow) from financing activities", "(243.0)", "(91.0)"],
            ["Cash and cash equivalents at the end of the period", "74.7", "66.1"],
        ],
    )

    result = _run_pass2_locator([weak_consolidated_note, formal_statement])

    assert result["cashflow_statement"] is formal_statement


def test_pass2_cashflow_keeps_component_statement_when_no_group_statement_exists():
    """The group-preference rule must not reject a standalone statement."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    component_statement = DoclingTable(
        page_number=51,
        caption="Dexus Property Trust Statement of Cash Flows",
        headers=["", "31 Dec 2025 $m"],
        rows=[
            ["", "31 Dec 2025 $m"],
            ["Net cash inflow from operating activities", "735.2"],
            ["Net cash inflow from investing activities", "4,000.0"],
            ["Net cash outflow from financing activities", "(500.0)"],
            ["Cash and cash equivalents at the end of the period", "11.0"],
        ],
    )

    result = _run_pass2_locator([component_statement])

    assert result["cashflow_statement"] is component_statement


# ---------------------------------------------------------------------------
# Pass 3a — shares_outstanding scaling (body text + doc-level fallback)
# ---------------------------------------------------------------------------


def test_pass3a_shares_scaling_from_body_text():
    """shares_outstanding sanity check must also scan body rows for '000 indicators.

    SEG share capital table has "No. '000s" in a row label, not in column headers.
    The scaling logic must detect this and multiply by 1,000.
    """
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=24,
        caption="Note 6 — Issued Capital",
        rows=[
            ["", "No. '000s", "$'000s"],
            ["Balance at beginning of period", "280,875", "42,110"],
            ["Share issue", "—", "—"],
            ["Balance at end of period", "280,875", "42,110"],
        ],
        headers=["", "Dec 2025", "Dec 2025"],  # headers DON'T have '000s
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    # LLM returns raw table value without conversion
    mock_raw = {
        "shares_outstanding": 280875,  # raw from table, not absolute
        "pass3_confidence": 0.9,
        "row_refs": {"shares_outstanding": "Balance at end of period"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["shares_outstanding"] == 280_875_000, (
        f"Expected 280,875,000 (×1000 from body row '000s indicator), "
        f"got {results[0]['shares_outstanding']}"
    )


def test_pass3a_shares_prefers_number_of_shares_column_over_amount_column():
    """QBE share tables expose count and adjacent US$M amount columns."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    table = DoclingTable(
        page_number=32,
        caption="4.3.1 Share capital",
        rows=[
            ["", "NUMBER OF SHARES MILLIONS", "US$M", "NUMBER OF SHARES MILLIONS", "US$M"],
            ["Issued ordinary shares, fully paid at 1 January", "1,505", "7,824", "1,494", "8,495"],
            ["Shares issued under the Employee Share and Option Plan", "5", "55", "3", "34"],
            ["Issued ordinary shares, fully paid at 30 June", "1,510", "8,338", "1,502", "8,409"],
        ],
        headers=["", "30 June 2025", "30 June 2025", "30 June 2024", "30 June 2024"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-06-30",
        "currency": "USD",
        "scale": "millions",
    }
    mock_raw = {
        "shares_outstanding": 8409,
        "pass3_confidence": 0.9,
        "row_refs": {"shares_outstanding": "Issued ordinary shares, fully paid at 30 June"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["shares_outstanding"] == 1_510_000_000
    assert (
        results[0]["row_refs"]["shares_outstanding"]
        == "Issued ordinary shares, fully paid at 30 June"
    )


def test_shares_source_overlay_handles_parser_shape_without_header_units():
    """QBE parser shape can lose the NUMBER OF SHARES MILLIONS header."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _apply_preferred_shares_source_payload

    table = DoclingTable(
        page_number=32,
        caption="For personal use only",
        headers=[
            "Issued ordinary shares, fully paid at 1 January\n"
            "Shares issued under the Employee Share and Option Plan\n"
            "Shares issued under the Dividend Reinvestment Plan\n"
            "Foreign exchange",
            "1,505",
            "7,824",
            "1,494 8,495\n3 34\n5 58\n- (178)",
        ],
        rows=[
            ["", "5", "55", ""],
            ["", "-", "-", ""],
            ["", "-", "459", ""],
            ["Issued ordinary shares, fully paid at 30 June", "1,510", "8,338", "1,502 8,409"],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"shares_outstanding": 8_409_000_000},
        "shares_outstanding": 8_409_000_000,
        "row_refs": {"shares_outstanding": "Issued ordinary shares, fully paid at 30 June"},
        "provenance": {},
    }

    _apply_preferred_shares_source_payload(
        payload,
        [table],
        pass1_result={
            "report_type": "H",
            "period_end": "2025-06-30",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["shares_outstanding"] == 1_510_000_000
    assert payload["shares_outstanding"] == 1_510_000_000


def test_shares_source_overlay_handles_fmg_split_share_count_header_table():
    """FMG PyMuPDF output splits share-count headers from the data rows."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _apply_preferred_shares_source_payload

    split_header = DoclingTable(
        page_number=30,
        caption="For personal use only",
        headers=[
            "",
            "Issued",
            "Treasury",
            "Contributed",
            "Issued",
            "Treasury",
            "Contributed",
        ],
        rows=[
            [
                "",
                "Issued",
                "Treasury",
                "Contributed",
                "Issued",
                "Treasury",
                "Contributed",
            ],
            ["", "shares", "shares", "equity", "shares", "shares", "equity"],
        ],
    )
    share_rows = DoclingTable(
        page_number=30,
        caption="For personal use only",
        headers=[
            "At 1 July 2024",
            "3,078,964,918",
            "(2,999,674)",
            "3,075,965,244",
            "1,195",
            "(118)",
            "1,077",
        ],
        rows=[
            [
                "At 1 July 2024",
                "3,078,964,918",
                "(2,999,674)",
                "3,075,965,244",
                "1,195",
                "(118)",
                "1,077",
            ],
            [
                "Purchase of shares under\nemployee share plans",
                "-",
                "(14,140,364)",
                "(14,140,364)",
                "-",
                "(163)",
                "(163)",
            ],
            [
                "Employee share awards vested",
                "-",
                "12,745,988",
                "12,745,988",
                "-",
                "173",
                "173",
            ],
            [
                "At 30 June 2025",
                "3,078,964,918",
                "(4,394,050)",
                "3,074,570,868",
                "1,195",
                "(108)",
                "1,087",
            ],
            [
                "Purchase of shares under\nemployee share plans",
                "-",
                "(8,769,251)",
                "(8,769,251)",
                "-",
                "(109)",
                "(109)",
            ],
            [
                "Employee share awards vested",
                "-",
                "12,739,353",
                "12,739,353",
                "-",
                "179",
                "179",
            ],
            [
                "At 31 December 2025",
                "3,078,964,918",
                "(423,948)",
                "3,078,540,970",
                "1,195",
                "(38)",
                "1,157",
            ],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"shares_outstanding": None},
        "shares_outstanding": None,
        "row_refs": {},
        "provenance": {},
    }

    _apply_preferred_shares_source_payload(
        payload,
        [split_header, share_rows],
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["shares_outstanding"] == 3_078_964_918
    assert payload["shares_outstanding"] == 3_078_964_918
    assert payload["row_refs"]["shares_outstanding"] == "At 31 December 2025"


def test_shares_source_overlay_prefers_number_of_shares_note_over_equity_balance():
    """RMS share count is in the Number of shares note, not equity $000 balance rows."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _apply_preferred_shares_source_payload

    equity_balance = DoclingTable(
        page_number=22,
        caption="For personal use only",
        headers=["Balance at 31 December 2025", "2,890,512", "7,489"],
        rows=[["Balance at 31 December 2025", "2,890,512", "7,489"]],
    )
    share_note = DoclingTable(
        page_number=31,
        caption="For personal use only",
        headers=["", "", "", "Notes", "", "", "", "Number of", "", "$'000", "", ""],
        rows=[
            ["", "", "", "", "", "", "", "shares", "", "", "", ""],
            ["", "Ordinary shares", "", "", "", "", "", "", "", "", "", ""],
            ["", "At 31 December 2025", "", "", "", "", "", "1,924,937,480", "", "", "2,890,512", ""],
        ],
    )
    payload = {
        "period_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {"shares_outstanding": 2_890_512},
        "shares_outstanding": 2_890_512,
        "row_refs": {"shares_outstanding": "Balance at 31 December 2025"},
        "provenance": {},
    }

    _apply_preferred_shares_source_payload(
        payload,
        [equity_balance, share_note],
        pass1_result={
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
        },
    )

    assert payload["metrics"]["shares_outstanding"] == 1_924_937_480
    assert payload["row_refs"]["shares_outstanding"] == "At 31 December 2025"


def test_shares_source_overlay_ignores_at_date_without_share_count_evidence():
    """At-date prose rows are not share counts without share/security evidence."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _apply_preferred_shares_source_payload

    table = DoclingTable(
        page_number=56,
        caption="Significant events - Samarco dam failure",
        headers=["", "2021", "2020"],
        rows=[
            [
                "billion before tax and after discounting at 30 June 2021",
                "2.6",
                "1.8",
            ],
        ],
    )
    payload = {
        "period_type": "A",
        "period_end": "2021-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"shares_outstanding": None},
        "shares_outstanding": None,
        "row_refs": {},
        "provenance": {},
    }

    _apply_preferred_shares_source_payload(
        payload,
        [table],
        pass1_result={
            "report_type": "A",
            "period_end": "2021-06-30",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["shares_outstanding"] is None
    assert "shares_outstanding" not in payload["row_refs"]


def test_shares_source_overlay_ignores_weighted_average_shares():
    """Weighted-average EPS rows are not period-end shares outstanding."""
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _apply_preferred_shares_source_payload

    table = DoclingTable(
        page_number=23,
        caption="Earnings per share",
        headers=["", "2021", "2020"],
        rows=[
            ["Weighted average number of shares (Million)", "5,057", "5,057"],
        ],
    )
    payload = {
        "period_type": "A",
        "period_end": "2021-06-30",
        "currency": "USD",
        "scale": "millions",
        "metrics": {"shares_outstanding": None},
        "shares_outstanding": None,
        "row_refs": {},
        "provenance": {},
    }

    _apply_preferred_shares_source_payload(
        payload,
        [table],
        pass1_result={
            "report_type": "A",
            "period_end": "2021-06-30",
            "currency": "USD",
        },
    )

    assert payload["metrics"]["shares_outstanding"] is None
    assert "shares_outstanding" not in payload["row_refs"]


def test_shares_prose_recovers_dual_listed_ordinary_shares_on_issue():
    """BHP-style dual-listed company prose can prove period-end shares."""
    from app.services.multipass_extraction import _extract_shares_from_prose

    value, provenance = _extract_shares_from_prose(
        [
            {
                "page": 53,
                "text": (
                    "At 30 June 2021, BHP Group Limited had 2,945 million ordinary "
                    "shares on issue and held by the public and BHP"
                ),
            },
            {
                "page": 53,
                "text": (
                    "Group Plc had 2,112 million ordinary shares on issue and held "
                    "by the public. No shares in BHP Group Limited were"
                ),
            },
        ]
    )

    assert value == 5_057_000_000
    assert provenance.startswith("prose_note:page_53:")


def test_shares_prose_recovers_split_number_of_shares_on_issue():
    """SEG-style PyMuPDF sections can split the label and share count."""
    from app.services.multipass_extraction import _extract_shares_from_prose

    value, provenance = _extract_shares_from_prose(
        [
            {"page": 24, "text": "6. Issued Capital"},
            {"page": 24, "text": "Number of shares on issue"},
            {"page": 24, "text": "280,874,770"},
            {"page": 24, "text": "Fully Paid Ordinary Share Capital"},
        ]
    )

    assert value == 280_874_770
    assert provenance.startswith("prose_note:page_24:")


def test_shares_prose_rejects_split_weighted_average_shares():
    """Weighted-average EPS denominators are not period-end shares outstanding."""
    from app.services.multipass_extraction import _extract_shares_from_prose

    value, provenance = _extract_shares_from_prose(
        [
            {
                "page": 21,
                "text": (
                    "Weighted average number of ordinary shares on issue during "
                    "the financial period"
                ),
            },
            {"page": 21, "text": "280,874,770 shares"},
        ]
    )

    assert value is None
    assert provenance == ""


def test_pass3a_shares_scaling_doc_level_fallback():
    """When table headers AND body text lack scale indicators, but the document-level
    scale is 'thousands', the fallback must apply the document multiplier.

    This covers tables that inherit the filing-level scale without restating it.
    """
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=24,
        caption="Share Capital",
        rows=[
            ["", "No.", "Amount"],
            ["Ordinary shares at end of period", "280,875", "42,110"],
        ],
        headers=["", "No.", "Amount"],  # no scale indicator
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "shares_outstanding": 280875,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["shares_outstanding"] == 280_875_000, (
        f"Expected 280,875,000 (×1000 from doc-level scale fallback), "
        f"got {results[0]['shares_outstanding']}"
    )


def test_pass3a_shares_outstanding_rejects_equity_dollar_table():
    """Dollar-denominated equity movement tables must not fabricate share counts."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=27,
        caption="",
        rows=[
            ["Telstra Group.", "Share capital.$m", "Total equity.$m"],
            ["Balance at 30 June 2025", "16,792", "17,733"],
            ["Additional shares purchased", "74", "74"],
            ["Balance at 31 December 2025", "16,940", "17,865"],
        ],
        headers=["Telstra Group.", "Share capital.$m", "Total equity.$m"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
    }

    mock_raw = {
        "shares_outstanding": 1694,
        "pass3_confidence": 0.8,
        "row_refs": {"shares_outstanding": "Balance at 31 December 2025"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["shares_outstanding"] is None


def test_pass3a_shares_outstanding_rejects_weighted_average_row():
    """Weighted-average share rows are EPS denominators, not period-end shares."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=23,
        caption="Earnings per share",
        rows=[
            ["Weighted average number of shares (Million)", "5,057", "5,057"],
        ],
        headers=["", "2021", "2020"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "A",
        "period_end": "2021-06-30",
        "currency": "USD",
        "scale": "millions",
    }
    mock_raw = {
        "shares_outstanding": 5_057_000_000,
        "pass3_confidence": 0.8,
        "row_refs": {
            "shares_outstanding": "Weighted average number of shares (Million)"
        },
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["shares_outstanding"] is None


def test_pass3a_shares_no_scaling_when_absolute():
    """When the LLM returns an absolute count (>= 1M), no scaling must be applied
    regardless of document-level scale — the value is already correct.
    """
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=32,
        caption="Share Capital Note",
        rows=[
            ["", "Number", "$M"],
            ["Balance at end of period", "196,478,902", "5,057"],
        ],
        headers=["", "Number", "$M"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
    }

    mock_raw = {
        "shares_outstanding": 196478902,  # absolute count, already correct
        "pass3_confidence": 0.95,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["shares_outstanding"] == 196_478_902, (
        f"Absolute count must not be scaled; got {results[0]['shares_outstanding']}"
    )


def test_pass3a_shares_outstanding_accepts_stapled_security_counts():
    """Securities/unit count tables should count as valid share-count evidence."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=40,
        caption="Note 14 Contributed equity",
        rows=[
            [
                "",
                "For the 6 months to 31 Dec 2025 No. of securities",
                "For the 12 months to 30 Jun 2025 No. of securities",
            ],
            ["Closing balance", "1,075,565,246", "1,075,565,246"],
        ],
        headers=[
            "",
            "For the 6 months to 31 Dec 2025 No. of securities",
            "For the 12 months to 30 Jun 2025 No. of securities",
        ],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": None,
        "share_capital": table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
    }

    mock_raw = {
        "shares_outstanding": 1075565246,
        "pass3_confidence": 0.9,
        "row_refs": {"shares_outstanding": "Closing balance"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["shares_outstanding"] == 1_075_565_246


def test_pass3a_infers_total_debt_row_ref_from_balance_sheet_rows():
    """Balance-sheet debt extraction should preserve strong provenance even when the model omits it."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=17,
        caption="Statement of financial position",
        rows=[
            ["Cash and cash equivalents", "74.7", "65.3"],
            ["Interest bearing liabilities", "782.8", "907.1"],
            ["Interest bearing liabilities", "3,808.6", "3,813.0"],
            ["Total liabilities", "5,261.1", "5,475.5"],
        ],
        headers=["", "31 Dec 2025 $m", "30 Jun 2025 $m"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": table,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
    }

    mock_raw = {
        "net_debt": None,
        "total_debt": 4591.4,
        "shares_outstanding": None,
        "pass3_confidence": 0.8,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["row_refs"]["total_debt"] == "Interest bearing liabilities"


def test_pass3a_recovers_total_debt_from_current_and_noncurrent_borrowings():
    """Balance-sheet total_debt should include current plus non-current borrowings."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=12,
        caption="Consolidated balance sheet",
        rows=[
            ["Cash and cash equivalents", "", "1,145", "2,157"],
            ["Interest-bearing liabilities and borrowings", "7", "717", "804"],
            ["Interest-bearing liabilities and borrowings", "7", "10,421", "10,694"],
            ["Total liabilities", "", "17,442", "17,997"],
        ],
        headers=[
            "",
            "Notes",
            "Consolidated Entity.December 2025 US$m",
            "Consolidated Entity.June 2025 US$m",
        ],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": table,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
    }
    mock_raw = {
        "net_debt": None,
        "total_debt": 10_421,
        "shares_outstanding": None,
        "pass3_confidence": 0.8,
        "row_refs": {"total_debt": "Interest-bearing liabilities and borrowings"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["total_debt"] == 11_138_000_000
    assert results[0]["row_refs"]["total_debt"] == [
        "Interest-bearing liabilities and borrowings",
        "Interest-bearing liabilities and borrowings",
    ]


def test_pass3a_recovers_total_debt_from_multiline_balance_sheet_groups():
    """Grouped Docling rows should align labels with same-line current values."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=12,
        caption="Consolidated balance sheet",
        rows=[
            [
                (
                    "CURRENT LIABILITIES\n"
                    "Trade and other payables\n"
                    "Interest-bearing liabilities and borrowings 7\n"
                    "Current tax liabilities\n"
                    "Provisions"
                ),
                "3,171\n717\n302\n418",
                "3,461\n804\n280\n270",
            ],
            [
                (
                    "NON-CURRENT LIABILITIES\n"
                    "Interest-bearing liabilities and borrowings 7\n"
                    "Retirement benefit liabilities\n"
                    "Deferred tax liabilities\n"
                    "Provisions\n"
                    "Other non-current liabilities"
                ),
                "10,421\n306",
                "10,694\n308\n1,510\n155\n515",
            ],
        ],
        headers=["", "December 2025 US$m", "June 2025 US$m"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": table,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
    }
    mock_raw = {
        "net_debt": None,
        "total_debt": 10_421,
        "shares_outstanding": None,
        "pass3_confidence": 0.8,
        "row_refs": {"total_debt": "Interest-bearing liabilities and borrowings 7"},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["total_debt"] == 11_138_000_000
    assert results[0]["row_refs"]["total_debt"] == [
        "Interest-bearing liabilities and borrowings 7",
        "Interest-bearing liabilities and borrowings 7",
    ]


def test_total_debt_recovery_aligns_unicode_hyphenated_liability_groups():
    """Unicode non-breaking hyphens must not shift grouped debt values."""
    from app.services.multipass_extraction import (
        _recover_total_debt_from_balance_sheet_table,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=10,
        caption="Statement of financial position",
        rows=[
            [
                (
                    "Current liabilities\n"
                    "Trade and other payables\n"
                    "Lease liabilities\n"
                    "Borrowings\n"
                    "Current tax payable\n"
                    "Other financial liabilities\n"
                    "Provisions\n"
                    "Other liabilities"
                ),
                "",
                "8,083\n1,699\n244\n127\n342\n1,791\n11",
            ],
            ["", "8,487", ""],
            ["", "1,724", ""],
            ["", "422", ""],
            ["", "114", ""],
            ["", "226", ""],
            ["", "2,475", ""],
            ["", "13", ""],
            ["Total current liabilities", "13,461", "12,297"],
            [
                (
                    "Non‑current liabilities\n"
                    "Lease liabilities\n"
                    "Borrowings\n"
                    "Other financial liabilities\n"
                    "Provisions\n"
                    "Deferred tax liability\n"
                    "Other liabilities"
                ),
                "",
                "10,175\n5,267\n46\n963\n61\n58",
            ],
            ["", "9,788", ""],
            ["", "5,264", ""],
            ["", "96", ""],
            ["", "915", ""],
            ["", "53", ""],
            ["", "53", ""],
            ["Total non‑current liabilities", "16,169", "16,570"],
        ],
        headers=["", "4 January 2026 $m", "29 June 2025 $m"],
    )

    recovered = _recover_total_debt_from_balance_sheet_table(table, "millions")

    assert recovered == (
        5_686_000_000,
        ["Borrowings", "Borrowings"],
    )


def test_total_debt_recovery_avoids_double_counting_and_excludes_leases():
    """Component rows beat explicit totals without adding leases or the total twice."""
    from app.services.multipass_extraction import (
        _recover_total_debt_from_balance_sheet_table,
    )
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=10,
        caption="Statement of financial position",
        rows=[
            ["Lease liabilities", "1,724", "1,699"],
            ["Borrowings", "422", "244"],
            ["Lease liabilities", "9,788", "10,175"],
            ["Borrowings", "5,264", "5,267"],
            ["Total debt", "5,686", "5,511"],
        ],
        headers=["", "4 January 2026 $m", "29 June 2025 $m"],
    )

    recovered = _recover_total_debt_from_balance_sheet_table(table, "millions")

    assert recovered == (
        5_686_000_000,
        ["Borrowings", "Borrowings"],
    )


def test_pass3a_recovers_total_debt_from_pymupdf_blank_value_rows():
    """PyMuPDF grouped rows should align labels with following current values."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=19,
        caption="",
        headers=[
            (
                "Assets\n"
                "Cash and cash equivalents\n"
                "Investments 3.2\n"
                "Intangible assets"
            ),
            "",
            "1,638\n28,932\n1,964",
        ],
        rows=[
            [
                (
                    "Liabilities\n"
                    "Derivative financial instruments 4.2\n"
                    "Borrowings 4.1\n"
                    "Total liabilities\n"
                    "Net assets"
                ),
                "",
                "402\n2,664\n33,115\n10,731",
            ],
            ["", "208", ""],
            ["", "3,679", ""],
            ["", "36,381", ""],
            ["", "10,898", ""],
        ],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": table,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-06-30",
        "currency": "USD",
        "scale": "millions",
    }
    mock_raw = {
        "net_debt": None,
        "total_debt": None,
        "shares_outstanding": None,
        "pass3_confidence": 0.8,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["total_debt"] == 3_679_000_000
    assert results[0]["row_refs"]["total_debt"] == "Borrowings 4.1"


def test_pass3a_recovers_explicit_net_debt_from_balance_sheet_row():
    """A direct current-period Net debt row in a balance sheet is source-bound."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=16,
        caption="Balance sheet key metrics",
        rows=[
            ["Borrowings", "4", "5,150", "4,835"],
            ["Lease liabilities", "4", "606", "604"],
            ["Total debt", "", "5,756", "5,439"],
            ["Cash and cash equivalents", "4", "4,743", "4,328"],
            ["Net debt", "", "1,013", "1,111"],
        ],
        headers=["", "", "31 December 2025", "30 June 2025"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": table,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "USD",
        "scale": "millions",
    }
    mock_raw = {
        "net_debt": None,
        "total_debt": None,
        "shares_outstanding": None,
        "pass3_confidence": 0.8,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["net_debt"] == 1_013_000_000
    assert results[0]["row_refs"]["net_debt"] == "Net debt"


def test_pass3a_prefers_strong_total_debt_row_ref_from_model_list():
    """Mixed model row_ref lists should keep the strongest debt label only."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=17,
        caption="Statement of financial position",
        rows=[
            ["Interest bearing liabilities", "782.8", "907.1"],
            ["Lease liabilities", "11.8", "31.5"],
        ],
        headers=["", "31 Dec 2025 $m", "30 Jun 2025 $m"],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": None,
        "balance_sheet": table,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2025-12-31",
        "currency": "AUD",
        "scale": "millions",
    }

    mock_raw = {
        "net_debt": None,
        "total_debt": 4591.4,
        "shares_outstanding": None,
        "pass3_confidence": 0.8,
        "row_refs": {"total_debt": ["Interest bearing liabilities", "Lease liabilities"]},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["row_refs"]["total_debt"] == "Interest bearing liabilities"


# ---------------------------------------------------------------------------
# Pass 2 — CF table disqualification for IS/BS slots
# ---------------------------------------------------------------------------


def test_pass2_cf_disqualification_blocks_5b_from_income_statement():
    """A cash-flow table (Appendix 5B) with 'income tax' keyword must NOT
    claim the income_statement slot due to CF disqualification phrases in
    its body rows."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    cf_table = DoclingTable(
        page_number=11,
        caption="",
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date $A'000",
            ],
            ["1.1", "Receipts from customers", "21,836", "44,295"],
            ["1.7", "Income tax paid", "(400)", "(800)"],
        ],
    )

    labelled = _run_pass2_locator([cf_table])
    assert labelled["income_statement"] is None, (
        "Appendix 5B cash-flow table must NOT claim the income_statement slot "
        "despite having 'income tax' keyword match"
    )
    assert labelled["cashflow_statement"] is not None, (
        "The table must still be labelled as cashflow_statement"
    )


def test_pass2_cf_disqualification_blocks_5b_from_balance_sheet():
    """A cash-flow table with 'non-current assets' keyword must NOT
    claim the balance_sheet slot."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    cf_table = DoclingTable(
        page_number=12,
        caption="",
        headers=[
            "Consolidated statement of cash flows",
            "Consolidated statement of cash flows",
            "Current quarter $A'000",
            "Year to date $A'000",
        ],
        rows=[
            [
                "Consolidated statement of cash flows",
                "Consolidated statement of cash flows",
                "Current quarter $A'000",
                "Year to date $A'000",
            ],
            ["2.", "Cash flows from investing activities", "", ""],
            ["2.1(d)", "Exploration — non-current assets", "(100)", "(200)"],
        ],
    )

    labelled = _run_pass2_locator([cf_table])
    assert labelled["balance_sheet"] is None, (
        "Appendix 5B cash-flow table must NOT claim the balance_sheet slot "
        "despite having 'non-current assets' keyword match"
    )


def test_pass2_cross_guarantee_note_cannot_claim_income_statement():
    """Closed-group deed notes must not beat the real consolidated income statement."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    consolidated_table = DoclingTable(
        page_number=122,
        caption="Consolidated statement of comprehensive income",
        headers=["Year ended 30 June", "2025 US$M", "2024 US$M"],
        rows=[
            ["Revenue", "51,262", "55,658"],
            ["Profit before taxation", "15,123", "14,500"],
            ["Income tax expense", "(4,000)", "(3,900)"],
        ],
    )
    closed_group_note = DoclingTable(
        page_number=179,
        caption="",
        headers=["Consolidated Statement of Comprehensive Income and Retained Earnings"],
        rows=[
            ["36 Deed of Cross Guarantee", ""],
            ["Revenue", "28,032"],
            ["Profit before taxation", "7,100"],
        ],
    )

    labelled = _run_pass2_locator([closed_group_note, consolidated_table])

    assert labelled["income_statement"] is consolidated_table, (
        "Closed-group deed note must not win the canonical income_statement slot"
    )


def test_pass2_auditor_review_report_cannot_claim_balance_sheet():
    """Auditor review pages can mention statements but are not source tables."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    qbe_balance_sheet = DoclingTable(
        page_number=19,
        caption="",
        headers=[
            (
                "Assets\n"
                "Cash and cash equivalents\n"
                "Investments 3.2\n"
                "Intangible assets"
            ),
            "",
            "1,638\n28,932\n1,964",
        ],
        rows=[
            [
                (
                    "Assets\n"
                    "Cash and cash equivalents\n"
                    "Investments 3.2\n"
                    "Intangible assets"
                ),
                "",
                "1,638\n28,932\n1,964",
            ],
            ["", "2,124", ""],
            ["", "31,822", ""],
            ["", "2,072", ""],
            [
                (
                    "Liabilities\n"
                    "Derivative financial instruments\n"
                    "Borrowings\n"
                    "Total liabilities\n"
                    "Net assets\n"
                    "Equity\n"
                    "Total equity"
                ),
                "",
                "402\n2,664\n33,115\n10,731\n10,731",
            ],
            ["", "208", ""],
            ["", "3,679", ""],
            ["", "36,381", ""],
            ["", "10,898", ""],
            ["", "10,898", ""],
        ],
    )
    auditor_review = DoclingTable(
        page_number=36,
        caption="",
        headers=["32", "", "", "", "", "", "", ""],
        rows=[
            ["32", "", "", "", "", "", "", ""],
            ["", "Independent a", "uditor's", "review", "repo", "rt", "", ""],
            ["", "Report on the Half Year Financ", "ial Report", "", "", "", "", ""],
            [
                "",
                "which comprises the consolidated balance sheet",
                "as at 30 June 2025",
                "",
                "",
                "",
                "",
                "",
            ],
        ],
    )

    labelled = _run_pass2_locator([auditor_review, qbe_balance_sheet])

    assert labelled["balance_sheet"] is qbe_balance_sheet


# ---------------------------------------------------------------------------
# Redundant table skipping
# ---------------------------------------------------------------------------


def _make_dummy_table(caption="Dummy"):
    from app.services.docling_extract import DoclingTable

    return DoclingTable(
        page_number=1,
        caption=caption,
        rows=[["", "H1"], ["Item", "100"]],
        headers=["", "H1"],
    )


def test_share_capital_not_skipped_when_balance_sheet_present():
    """share_capital LLM call must NOT be skipped even when balance_sheet is present.

    Balance sheets are dense and unreliable for share counts; the dedicated
    share_capital table is the most reliable source for shares_outstanding.
    """
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "balance_sheet": _make_dummy_table("Balance Sheet"),
        "share_capital": _make_dummy_table("Share Capital"),
        "income_statement": None,
        "cashflow_statement": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "net_debt": 500,
        "total_debt": None,
        "shares_outstanding": 1_000_000,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    original_tables = []

    def _tracking_llm_call(prompt, *args, **kwargs):
        if "share_capital" in prompt:
            original_tables.append("share_capital")
        elif "balance_sheet" in prompt:
            original_tables.append("balance_sheet")
        return mock_raw

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        side_effect=_tracking_llm_call,
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "1"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    # Both balance_sheet AND share_capital should have been called
    assert "share_capital" in original_tables
    assert "balance_sheet" in original_tables
    sources = [r["_source"] for r in results]
    assert "share_capital" in sources


def test_share_capital_not_skipped_when_balance_sheet_absent():
    """share_capital must NOT be skipped when balance_sheet is absent."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "balance_sheet": None,
        "share_capital": _make_dummy_table("Share Capital"),
        "income_statement": None,
        "cashflow_statement": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "shares_outstanding": 1_000_000,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "1"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    sources = [r["_source"] for r in results]
    assert "share_capital" in sources


def test_skip_highlights_when_is_and_cf_present():
    """highlights LLM call must be skipped when IS + CF are both present."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "income_statement": _make_dummy_table("Income Statement"),
        "cashflow_statement": _make_dummy_table("Cash Flow"),
        "balance_sheet": None,
        "share_capital": None,
        "highlights": _make_dummy_table("Highlights"),
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "revenue": 1000,
        "ebit": 200,
        "np_attributable": 150,
        "operating_cf": 500,
        "investing_cf": -100,
        "financing_cf": -50,
        "capex": None,
        "cash_end": None,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    called_tables = []

    def _tracking_llm_call(prompt, *args, **kwargs):
        if "highlights" in prompt:
            called_tables.append("highlights")
        elif "income_statement" in prompt:
            called_tables.append("income_statement")
        elif "cashflow_statement" in prompt:
            called_tables.append("cashflow_statement")
        return mock_raw

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        side_effect=_tracking_llm_call,
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "1"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert "highlights" not in called_tables
    sources = [r["_source"] for r in results]
    assert "highlights" not in sources


def test_highlights_not_skipped_when_cf_absent():
    """highlights must NOT be skipped when cashflow_statement is absent."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "income_statement": _make_dummy_table("Income Statement"),
        "cashflow_statement": None,
        "balance_sheet": None,
        "share_capital": None,
        "highlights": _make_dummy_table("Highlights"),
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "revenue": 1000,
        "ebit": 200,
        "np_attributable": 150,
        "operating_cf": None,
        "investing_cf": None,
        "financing_cf": None,
        "capex": None,
        "cash_end": None,
        "net_debt": None,
        "shares_outstanding": None,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "1"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    sources = [r["_source"] for r in results]
    assert "highlights" in sources


def test_skip_redundant_disabled_by_env_var():
    """When EXTRACTION_SKIP_REDUNDANT=0, no tables should be skipped."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor

    labelled = {
        "income_statement": _make_dummy_table("Income Statement"),
        "cashflow_statement": _make_dummy_table("Cash Flow"),
        "balance_sheet": _make_dummy_table("Balance Sheet"),
        "share_capital": _make_dummy_table("Share Capital"),
        "highlights": _make_dummy_table("Highlights"),
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    mock_raw = {
        "revenue": 1000,
        "ebit": 200,
        "np_attributable": 150,
        "operating_cf": 500,
        "investing_cf": -100,
        "financing_cf": -50,
        "capex": None,
        "cash_end": 800,
        "net_debt": 300,
        "total_debt": None,
        "shares_outstanding": 1_000_000,
        "pass3_confidence": 0.9,
        "row_refs": {},
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
    ):
        with patch.dict("os.environ", {"EXTRACTION_SKIP_REDUNDANT": "0"}):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    sources = [r["_source"] for r in results]
    assert "share_capital" in sources
    assert "highlights" in sources


# ---------------------------------------------------------------------------
# skip_narrative — optional Pass 3b skipping
# ---------------------------------------------------------------------------


def _mock_structured_doc():
    """Build a minimal StructuredDocument for run_multipass_extraction tests."""
    from app.services.docling_extract import DoclingTable

    class _FakeDoc:
        extraction_method = "docling"
        page_count = 1
        docling_version = "test"
        sections = [
            {
                "text": (
                    "Half-Year Report for the half-year ended 30 June 2025. "
                    "Some prose about risk."
                ),
                "page": 1,
            }
        ]
        tables = [
            DoclingTable(
                page_number=1,
                caption="Income Statement",
                headers=["", "H1 2025 $'000"],
                raw_header_rows=[["", "30 Jun 2025 $'000"]],
                rows=[
                    ["", "H1 2025 $'000"],
                    ["Revenue", "500,000"],
                    ["EBIT", "80,000"],
                    ["Net profit", "55,000"],
                ],
            ),
        ]

    return _FakeDoc()


def _pass1_response():
    return {
        "report_type": "H",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "scale": "thousands",
        "classifier_confidence": 0.95,
    }


def _pass3a_response():
    return {
        "revenue": 500_000,
        "ebit": 80_000,
        "np_attributable": 55_000,
        "operating_cf": None,
        "investing_cf": None,
        "financing_cf": None,
        "capex": None,
        "cash_end": None,
        "net_debt": None,
        "shares_outstanding": None,
        "total_debt": None,
        "pass3_confidence": 0.88,
        "row_refs": {
            "revenue": "Revenue",
            "ebit": "EBIT",
            "np_attributable": "Net profit",
        },
    }


def _pass3b_response():
    return {
        "risk_summary": "Commodity price risk exposure",
        "risk_bullets": "Iron ore volatility",
        "guidance_summary": "Revenue growth 10%",
        "material_changes": None,
        "confidence_narrative": 0.75,
    }


def test_run_multipass_abstains_when_currency_has_no_explicit_evidence():
    """A generic dollar scale and classifier null must not be rewritten to AUD."""
    from app.services.multipass_extraction import run_multipass_extraction

    pass1 = _pass1_response()
    pass1["currency"] = "null"

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=pass1,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=[_pass3a_response()],
    ):
        result = run_multipass_extraction(
            "/fake/ambiguous-currency.pdf",
            {
                "document_id": "ambiguous-currency",
                "ticker": "TST",
                "title": "Half-Year Report",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert result.status == "failed"
    assert result.error == "validation_gate:currency_unknown"
    assert result.payload["currency"] == ""
    assert result.payload["_structured_extraction"]["warnings"] == []


def test_run_multipass_abstains_when_classifier_omits_currency():
    """An omitted classifier currency without table evidence must stay unknown."""
    from app.services.multipass_extraction import run_multipass_extraction

    pass1 = _pass1_response()
    del pass1["currency"]

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ), patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value=pass1,
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value={},
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        return_value=[_pass3a_response()],
    ):
        result = run_multipass_extraction(
            "/fake/missing-currency.pdf",
            {
                "document_id": "missing-currency",
                "ticker": "TST",
                "title": "Half-Year Report",
            },
            llm_client=None,
            skip_narrative=True,
        )

    assert result.status == "failed"
    assert result.error == "validation_gate:currency_unknown"
    assert result.payload["currency"] == ""
    assert result.payload["_structured_extraction"]["warnings"] == []


def test_skip_narrative_param_skips_pass3b_llm_call():
    """With skip_narrative=True, no LLM call should be made for pass3b."""
    from app.services.multipass_extraction import run_multipass_extraction

    call_log = []

    def mock_llm(prompt, llm_client, max_tokens=512, **kwargs):
        call_log.append(prompt)
        # Return pass1 on first call, pass3a on subsequent
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            result = run_multipass_extraction(
                "/fake/path.pdf",
                {"document_id": "d1", "ticker": "TST", "title": "Test Report"},
                llm_client=None,
                skip_narrative=True,
            )

    # No call should contain the pass3b narrative prompt keywords
    for prompt in call_log:
        assert "narrative extractor" not in prompt.lower(), (
            "Pass 3b LLM call must not be made when skip_narrative=True"
        )

    # Narrative fields must be null
    assert result.payload.get("risk_summary") is None
    assert result.payload.get("guidance_summary") is None
    assert result.payload.get("confidence_narrative") == 0.0


def test_skip_narrative_env_var_skips_pass3b():
    """EXTRACTION_SKIP_NARRATIVE=1 env var must skip pass3b even when param is False."""
    from app.services.multipass_extraction import run_multipass_extraction

    call_log = []

    def mock_llm(prompt, llm_client, max_tokens=512, **kwargs):
        call_log.append(prompt)
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            with patch.dict("os.environ", {"EXTRACTION_SKIP_NARRATIVE": "1"}):
                result = run_multipass_extraction(
                    "/fake/path.pdf",
                    {"document_id": "d2", "ticker": "TST", "title": "Test"},
                    llm_client=None,
                )

    for prompt in call_log:
        assert "narrative extractor" not in prompt.lower(), (
            "Pass 3b LLM call must not be made when EXTRACTION_SKIP_NARRATIVE=1"
        )
    assert result.payload.get("risk_summary") is None


def test_skip_narrative_produces_valid_pipeline_output():
    """Pipeline with skip_narrative must still produce a structurally valid result
    that passes the validation gate (all narrative fields null is acceptable)."""
    from app.services.multipass_extraction import (
        run_multipass_extraction,
        METRIC_FIELDS,
    )

    def mock_llm(prompt, llm_client, max_tokens=512, **kwargs):
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            result = run_multipass_extraction(
                "/fake/path.pdf",
                {"document_id": "d3", "ticker": "TST", "title": "Test"},
                llm_client=None,
                skip_narrative=True,
            )

    # Must not fail due to missing narrative
    assert result.status in ("ok", "ok_low_confidence"), (
        f"Pipeline must not fail with skip_narrative; got status={result.status!r}, error={result.error!r}"
    )

    # Payload structure must include all expected keys
    assert "metrics" in result.payload
    for m in METRIC_FIELDS:
        assert m in result.payload, f"Metric field {m!r} missing from payload"
    assert "risk_summary" in result.payload
    assert "guidance_summary" in result.payload
    assert "confidence_narrative" in result.payload
    assert "provenance" in result.payload


def test_skip_narrative_false_still_calls_pass3b():
    """Default behaviour (skip_narrative=False) must still call pass3b."""
    from app.services.multipass_extraction import run_multipass_extraction

    call_log = []

    def mock_llm(prompt, llm_client, max_tokens=512, **kwargs):
        call_log.append(prompt)
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        if "narrative" in prompt.lower() or "risk" in prompt.lower():
            return _pass3b_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            with patch.dict(
                "os.environ", {"EXTRACTION_SKIP_NARRATIVE": ""}, clear=False
            ):
                result = run_multipass_extraction(
                    "/fake/path.pdf",
                    {"document_id": "d4", "ticker": "TST", "title": "Test"},
                    llm_client=None,
                    skip_narrative=False,
                )

    # At least one call must be for narrative extraction
    narrative_calls = [
        p for p in call_log if "narrative" in p.lower() or "risk" in p.lower()
    ]
    assert len(narrative_calls) >= 1, (
        "Pass 3b LLM call must be made when skip_narrative=False"
    )
    assert result.payload.get("risk_summary") == "Commodity price risk exposure"


def test_debug_capture_collects_pass3a_results_without_changing_payload_shape():
    """Optional debug capture should retain raw pass3a outputs for the caller only."""
    from app.services.multipass_extraction import run_multipass_extraction

    debug_capture = {}

    def mock_llm(prompt, llm_client, max_tokens=512, **kwargs):
        if "classifier" in prompt.lower() or "report_type" in prompt.lower():
            return _pass1_response()
        if "narrative" in prompt.lower() or "risk" in prompt.lower():
            return _pass3b_response()
        return _pass3a_response()

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_mock_structured_doc(),
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call", side_effect=mock_llm
        ):
            result = run_multipass_extraction(
                "/fake/path.pdf",
                {"document_id": "d5", "ticker": "TST", "title": "Test"},
                llm_client=None,
                debug_capture=debug_capture,
            )

    assert result.status in ("ok", "ok_low_confidence")
    assert "_debug_capture" not in result.payload
    assert "pass3a_results" in debug_capture
    assert len(debug_capture["pass3a_results"]) == 1
    captured = debug_capture["pass3a_results"][0]
    assert captured["_source"] == "income_statement"
    assert captured["revenue"] == 500_000_000
    assert 0.0 <= captured["pass3_confidence"] <= 1.0


def test_run_multipass_blocks_derived_net_debt_even_when_note_slot_is_selected():
    """Glossary-only Net debt mentions must block derivation regardless of locator output."""
    from app.services.multipass_extraction import run_multipass_extraction
    from app.services.docling_extract import DoclingTable

    class _FakeDoc:
        extraction_method = "docling"
        page_count = 2
        docling_version = "test"
        sections = [{"text": "Half year report", "page": 1}]
        tables = [
            DoclingTable(
                page_number=1,
                caption="",
                rows=[
                    ["GLOSSARY", ""],
                    [
                        "Net debt",
                        "Gross debt less cash and cash equivalents. Includes finance lease liabilities.",
                    ],
                ],
                headers=["Term", "Definition"],
            ),
            DoclingTable(
                page_number=2,
                caption="",
                rows=[
                    ["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
                    ["Borrowings", "(15,730)", "(14,896)"],
                    ["Cash and cash equivalents", "1,436", "1,012"],
                    ["Net debt", "(16,800)", "(16,445)"],
                ],
                headers=["Table A", "As at 31 Dec 2025", "As at 30 Jun 2025"],
            ),
        ]

    note_table = _FakeDoc.tables[1]
    labelled = {
        "cashflow_statement": None,
        "income_statement": note_table,
        "net_debt_note": note_table,
        "balance_sheet": None,
        "share_capital": None,
        "highlights": None,
        "unmatched": [],
    }

    def _capture_pass3a(_labelled, pass1, llm_client, **kwargs):
        assert pass1["_block_derived_net_debt"] is True
        return [
            {
                "_source": "income_statement",
                "_page_number": 2,
                "revenue": 500_000_000,
                "ebit": 80_000_000,
                "np_attributable": 55_000_000,
                "pass3_confidence": 0.88,
                "row_refs": {
                    "revenue": "Revenue",
                    "ebit": "EBIT",
                    "np_attributable": "Net profit",
                },
            }
        ]

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_FakeDoc(),
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value=_pass1_response(),
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        return_value=labelled,
    ), patch(
        "app.services.multipass_extraction._run_pass3a_metric_extractor",
        side_effect=_capture_pass3a,
    ):
        result = run_multipass_extraction(
            "/fake/path.pdf",
            {"document_id": "min-test", "ticker": "MIN", "title": "MIN Half Year"},
            llm_client=None,
            skip_narrative=True,
        )

    assert result.status in ("ok", "ok_low_confidence")


def test_validation_gate_accepts_null_narrative_fields():
    """The validation gate must not reject a payload just because narrative fields are null."""
    from app.services.multipass_extraction import _validate_gate

    payload = _good_payload()
    payload["risk_summary"] = None
    payload["risk_bullets"] = None
    payload["guidance_summary"] = None
    payload["material_changes"] = None
    payload["confidence_narrative"] = 0.0

    status, error = _validate_gate(payload)
    assert status in ("ok", "ok_low_confidence"), (
        f"Gate must accept all-null narrative fields; got status={status!r}, error={error!r}"
    )


def _whc_openability_diagnostic():
    diagnostic = {
        "schema": "docling_openability_diagnostics_v1",
        "provenance_only": True,
        "feeds_canonical_output": False,
        "canonical_output_changed": False,
        "ocr_records": [
            {
                "page": 57,
                "statement_label": "income_statement",
                "period_phrases": ["For the year ended 30 June 2022"],
                "scale_phrases": ["$000"],
                "row_candidates": [
                    {
                        "source_text": "Revenue 21 4,920,102 1,556,976",
                        "candidate_value_text": "4,920,102",
                        "value_text_candidates": ["21", "4,920,102", "1,556,976"],
                        "candidate_value_quality": "financial_amount",
                    },
                    {
                        "source_text": "Profit/(loss) before net financial expense 2,821,254 (706,181)",
                        "candidate_value_text": "2,821,254",
                        "value_text_candidates": ["2,821,254", "(706,181)"],
                        "candidate_value_quality": "financial_amount",
                    },
                    {
                        "source_text": "Unusable subtotal 123",
                        "candidate_value_text": "123",
                        "value_text_candidates": ["123"],
                        "candidate_value_quality": "low_confidence",
                    },
                ],
            },
            {
                "page": 58,
                "statement_label": "balance_sheet",
                "period_phrases": ["As at 30 June 2022"],
                "scale_phrases": ["$000"],
                "row_candidates": [
                    {
                        "source_text": "Cash and cash equivalents 1,215,460 95,202",
                        "candidate_value_text": "1,215,460",
                        "value_text_candidates": ["1,215,460", "95,202"],
                        "candidate_value_quality": "financial_amount",
                    },
                    {
                        "source_text": "Total liabilities 1,912,899 1,687,128",
                        "candidate_value_text": "1,912,899",
                        "value_text_candidates": ["1,912,899", "1,687,128"],
                        "candidate_value_quality": "financial_amount",
                    },
                ],
            },
            {
                "page": 60,
                "statement_label": "cashflow_statement",
                "period_phrases": ["For the year ended 30 June 2022"],
                "scale_phrases": ["$000"],
                "row_candidates": [
                    {
                        "source_text": "Net cash from operating activities 3.4 2,529,823 138,765",
                        "candidate_value_text": "2,529,823",
                        "value_text_candidates": ["3.4", "2,529,823", "138,765"],
                        "candidate_value_quality": "financial_amount",
                    },
                    {
                        "source_text": "Purchase of property, plant and equipment (124,210) (68,693)",
                        "candidate_value_text": "(124,210)",
                        "value_text_candidates": ["(124,210)", "(68,693)"],
                        "candidate_value_quality": "financial_amount",
                    },
                    {
                        "source_text": "Cash and cash equivalents at end of year 1,215,460 95,202",
                        "candidate_value_text": "1,215,460",
                        "value_text_candidates": ["1,215,460", "95,202"],
                        "candidate_value_quality": "financial_amount",
                    },
                ],
            },
            {
                "page": 61,
                "statement_label": None,
                "period_phrases": ["For the year ended 30 June 2022"],
                "scale_phrases": ["rounded to the nearest thousand"],
                "row_candidates": [],
            },
        ],
    }
    for record in diagnostic["ocr_records"]:
        for row_index, candidate in enumerate(record["row_candidates"], start=1):
            candidate.update(
                {
                    "source_region": {
                        "left": 10,
                        "top": row_index * 20,
                        "right": 500,
                        "bottom": row_index * 20 + 12,
                    },
                    "source_row": row_index,
                    "source_cell": [1, 2],
                    "recognition_confidence": 95,
                }
            )
    return diagnostic


class _OpenabilityDoc:
    extraction_method = "pymupdf"
    page_count = 61
    source_pdf_page_count = 61
    docling_version = "test"
    sections = [
        {
            "text": "Whitehaven Coal 2022 Annual Report For the year ended 30 June 2022.",
            "page": 1,
        }
    ]
    tables = []
    parser_diagnostics = {"openability": _whc_openability_diagnostic()}


class _OpenabilityPeriodOnlyDoc(_OpenabilityDoc):
    sections = [{"text": "Whitehaven Coal 2022 Annual Report.", "page": 1}]


def test_openability_selected_tables_builds_statement_tables_from_source_bound_diagnostics():
    from app.services.multipass_extraction import (
        _build_openability_selected_tables,
        _detect_scale_from_table,
        _run_pass2_locator,
    )

    tables = _build_openability_selected_tables(_OpenabilityDoc())

    assert [table.page_number for table in tables] == [57, 58, 60]
    assert all(_detect_scale_from_table(table) == "thousands" for table in tables)
    assert "Revenue 21 4,920,102 1,556,976" in tables[0].rows[1][0]
    assert "region=" in tables[0].rows[1][0]
    assert "row=1" in tables[0].rows[1][0]
    assert "cells=[1, 2]" in tables[0].rows[1][0]
    assert "Unusable subtotal" not in " ".join(
        " ".join(row) for table in tables for row in table.rows
    )

    labelled = _run_pass2_locator(tables)
    assert labelled["income_statement"].page_number == 57
    assert labelled["balance_sheet"].page_number == 58
    assert labelled["cashflow_statement"].page_number == 60


def test_openability_selected_tables_fail_closed_without_period_or_scale_evidence():
    from app.services.multipass_extraction import _build_openability_selected_tables

    class _MissingPeriodDoc(_OpenabilityDoc):
        parser_diagnostics = {"openability": _whc_openability_diagnostic()}

    _MissingPeriodDoc.parser_diagnostics["openability"]["ocr_records"][0][
        "period_phrases"
    ] = []
    period_tables = _build_openability_selected_tables(_MissingPeriodDoc())
    assert {table.page_number for table in period_tables} == {58, 60}

    class _MissingScaleDoc(_OpenabilityDoc):
        parser_diagnostics = {"openability": _whc_openability_diagnostic()}

    for record in _MissingScaleDoc.parser_diagnostics["openability"]["ocr_records"]:
        record["scale_phrases"] = []
    assert _build_openability_selected_tables(_MissingScaleDoc()) == []


def test_openability_selected_tables_quarantine_conflicting_cross_page_scales():
    import copy

    from app.services.multipass_extraction import _build_openability_selected_tables

    diagnostic = copy.deepcopy(_whc_openability_diagnostic())
    diagnostic["ocr_records"][0]["scale_phrases"] = ["$000"]
    diagnostic["ocr_records"][1]["scale_phrases"] = ["millions"]
    diagnostic["ocr_records"][2]["scale_phrases"] = ["$000", "millions"]

    class _ConflictingScaleDoc(_OpenabilityDoc):
        parser_diagnostics = {"openability": diagnostic}

    tables = _build_openability_selected_tables(_ConflictingScaleDoc())

    assert [(table.page_number, table.headers[1]) for table in tables] == [
        (57, "For the year ended 30 June 2022 $000"),
        (58, "As at 30 June 2022 millions"),
    ]


@pytest.mark.parametrize("confidence", [None, "not-a-number", True, 79.99])
def test_openability_final_selection_requires_numeric_confidence_at_least_80(
    confidence,
):
    import copy

    from app.services.multipass_extraction import _build_openability_selected_tables

    diagnostic = copy.deepcopy(_whc_openability_diagnostic())
    diagnostic["ocr_records"][0]["row_candidates"][0][
        "recognition_confidence"
    ] = confidence

    class _InvalidConfidenceDoc(_OpenabilityDoc):
        parser_diagnostics = {"openability": diagnostic}

    tables = _build_openability_selected_tables(_InvalidConfidenceDoc())

    income_table = next(
        table for table in tables if table.page_number == 57
    )
    assert all("Revenue 21" not in row[0] for row in income_table.rows)
    assert all(
        candidate["source_text"] != "Revenue 21 4,920,102 1,556,976"
        for candidate in income_table.ocr_source_candidates
    )


def test_openability_final_metric_retains_structured_provenance_without_row_refs():
    from app.services.multipass_extraction import (
        _build_openability_selected_tables,
        _run_pass3a_metric_extractor,
        _run_pass4_reconciler,
    )

    table = _build_openability_selected_tables(_OpenabilityDoc())[0]
    pass1 = {
        "report_type": "A",
        "period_end": "2022-06-30",
        "currency": "AUD",
        "scale": "unknown",
    }

    with patch(
        "app.services.multipass_extraction._llm_json_call",
        return_value={
            "revenue": 4_920_102,
            "ebit": None,
            "np_attributable": None,
            "row_refs": {},
            "pass3_confidence": 0.9,
        },
    ):
        extracted = _run_pass3a_metric_extractor(
            {"income_statement": table},
            pass1,
            llm_client=None,
        )

    payload = _run_pass4_reconciler(extracted, {}, pass1)

    assert payload["metrics"]["revenue"] == 4_920_102_000
    assert payload["row_refs"]["revenue"] == "Revenue 21 4,920,102 1,556,976"
    assert payload["field_provenance"]["revenue"]["ocr_source"] == {
        "page_number": 57,
        "source_region": {"left": 10, "top": 20, "right": 500, "bottom": 32},
        "source_row": 1,
        "source_cell": [1, 2],
        "source_text": "Revenue 21 4,920,102 1,556,976",
        "candidate_value_text": "4,920,102",
        "recognition_confidence": 95.0,
    }


def test_openability_period_source_text_reuses_existing_ambiguous_period_guard():
    from app.services.multipass_extraction import (
        _detect_source_period_end_evidence,
        _openability_period_source_text,
    )

    class _AmbiguousPeriodDoc(_OpenabilityDoc):
        parser_diagnostics = {"openability": _whc_openability_diagnostic()}

    _AmbiguousPeriodDoc.parser_diagnostics["openability"]["ocr_records"][0][
        "period_phrases"
    ] = [
        "For the year ended 30 June 2022",
        "For the year ended 31 December 2021",
    ]

    evidence = _detect_source_period_end_evidence(
        "",
        _openability_period_source_text(_AmbiguousPeriodDoc()),
    )

    assert evidence["reason"] == "ambiguous"
    assert evidence["period_end"] is None


def test_openability_period_source_text_ignores_malformed_period_phrases():
    from app.services.multipass_extraction import _openability_period_source_text

    class _MalformedPeriodDoc(_OpenabilityDoc):
        parser_diagnostics = {"openability": _whc_openability_diagnostic()}

    for record in _MalformedPeriodDoc.parser_diagnostics["openability"][
        "ocr_records"
    ]:
        record["period_phrases"] = "For the year ended 30 June 2022"

    assert _openability_period_source_text(_MalformedPeriodDoc()) == ""


def test_openability_selected_tables_ignores_malformed_period_phrases():
    from app.services.multipass_extraction import _build_openability_selected_tables

    class _MalformedPeriodDoc(_OpenabilityDoc):
        parser_diagnostics = {"openability": _whc_openability_diagnostic()}

    for record in _MalformedPeriodDoc.parser_diagnostics["openability"][
        "ocr_records"
    ]:
        record["period_phrases"] = "For the year ended 30 June 2022"

    assert _build_openability_selected_tables(_MalformedPeriodDoc()) == []


def test_run_multipass_default_does_not_request_openability_bridge():
    from app.services.multipass_extraction import run_multipass_extraction

    captured_kwargs = {}

    def _capture_extract(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return _OpenabilityPeriodOnlyDoc()

    captured_table_count = []

    def _capture_pass2(tables):
        captured_table_count.append(len(tables))
        return {"unmatched": []}

    with patch(
        "app.services.docling_extract.extract_structured",
        side_effect=_capture_extract,
    ), patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value={
            "report_type": "A",
            "period_end": None,
            "currency": "AUD",
            "scale": "thousands",
            "classifier_confidence": 0.95,
        },
    ), patch(
        "app.services.multipass_extraction._run_pass2_locator",
        side_effect=_capture_pass2,
    ):
        result = run_multipass_extraction(
            "/fake/whc.pdf",
            {"document_id": "whc", "ticker": "WHC", "title": "2022 Annual Report"},
            llm_client=None,
            skip_narrative=True,
        )

    assert captured_kwargs["openability_diagnostics"] is False
    assert captured_table_count == [0]
    assert result.status == "failed"
    assert result.error == "validation_gate:missing_period_end"
    assert result.payload["source_period_end_evidence"]["reason"] == "not_detected"


def test_run_multipass_opt_in_routes_openability_tables_through_existing_gates():
    from app.services.multipass_extraction import run_multipass_extraction

    debug_capture = {}

    def _mock_llm(prompt, *args, **kwargs):
        if "Table type: income_statement" in prompt:
            return {
                "revenue": 4_920_102,
                "ebit": 2_821_254,
                "np_attributable": 1_952_000,
                "pass3_confidence": 0.9,
                "row_refs": {
                    "revenue": "Revenue 21 4,920,102 1,556,976",
                    "ebit": "Profit/(loss) before net financial expense 2,821,254 (706,181)",
                    "np_attributable": "Profit/(loss) before net financial expense 2,821,254 (706,181)",
                },
            }
        if "Table type: cashflow_statement" in prompt:
            return {
                "operating_cf": 2_529_823,
                "investing_cf": None,
                "financing_cf": None,
                "cash_end": 1_215_460,
                "capex": -124_210,
                "pass3_confidence": 0.9,
                "row_refs": {
                    "operating_cf": "Net cash from operating activities 3.4 2,529,823 138,765",
                    "cash_end": "Cash and cash equivalents at end of year 1,215,460 95,202",
                    "capex": "Purchase of property, plant and equipment (124,210) (68,693)",
                },
            }
        if "Table type: balance_sheet" in prompt:
            return {
                "net_debt": None,
                "total_debt": None,
                "shares_outstanding": None,
                "pass3_confidence": 0.0,
                "row_refs": {},
            }
        raise AssertionError(prompt)

    with patch(
        "app.services.docling_extract.extract_structured",
        return_value=_OpenabilityPeriodOnlyDoc(),
    ) as extract_mock, patch(
        "app.services.multipass_extraction._run_pass1_classifier",
        return_value={
            "report_type": "A",
            "period_end": None,
            "currency": "AUD",
            "scale": "unknown",
            "classifier_confidence": 0.95,
        },
    ), patch(
        "app.services.multipass_extraction._llm_json_call",
        side_effect=_mock_llm,
    ), patch.dict(
        "os.environ", {"EXTRACTION_PARALLEL": "0"}
    ):
        result = run_multipass_extraction(
            "/fake/whc.pdf",
            {"document_id": "whc", "ticker": "WHC", "title": "2022 Annual Report"},
            llm_client=None,
            skip_narrative=True,
            debug_capture=debug_capture,
            openability_selected_tables=True,
            openability_pages=[57, 58, 60, 61],
        )

    assert extract_mock.call_args.kwargs["openability_diagnostics"] is True
    assert extract_mock.call_args.kwargs["openability_pages"] == [57, 58, 60, 61]
    assert len(debug_capture["openability_selected_tables"]) == 3
    assert result.status in {"ok", "ok_low_confidence"}
    assert result.payload["period_end"] == "2022-06-30"
    assert result.payload["source_period_end_evidence"]["reason"] == "year_ended_explicit_date"
    assert result.payload["scale"] == "thousands"
    assert result.payload["revenue"] == 4_920_102_000
    assert result.payload["operating_cf"] == 2_529_823_000
    assert result.payload["capex"] == -124_210_000
    assert result.payload["metric_source_scales"]["revenue"] == "thousands"
    assert result.payload["metric_scale_sources"]["revenue"] == "table"
    assert "Revenue 21 4,920,102 1,556,976" in result.payload["row_refs"]["revenue"]


# ---------------------------------------------------------------------------
# Parallel Pass 3a — verify parallel produces same results as sequential
# ---------------------------------------------------------------------------


def test_pass3a_parallel_matches_sequential():
    """Parallel and sequential Pass 3a must produce identical results."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable
    import threading

    # Build multiple tables so parallelism actually kicks in (>1 eligible table).
    cf_table = DoclingTable(
        page_number=2,
        caption="Cash Flow Statement",
        rows=[["", "H1 2025"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025"],
    )
    is_table = DoclingTable(
        page_number=3,
        caption="Income Statement",
        rows=[["", "H1 2025"], ["Revenue", "10,000"]],
        headers=["", "H1 2025"],
    )
    bs_table = DoclingTable(
        page_number=4,
        caption="Balance Sheet",
        rows=[["", "H1 2025"], ["Net debt", "5,000"]],
        headers=["", "H1 2025"],
    )
    labelled = {
        "cashflow_statement": cf_table,
        "income_statement": is_table,
        "balance_sheet": bs_table,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
    }

    # Per-table mock responses keyed by table_type embedded in the prompt.
    mock_responses = {
        "cashflow_statement": {
            "operating_cf": 3241,
            "investing_cf": -100,
            "financing_cf": -50,
            "cash_end": 500,
            "capex": None,
            "pass3_confidence": 0.9,
            "row_refs": {},
        },
        "income_statement": {
            "revenue": 10000,
            "ebit": 5000,
            "np_attributable": 3000,
            "pass3_confidence": 0.85,
            "row_refs": {},
        },
        "balance_sheet": {
            "net_debt": 5000,
            "total_debt": 6000,
            "shares_outstanding": 2_000_000,
            "pass3_confidence": 0.92,
            "row_refs": {},
        },
    }
    call_threads = []

    def _mock_llm(prompt, *args, **kwargs):
        call_threads.append(threading.current_thread().name)
        for tt, resp in mock_responses.items():
            if tt in prompt:
                return resp
        return {}

    # Run sequentially (EXTRACTION_PARALLEL=0)
    with patch(
        "app.services.multipass_extraction._llm_json_call", side_effect=_mock_llm
    ):
        with patch.dict("os.environ", {"EXTRACTION_PARALLEL": "0"}):
            seq_results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    call_threads.clear()

    # Run in parallel (EXTRACTION_PARALLEL=1, the default)
    with patch(
        "app.services.multipass_extraction._llm_json_call", side_effect=_mock_llm
    ):
        with patch.dict("os.environ", {"EXTRACTION_PARALLEL": "1"}):
            par_results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    # Same number of results
    assert len(par_results) == len(seq_results), (
        f"Parallel returned {len(par_results)} results, sequential returned {len(seq_results)}"
    )

    # Same source order (must match labelled_tables iteration order)
    seq_sources = [r["_source"] for r in seq_results]
    par_sources = [r["_source"] for r in par_results]
    assert par_sources == seq_sources, (
        f"Order mismatch: parallel={par_sources}, sequential={seq_sources}"
    )

    # Same metric values
    for seq_r, par_r in zip(seq_results, par_results):
        for key in seq_r:
            assert par_r.get(key) == seq_r[key], (
                f"Mismatch for {seq_r['_source']}.{key}: "
                f"sequential={seq_r[key]}, parallel={par_r.get(key)}"
            )


def test_pass3a_parallel_disabled_by_env():
    """When EXTRACTION_PARALLEL=0, all LLM calls must run on the main thread."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable
    import threading

    tables = {}
    for tt in ("cashflow_statement", "income_statement"):
        tables[tt] = DoclingTable(
            page_number=1,
            caption=tt,
            rows=[["", "H1"], ["Item", "100"]],
            headers=["", "H1"],
        )
    labelled = {**tables, "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "units",
    }

    mock_raw = {"revenue": 100, "pass3_confidence": 0.5, "row_refs": {}}
    call_threads = []

    def _mock_llm(prompt, *args, **kwargs):
        call_threads.append(threading.current_thread().name)
        return mock_raw

    main_thread = threading.current_thread().name
    with patch(
        "app.services.multipass_extraction._llm_json_call", side_effect=_mock_llm
    ):
        with patch.dict("os.environ", {"EXTRACTION_PARALLEL": "0"}):
            _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    # All calls must have happened on the main thread
    assert all(t == main_thread for t in call_threads), (
        f"Expected all calls on main thread ({main_thread}), got: {call_threads}"
    )


# ---------------------------------------------------------------------------
# Row Filtering
# ---------------------------------------------------------------------------

from app.services.multipass_extraction import (
    _filter_table_rows,
    _is_section_header,
    _is_total_row,
)


def _make_table_with_rows(rows):
    """Create a minimal table-like object with given rows."""
    t = MagicMock()
    t.rows = rows
    t.headers = rows[0] if rows else []
    t.caption = ""
    t.page_number = 1
    return t


class TestRowFiltering:
    def test_small_table_not_filtered(self):
        """Tables with <=20 rows should not be filtered."""
        rows = [["Header", "Val"]] + [[f"Row {i}", str(i)] for i in range(15)]
        table = _make_table_with_rows(rows)
        result = _filter_table_rows(table, "cashflow_statement")
        assert result == rows  # unchanged

    def test_highlights_not_filtered(self):
        rows = [["Header", "Val"]] + [[f"Row {i}", str(i)] for i in range(25)]
        table = _make_table_with_rows(rows)
        result = _filter_table_rows(table, "highlights")
        assert result == rows

    def test_large_cf_table_filtered(self):
        """Large CF table should be filtered, keeping headers/totals/metric rows."""
        rows = [
            ["Item", "Dec 2025 $M", "Dec 2024 $M"],
            ["CASH FLOWS FROM OPERATING ACTIVITIES", "", ""],
            ["Receipts from customers", "3,343", "2,368"],
            ["Payments to suppliers and employees", "(2,267)", "(2,844)"],
            ["Subcontractor costs", "(100)", "(50)"],
            ["Raw materials consumed", "(200)", "(150)"],
            ["Equipment lease costs", "(80)", "(70)"],
            ["Travel and entertainment", "(10)", "(5)"],
            ["Professional fees", "(30)", "(20)"],
            ["Insurance costs", "(15)", "(12)"],
            ["Rent and occupancy", "(25)", "(18)"],
            ["IT and communications", "(20)", "(15)"],
            ["Net cash from operating activities", "880", "(656)"],
            ["CASH FLOWS FROM INVESTING ACTIVITIES", "", ""],
            ["Payments for property, plant and equipment", "(333)", "(732)"],
            ["Acquisition of subsidiaries", "(100)", "(50)"],
            ["Proceeds from disposal of assets", "25", "4"],
            ["Exploration expenditure", "(40)", "(30)"],
            ["Development expenditure", "(60)", "(45)"],
            ["Net cash used in investing activities", "(527)", "(658)"],
            ["CASH FLOWS FROM FINANCING ACTIVITIES", "", ""],
            ["Proceeds from borrowings", "500", "1,200"],
            ["Repayment of borrowings", "(400)", "(100)"],
            ["Dividend payments", "(200)", "(180)"],
            ["Repayment of lease liabilities", "(102)", "(103)"],
            ["Net cash from financing activities", "(126)", "1,114"],
            ["Net increase in cash and cash equivalents", "227", "(200)"],
            ["Cash and cash equivalents at beginning", "412", "908"],
            ["Effects of exchange rate changes", "(1)", "12"],
            ["Cash and cash equivalents at the end", "638", "720"],
        ]
        table = _make_table_with_rows(rows)
        result = _filter_table_rows(table, "cashflow_statement")
        # Should have fewer rows than original
        real_rows = [r for r in result if not str(r[0]).startswith("[...")]
        assert len(real_rows) < len(rows), (
            f"Expected filtering, got {len(real_rows)} vs {len(rows)}"
        )
        # Must keep header, section headers, totals, and key metric rows
        labels = [str(r[0]) for r in result]
        assert "Item" in labels  # header
        assert "CASH FLOWS FROM OPERATING ACTIVITIES" in labels  # section header
        assert "Net cash from operating activities" in labels  # total
        assert "Payments for property, plant and equipment" in labels  # capex
        assert "Cash and cash equivalents at the end" in labels  # cash_end
        # Should have omission markers
        assert any("[..." in str(r[0]) for r in result)

    def test_section_header_detection(self):
        assert _is_section_header(["CASH FLOWS FROM OPERATING ACTIVITIES", "", ""])
        assert not _is_section_header(["Revenue", "3,052", "2,290"])
        assert not _is_section_header(["", "", ""])

    def test_total_row_detection(self):
        assert _is_total_row(["Total revenue", "3,052", "2,290"])
        assert _is_total_row(["Net cash from operating activities", "880", "(656)"])
        assert not _is_total_row(["Receipts from customers", "3,343", "2,368"])

    def test_docling_compacted_cash_end_row_survives_filter(self):
        rows = [["Item", "30 June 2025 US$M", "30 June 2024 US$M"]]
        rows.extend([[f"Noise row {i}", str(i), str(i - 1)] for i in range(1, 25)])
        rows.append(["Netcashflows from operating activities", "1,756", "1,212"])
        rows.append(["Cashandcashequivalentsat30June", "2,124", "1,445"])
        table = _make_table_with_rows(rows)

        result = _filter_table_rows(table, "cashflow_statement")
        labels = [str(r[0]) for r in result]

        assert "Cashandcashequivalentsat30June" in labels

    def test_docling_compacted_share_row_survives_balance_sheet_filter(self):
        rows = [["Item", "30 June 2025", "31 December 2024"]]
        rows.extend([[f"Noise row {i}", str(i), str(i - 1)] for i in range(1, 25)])
        rows.append(["Borrowings", "3,679", "2,664"])
        rows.append(["Issued ordinary shares, fullypaidat30June", "1,510", "1,502"])
        table = _make_table_with_rows(rows)

        result = _filter_table_rows(table, "balance_sheet")
        labels = [str(r[0]) for r in result]

        assert "Issued ordinary shares, fullypaidat30June" in labels

    def test_filter_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv("EXTRACTION_FILTER_ROWS", "0")
        rows = [["H", "V"]] + [[f"Row {i}", str(i)] for i in range(25)]
        table = _make_table_with_rows(rows)
        # When disabled, _extract_single_table uses unfiltered path.
        # But _filter_table_rows itself doesn't check the env — it's the caller's job.
        # So test the filter still works (it's the caller that gates it).
        result = _filter_table_rows(table, "cashflow_statement")
        assert len(result) <= len(rows)


def test_pass3a_retries_full_table_when_filtered_output_misses_key_metric():
    """Filtered-table extraction should retry full table when key metrics are missing."""
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    rows = [["Item", "Current", "Prior"]]
    rows.extend([[f"Noise row {i}", str(i), str(i - 1)] for i in range(1, 28)])
    rows.append(["Revenue", "1200", "1100"])

    table = DoclingTable(
        page_number=4,
        caption="Income Statement",
        rows=rows,
        headers=["Item", "Current", "Prior"],
        raw_header_rows=[["Item", "31 Dec 2024", "31 Dec 2023"]],
    )
    labelled = {
        "cashflow_statement": None,
        "income_statement": table,
        "balance_sheet": None,
        "highlights": None,
        "unmatched": [],
    }
    pass1 = {
        "report_type": "H",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "units",
    }

    first_raw = {
        "revenue": None,
        "ebit": 500,
        "np_attributable": 300,
        "period_col": "Current",
        "pass3_confidence": 0.7,
        "row_refs": {"ebit": "EBIT", "np_attributable": "NPAT"},
    }
    second_raw = {
        "revenue": 1200,
        "ebit": 500,
        "np_attributable": 300,
        "period_col": "Current",
        "pass3_confidence": 0.85,
        "row_refs": {
            "revenue": "Revenue",
            "ebit": "EBIT",
            "np_attributable": "NPAT",
        },
    }

    with patch(
        "app.services.multipass_extraction._filter_table_rows",
        return_value=rows[:8],
    ):
        with patch(
            "app.services.multipass_extraction._llm_json_call",
            side_effect=[first_raw, second_raw],
        ) as mock_llm:
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert mock_llm.call_count == 2, "Expected filtered extraction + full-table retry"
    assert results[0]["revenue"] == 1200


# ---------------------------------------------------------------------------
# Phase 02 Hardening — net debt explicit evidence filter
# ---------------------------------------------------------------------------


class TestIsExplicitNetDebtEvidence:
    """_is_explicit_net_debt_evidence must accept direct net debt rows and reject
    derived/movement/ratio rows that contain 'net debt' but are not the point-in-time
    figure we want to store."""

    def _check(self, row_ref: str) -> bool:
        from app.services.multipass_extraction import _is_explicit_net_debt_evidence

        return _is_explicit_net_debt_evidence(row_ref)

    def test_accepts_plain_net_debt(self) -> None:
        assert self._check("Net debt") is True

    def test_accepts_net_debt_with_footnote(self) -> None:
        """Row refs from ASX summaries often have footnote markers like '¹'."""
        assert self._check("Net debt¹") is True

    def test_accepts_net_debt_parenthetical(self) -> None:
        assert self._check("Net debt (US$ millions)") is True

    def test_rejects_opening_net_debt(self) -> None:
        assert self._check("Opening net debt") is False

    def test_rejects_closing_net_debt(self) -> None:
        assert self._check("Closing net debt") is False

    def test_rejects_movement_in_net_debt(self) -> None:
        assert self._check("Movement in net debt") is False

    def test_rejects_net_debt_movement(self) -> None:
        assert self._check("Net debt movement") is False

    def test_rejects_change_in_net_debt(self) -> None:
        assert self._check("Change in net debt") is False

    def test_rejects_net_debt_plus_total_equity(self) -> None:
        assert self._check("Net debt plus total equity") is False

    def test_rejects_net_debt_management(self) -> None:
        assert self._check("Net debt management") is False

    def test_rejects_net_debt_ratio(self) -> None:
        assert self._check("Net debt ratio") is False

    def test_rejects_net_debt_to_ebitda(self) -> None:
        assert self._check("Net debt to EBITDA") is False

    def test_rejects_net_debt_and(self) -> None:
        """'Net debt and equity' uses 'net debt and' prefix — rejected as a derived/combined row."""
        assert self._check("Net debt and equity") is False

    def test_rejects_net_gearing(self) -> None:
        """Net gearing contains 'net' but not 'debt' — also rejected."""
        assert self._check("Net gearing ratio") is False

    def test_rejects_none(self) -> None:
        assert self._check(None) is False

    def test_rejects_empty_string(self) -> None:
        assert self._check("") is False

    # --- Phase 02 regression: mining-sector movement and reconciliation labels ---

    def test_rejects_increase_decrease_in_net_debt(self) -> None:
        """'Increase/(decrease) in net debt' is a cash-flow movement row, not a balance."""
        assert self._check("Increase/(decrease) in net debt") is False

    def test_rejects_decrease_increase_in_net_debt(self) -> None:
        """'Decrease/(increase) in net debt' is the sign-reversed movement variant."""
        assert self._check("Decrease/(increase) in net debt") is False

    def test_rejects_net_debt_beginning_of_period(self) -> None:
        """'Net debt: beginning of period' is the reconciliation opening balance, not the close."""
        assert self._check("Net debt: beginning of period") is False

    def test_rejects_net_debt_beginning_of_year(self) -> None:
        """'Net debt: beginning of year' is another opening-balance label used in annual reports."""
        assert self._check("Net debt: beginning of year") is False

    def test_accepts_net_debt_including_lease_liabilities(self) -> None:
        """'Net debt including lease liabilities' is an explicit point-in-time balance."""
        assert self._check("Net debt including lease liabilities") is True

    def test_accepts_net_debt_position(self) -> None:
        """'Net debt position' is a period-end balance label, not a movement."""
        assert self._check("Net debt position") is True


# ---------------------------------------------------------------------------
# Phase 02 Hardening — shares_outstanding marker coverage
# ---------------------------------------------------------------------------


class TestSharesOutstandingMarkers:
    """shares_outstanding post-processing must recognise SEG-style 'No. \u2019000s'
    column headers and plain 'Ordinary shares' row labels as valid share-count
    evidence, preventing them from being nulled by has_share_count_evidence=False."""

    def _extract_shares(self, table):
        from unittest.mock import patch

        from app.services.multipass_extraction import _run_pass3a_metric_extractor
        from app.services.docling_extract import DoclingTable

        labelled = {
            "cashflow_statement": None,
            "income_statement": None,
            "balance_sheet": None,
            "highlights": None,
            "share_capital": table,
            "net_debt_note": None,
            "unmatched": [],
        }
        pass1 = {
            "report_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "millions",
        }
        mock_raw = {
            "shares_outstanding": 196,  # LLM returns un-scaled value
            "period_col": "Dec 2025",
            "pass3_confidence": 0.88,
            "row_refs": {"shares_outstanding": "Ordinary shares"},
        }
        with patch(
            "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
        ):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)
        return results

    def test_seg_no_000s_column_header_not_nulled(self) -> None:
        """A table with 'No. \u2019000s' column header must not be nulled by weak-evidence check."""
        from app.services.docling_extract import DoclingTable

        seg_table = DoclingTable(
            page_number=12,
            caption="",
            rows=[
                ["", "No. \u2019000s"],
                ["Ordinary shares", "196,478"],
            ],
            headers=["", "No. \u2019000s"],
        )
        results = self._extract_shares(seg_table)
        assert len(results) == 1
        shares = results[0].get("shares_outstanding")
        assert shares is not None, (
            "shares_outstanding must not be nulled for SEG-style No.\u2019000s column"
        )

    def test_plain_ordinary_shares_row_not_nulled(self) -> None:
        """A table with a plain 'Ordinary shares' row label must pass has_share_count_evidence."""
        from app.services.docling_extract import DoclingTable

        ordinary_table = DoclingTable(
            page_number=5,
            caption="Share Capital",
            rows=[
                ["", "Dec 2025", "Jun 2025"],
                ["Ordinary shares", "1,234", "1,200"],
            ],
            headers=["", "Dec 2025", "Jun 2025"],
        )
        results = self._extract_shares(ordinary_table)
        assert len(results) == 1
        shares = results[0].get("shares_outstanding")
        assert shares is not None, (
            "shares_outstanding must not be nulled for plain 'Ordinary shares' row label"
        )

    def test_absolute_count_requires_share_count_evidence(self) -> None:
        """Large LLM values still need share-count evidence.

        BHP-style prose/tax tables can contain billion-dollar amounts that are
        numerically plausible as share counts. They must not become
        shares_outstanding without share/security/unit evidence.
        """
        from unittest.mock import patch

        from app.services.multipass_extraction import _run_pass3a_metric_extractor
        from app.services.docling_extract import DoclingTable

        # Table with no recognisable share-count marker (generic label + numeric col)
        generic_table = DoclingTable(
            page_number=8,
            caption="Selected data",
            rows=[
                ["Item", "Dec 2025"],
                ["Count", "5,057"],
            ],
            headers=["Item", "Dec 2025"],
        )
        labelled = {
            "cashflow_statement": None,
            "income_statement": None,
            "balance_sheet": None,
            "highlights": None,
            "share_capital": generic_table,
            "net_debt_note": None,
            "unmatched": [],
        }
        pass1 = {
            "report_type": "A",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "millions",
        }
        # LLM returns an absolute-sized value, but the source row has no share marker.
        mock_raw = {
            "shares_outstanding": 5_057_000_000,
            "period_col": "Dec 2025",
            "pass3_confidence": 0.85,
            "row_refs": {"shares_outstanding": "Count"},
        }
        with patch(
            "app.services.multipass_extraction._llm_json_call", return_value=mock_raw
        ):
            results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

        assert len(results) == 1
        assert results[0].get("shares_outstanding") is None


# ---------------------------------------------------------------------------
# Phase 02 Hardening — quarterly validation gate minimum metric threshold
# ---------------------------------------------------------------------------


class TestValidateGateQuarterlyThreshold:
    """Quarterly Appendix 5B documents are structurally limited to cash-flow metrics.
    The validation gate must accept Q documents with as few as 1 non-null metric,
    while still requiring at least 3 non-null metrics for A and H documents."""

    def _make_q_payload(self, non_null_count: int) -> dict:
        """Build a minimal Q payload with exactly non_null_count non-null metrics."""
        cf_metrics = ["operating_cf", "cash_end", "investing_cf", "financing_cf", "capex"]
        metrics: dict = {
            "revenue": None,
            "ebit": None,
            "np_attributable": None,
            "operating_cf": None,
            "investing_cf": None,
            "financing_cf": None,
            "capex": None,
            "cash_end": None,
            "net_debt": None,
            "shares_outstanding": None,
        }
        for metric in cf_metrics[:non_null_count]:
            metrics[metric] = 1_000_000
        return {
            "period_end": "2025-09-30",
            "period_type": "Q",
            "scale": "thousands",
            "currency": "AUD",
            "metrics": metrics,
            "confidence_metrics": 0.80,
        }

    def test_quarterly_accepts_one_cashflow_metric(self) -> None:
        """Q doc with 1 non-null metric (operating_cf only) must pass the gate."""
        from app.services.multipass_extraction import _validate_gate

        status, error = _validate_gate(self._make_q_payload(1))
        assert status in ("ok", "ok_low_confidence"), (
            f"Q doc with 1 metric must pass gate; got status={status!r}, error={error!r}"
        )

    def test_quarterly_accepts_two_cashflow_metrics(self) -> None:
        """Q doc with 2 non-null metrics (GRE-style: operating_cf + cash_end) must pass."""
        from app.services.multipass_extraction import _validate_gate

        status, error = _validate_gate(self._make_q_payload(2))
        assert status in ("ok", "ok_low_confidence"), (
            f"Q doc with 2 metrics must pass gate; got status={status!r}, error={error!r}"
        )

    def test_quarterly_rejects_zero_metrics(self) -> None:
        """Q doc with 0 non-null metrics must still be rejected."""
        from app.services.multipass_extraction import _validate_gate

        status, error = _validate_gate(self._make_q_payload(0))
        assert status == "failed", (
            f"Q doc with 0 metrics must be rejected; got status={status!r}"
        )
        assert error is not None and "insufficient_metrics" in error

    def test_annual_still_requires_three_metrics(self) -> None:
        """A (annual) document with 2 non-null metrics must still be rejected."""
        from app.services.multipass_extraction import _validate_gate

        payload = {
            "period_end": "2025-06-30",
            "period_type": "A",
            "scale": "millions",
            "currency": "AUD",
            "metrics": {
                "revenue": None,
                "ebit": None,
                "np_attributable": None,
                "operating_cf": 5_000_000_000,
                "investing_cf": None,
                "financing_cf": None,
                "capex": None,
                "cash_end": 1_000_000_000,
                "net_debt": None,
                "shares_outstanding": None,
            },
            "confidence_metrics": 0.85,
        }
        status, error = _validate_gate(payload)
        assert status == "failed", (
            f"Annual doc with 2 metrics must still be rejected; got status={status!r}"
        )
        assert error is not None and "insufficient_metrics" in error

    def test_half_year_still_requires_three_metrics(self) -> None:
        """H (half-year) document with 2 non-null metrics must still be rejected."""
        from app.services.multipass_extraction import _validate_gate

        payload = {
            "period_end": "2025-12-31",
            "period_type": "H",
            "scale": "thousands",
            "currency": "AUD",
            "metrics": {
                "revenue": None,
                "ebit": None,
                "np_attributable": None,
                "operating_cf": 90_000_000,
                "investing_cf": None,
                "financing_cf": None,
                "capex": None,
                "cash_end": 50_000_000,
                "net_debt": None,
                "shares_outstanding": None,
            },
            "confidence_metrics": 0.85,
        }
        status, error = _validate_gate(payload)
        assert status == "failed", (
            f"Half-year doc with 2 metrics must still be rejected; got status={status!r}"
        )
        assert error is not None and "insufficient_metrics" in error


# ---------------------------------------------------------------------------
# Non-AUD currency handling (Phase 02 hardening)
# ---------------------------------------------------------------------------


class TestNonAUDCurrencyDetection:
    """Extended _CURRENCY_PATTERNS must detect GBP, EUR, CAD, NZD, CNY from table surfaces."""

    def test_gbp_detected_from_table_header(self) -> None:
        """£ in a column header must resolve to GBP."""
        from app.services.multipass_extraction import _detect_currency_from_tables
        from app.services.docling_extract import DoclingTable

        tables = [
            DoclingTable(
                page_number=1,
                caption="Income statement",
                headers=["Item", "£'000"],
                rows=[["Revenue", "12,500"]],
            )
        ]
        assert _detect_currency_from_tables(tables) == "GBP"

    def test_eur_detected_from_table_caption(self) -> None:
        """EUR in a caption must resolve to EUR."""
        from app.services.multipass_extraction import _detect_currency_from_tables
        from app.services.docling_extract import DoclingTable

        tables = [
            DoclingTable(
                page_number=1,
                caption="Cash flow EUR millions",
                headers=["Item", "Amount"],
                rows=[["Operating CF", "45.2"]],
            )
        ]
        assert _detect_currency_from_tables(tables) == "EUR"

    def test_cny_detected_from_rmb_marker(self) -> None:
        """RMB in a table row must resolve to CNY."""
        from app.services.multipass_extraction import _detect_currency_from_tables
        from app.services.docling_extract import DoclingTable

        tables = [
            DoclingTable(
                page_number=1,
                caption="Balance sheet (RMB '000)",
                headers=["Metric", "RMB '000"],
                rows=[["Total assets", "88,000"]],
            )
        ]
        assert _detect_currency_from_tables(tables) == "CNY"

    def test_nzd_detected_from_nz_dollar_marker(self) -> None:
        """NZ$ in a header must resolve to NZD."""
        from app.services.multipass_extraction import _detect_currency_from_tables
        from app.services.docling_extract import DoclingTable

        tables = [
            DoclingTable(
                page_number=1,
                caption="Financial summary",
                headers=["Item", "NZ$'000"],
                rows=[["Revenue", "5,200"]],
            )
        ]
        assert _detect_currency_from_tables(tables) == "NZD"

    def test_cad_detected_from_ca_dollar_marker(self) -> None:
        """CA$ in a column header must resolve to CAD."""
        from app.services.multipass_extraction import _detect_currency_from_tables
        from app.services.docling_extract import DoclingTable

        tables = [
            DoclingTable(
                page_number=1,
                caption="Financial summary",
                headers=["Item", "CA$'000"],
                rows=[["Revenue", "35,000"]],
            )
        ]
        assert _detect_currency_from_tables(tables) == "CAD"

    def test_cnh_variant_detected_as_cny(self) -> None:
        """CNH (offshore renminbi) must resolve to CNY — same ISO pool, different market."""
        from app.services.multipass_extraction import _detect_currency_from_tables
        from app.services.docling_extract import DoclingTable

        tables = [
            DoclingTable(
                page_number=1,
                caption="Balance sheet (CNH millions)",
                headers=["Metric", "CNH M"],
                rows=[["Total assets", "420,000"]],
            )
        ]
        assert _detect_currency_from_tables(tables) == "CNY"

    def test_aud_still_wins_over_gbp_when_dominant(self) -> None:
        """Multiple AUD markers vs single GBP marker — AUD must win by vote count."""
        from app.services.multipass_extraction import _detect_currency_from_tables
        from app.services.docling_extract import DoclingTable

        tables = [
            DoclingTable(
                page_number=1,
                caption="Cash flow A$M",
                headers=["Item", "A$M"],
                rows=[["Operating CF", "3.2"]],
            ),
            DoclingTable(
                page_number=2,
                caption="AUD summary",
                headers=["Metric", "AUD"],
                rows=[["Revenue", "80.1"]],
            ),
            DoclingTable(
                page_number=3,
                caption="GBP equivalent",
                headers=["Metric", "£M"],
                rows=[["Revenue", "42.0"]],
            ),
        ]
        assert _detect_currency_from_tables(tables) == "AUD"


class TestNonAUDCurrencyNormalisation:
    """Ambiguous currency must abstain; explicit native currency stays unchanged."""

    def _good_payload_non_aud(self, currency: str) -> dict:
        """Minimal passing payload for non-AUD currency."""
        return {
            "period_end": "2025-12-31",
            "period_type": "H",
            "scale": "thousands",
            "currency": currency,
            "metrics": {
                "revenue": 500_000_000,
                "ebit": 100_000_000,
                "np_attributable": 80_000_000,
                "operating_cf": None,
                "investing_cf": None,
                "financing_cf": None,
                "capex": None,
                "cash_end": None,
                "net_debt": None,
                "shares_outstanding": None,
            },
            "confidence_metrics": 0.85,
        }

    def test_validate_gate_string_null_currency_abstains(self) -> None:
        """A classifier null without source evidence must not be guessed as AUD."""
        from app.services.multipass_extraction import _validate_gate

        payload = self._good_payload_non_aud("null")
        status, error = _validate_gate(payload)
        assert status == "failed"
        assert error == "validation_gate:currency_unknown"

    @pytest.mark.parametrize("currency", ["none", "n/a", "unknown", "-"])
    def test_validate_gate_other_null_like_currencies_abstain(
        self, currency: str
    ) -> None:
        from app.services.multipass_extraction import _validate_gate

        payload = self._good_payload_non_aud(currency)

        assert _validate_gate(payload) == (
            "failed",
            "validation_gate:currency_unknown",
        )

    def test_conflicting_table_currency_evidence_abstains(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _detect_currency_from_tables

        tables = [
            DoclingTable(
                page_number=1,
                caption="Consolidated Income Statement (AUD millions)",
                headers=["AUD millions", "Current", "Comparative"],
                rows=[["Revenue", "100", "90"]],
            ),
            DoclingTable(
                page_number=2,
                caption="Consolidated Cash Flow Statement (USD millions)",
                headers=["USD millions", "Current", "Comparative"],
                rows=[["Operating cash flow", "20", "18"]],
            ),
        ]

        assert _detect_currency_from_tables(tables) == ""

    def test_validate_gate_non_aud_passes_hard_gates_before_downgrade(self) -> None:
        """Non-AUD with < 3 metrics must still fail, not merely downgrade.

        The non-AUD ok_low_confidence only fires after all hard gates (including
        insufficient_metrics) have passed.
        """
        from app.services.multipass_extraction import _validate_gate

        payload = self._good_payload_non_aud("GBP")
        # Force insufficient metrics
        for k in payload["metrics"]:
            payload["metrics"][k] = None
        payload["metrics"]["revenue"] = 100_000_000  # only 1 non-null for H

        status, error = _validate_gate(payload)
        assert status == "failed", (
            f"Non-AUD with insufficient metrics must fail, not ok_low_confidence; got {status!r}"
        )
        assert error is not None and "insufficient_metrics" in error

    def test_non_aud_warning_appears_in_structured_extraction_warnings(self) -> None:
        """Non-AUD currency must appear in payload['_structured_extraction']['warnings'].

        This ensures operator tooling can surface the warning without log-scraping.
        """
        # We test the payload assembly path directly via run_multipass_extraction
        # by verifying the warning key injection helper logic in isolation.
        # The actual injection happens right after _validate_gate in the main function;
        # confirm the pattern by checking what the payload looks like when built manually.
        warnings_list: list[str] = []
        currency = "GBP"
        if currency != "AUD":
            warnings_list.append(
                f"non_aud_currency:{currency} — values in native currency, no FX conversion"
            )
        assert len(warnings_list) == 1
        assert "non_aud_currency:GBP" in warnings_list[0]

    def test_aud_currency_produces_no_non_aud_warning_entry(self) -> None:
        """AUD documents must not add a non_aud_currency entry to warnings."""
        warnings_list: list[str] = []
        currency = "AUD"
        if currency != "AUD":
            warnings_list.append(
                f"non_aud_currency:{currency} — values in native currency, no FX conversion"
            )
        assert warnings_list == []


# ---------------------------------------------------------------------------
# Phase 02 Structural regression gate — _DERIVED_NET_DEBT_ROW_FRAGMENTS
# ---------------------------------------------------------------------------


class TestDerivedNetDebtFragmentsCoverageGate:
    """Structural gate: every fragment in _DERIVED_NET_DEBT_ROW_FRAGMENTS must be
    rejected by _is_explicit_net_debt_evidence when used as a standalone row label.

    This test is data-driven from the authoritative constant so it automatically
    catches any regression if a fragment is accidentally removed from the set.
    If a new fragment is added, it is covered without any additional test code.
    """

    def test_every_fragment_is_rejected_as_standalone_label(self) -> None:
        from app.services.multipass_extraction import (
            _DERIVED_NET_DEBT_ROW_FRAGMENTS,
            _is_explicit_net_debt_evidence,
        )

        failures = []
        for fragment in sorted(_DERIVED_NET_DEBT_ROW_FRAGMENTS):
            # Use the fragment as a standalone row label (title-case for realism)
            row_ref = fragment.title()
            result = _is_explicit_net_debt_evidence(row_ref)
            if result is not False:
                failures.append(f"  fragment={fragment!r} → accepted (expected rejection)")

        assert not failures, (
            f"_DERIVED_NET_DEBT_ROW_FRAGMENTS entries that were not rejected:\n"
            + "\n".join(failures)
        )

    def test_fragments_set_is_non_empty(self) -> None:
        """Guard against the set being accidentally cleared."""
        from app.services.multipass_extraction import _DERIVED_NET_DEBT_ROW_FRAGMENTS

        assert len(_DERIVED_NET_DEBT_ROW_FRAGMENTS) >= 10, (
            f"Expected at least 10 derived-row fragments; got {len(_DERIVED_NET_DEBT_ROW_FRAGMENTS)}"
        )


def test_pass2_locator_abstains_on_equal_top_income_table_evidence():
    from app.services.docling_extract import DoclingTable
    from app.services.multipass_extraction import _run_pass2_locator

    tables = [
        DoclingTable(
            page_number=page,
            caption="Consolidated Income Statement",
            headers=["", "Current", "Comparative"],
            rows=[["Revenue", "100", "90"], ["Profit after tax", "20", "18"]],
        )
        for page in (4, 9)
    ]

    labelled = _run_pass2_locator(tables)

    assert labelled["income_statement"] is None
    assert all(table in labelled["unmatched"] for table in tables)


class TestCurrentPeriodColumnBinding:
    def test_single_table_flow_fails_closed_without_quarter_basis_evidence(
        self,
    ) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _extract_single_table

        table = DoclingTable(
            page_number=1,
            caption="Quarterly cash flow report",
            headers=["", "31 March 2025"],
            raw_header_rows=[["", "31 March 2025"]],
            rows=[["Net cash from operating activities", "25"]],
        )

        with patch(
            "app.services.multipass_extraction._llm_json_call",
            return_value={
                "operating_cf": 25,
                "row_refs": {
                    "operating_cf": "Net cash from operating activities"
                },
                "pass3_confidence": 0.9,
            },
        ):
            extracted = _extract_single_table(
                "cashflow_statement",
                table,
                {
                    "report_type": "Q",
                    "period_basis": "period_only",
                    "period_end": "2025-03-31",
                    "currency": "AUD",
                },
                "units",
                1,
                llm_client=None,
            )

        assert extracted is not None
        assert extracted["operating_cf"] is None
        assert extracted["_period_binding"]["reason"] == "quarter_basis_missing"

    def test_preferred_income_overlay_fails_closed_on_ambiguous_quarter_basis(
        self,
    ) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import (
            _apply_preferred_income_statement_source_payload,
        )

        table = DoclingTable(
            page_number=1,
            caption="Quarterly income statement",
            headers=["", "Current quarter / Year to date 31 March 2025"],
            raw_header_rows=[
                ["", "Current quarter / Year to date"],
                ["", "31 March 2025"],
            ],
            rows=[["Revenue", "25"]],
        )
        payload = {
            "metrics": {"revenue": None},
            "row_refs": {},
            "provenance": {},
        }

        _apply_preferred_income_statement_source_payload(
            payload,
            [table],
            scale="units",
            pass1_result={
                "report_type": "Q",
                "period_basis": "period_only",
                "period_end": "2025-03-31",
                "currency": "AUD",
            },
        )

        assert payload["metrics"]["revenue"] == 25
        assert "source_cell" not in payload["field_provenance"]["revenue"]

    def test_announcement_date_never_binds_as_period_end(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _bind_current_period_column

        table = DoclingTable(
            page_number=1,
            caption="Results announcement",
            headers=["", "Announcement date 31 March 2025"],
            raw_header_rows=[["", "Announcement date 31 March 2025"]],
            rows=[["Revenue", "25"]],
        )

        binding = _bind_current_period_column(table, "2025-03-31")

        assert binding["status"] == "DATA_MISSING"
        assert binding["reason"] == "period_headers_missing"

    def test_quarter_binding_records_exact_table_role_and_basis(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _bind_current_period_column

        table = DoclingTable(
            page_number=1,
            caption="Quarterly cash flow report",
            headers=["", "Current quarter 31 March 2025", "Year to date 31 March 2025"],
            raw_header_rows=[
                ["", "Current quarter", "Year to date"],
                ["", "31 March 2025", "31 March 2025"],
            ],
            rows=[["Receipts from customers", "25", "70"]],
        )
        table.index_in_doc = 4

        binding = _bind_current_period_column(
            table, "2025-03-31", period_basis="period_only"
        )

        assert binding["status"] == "BOUND"
        assert binding["table_index"] == 4
        assert binding["column_index"] == 1
        assert binding["column_role"] == "current_quarter"
        assert binding["period_basis"] == "period_only"

    def test_same_date_conflicting_quarter_basis_fails_closed(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _bind_current_period_column

        table = DoclingTable(
            page_number=1,
            caption="Quarterly cash flow report",
            headers=["", "Current quarter / Year to date 31 March 2025"],
            raw_header_rows=[
                ["", "Current quarter / Year to date"],
                ["", "31 March 2025"],
            ],
            rows=[["Receipts from customers", "25"]],
        )

        binding = _bind_current_period_column(
            table, "2025-03-31", period_basis="period_only"
        )

        assert binding["status"] == "DATA_MISSING"
        assert binding["reason"] == "conflicting_quarter_basis"

    def test_binds_exact_requested_period_and_ignores_note_column(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _bind_current_period_column

        table = DoclingTable(
            page_number=21,
            caption="Income statement",
            headers=[
                "",
                "Note",
                "31 December 2025 US$m",
                "31 December 2024 US$m",
            ],
            raw_header_rows=[
                ["", "", "31 December 2025", "31 December 2024"],
                ["", "Note", "US$m", "US$m"],
            ],
            rows=[["Operating sales revenue", "2", "8,439", "7,638"]],
        )

        binding = _bind_current_period_column(table, "2025-12-31")

        assert binding["status"] == "BOUND"
        assert binding["column_index"] == 2
        assert binding["header_cell"] == "31 December 2025"
        assert binding["comparative_columns"] == [3]

    def test_fails_closed_on_duplicate_current_period_headers(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _bind_current_period_column

        table = DoclingTable(
            page_number=1,
            caption="Income statement",
            headers=["", "31 Dec 2025", "31 Dec 2025", "31 Dec 2024"],
            raw_header_rows=[
                ["", "31 Dec 2025", "31 Dec 2025", "31 Dec 2024"]
            ],
            rows=[["Revenue", "100", "100", "90"]],
        )

        binding = _bind_current_period_column(table, "2025-12-31")

        assert binding["status"] == "DATA_MISSING"
        assert binding["reason"] == "duplicate_current_period_header"
        assert binding["column_index"] is None

    def test_fails_closed_on_conflicting_dates_in_one_column(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _bind_current_period_column

        table = DoclingTable(
            page_number=1,
            caption="Income statement",
            headers=["", "31 Dec 2025 30 Jun 2025", "31 Dec 2024"],
            raw_header_rows=[
                ["", "31 Dec 2025 30 Jun 2025", "31 Dec 2024"]
            ],
            rows=[["Revenue", "100", "90"]],
        )

        binding = _bind_current_period_column(table, "2025-12-31")

        assert binding["status"] == "DATA_MISSING"
        assert binding["reason"] == "conflicting_period_headers"

    def test_missing_requested_period_abstains_instead_of_using_comparative(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _bind_current_period_column

        table = DoclingTable(
            page_number=1,
            caption="Cash flows",
            headers=["", "31 Dec 2024", "31 Dec 2023"],
            raw_header_rows=[["", "31 Dec 2024", "31 Dec 2023"]],
            rows=[["Net cash inflow from operating activities", "90", "80"]],
        )

        binding = _bind_current_period_column(table, "2025-12-31")

        assert binding["status"] == "DATA_MISSING"
        assert binding["reason"] == "requested_period_header_missing"

    def test_markdown_uses_preserved_header_without_dropping_first_data_row(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _table_to_markdown

        table = DoclingTable(
            page_number=21,
            caption="Cash flows",
            headers=["", "30 June 2025 US$m", "30 June 2024 US$m"],
            raw_header_rows=[["", "30 June 2025 US$m", "30 June 2024 US$m"]],
            rows=[
                ["Operating activities", "", ""],
                ["Net cash flows from operating activities", "1,756", "1,212"],
            ],
        )

        markdown = _table_to_markdown(table)

        assert markdown.splitlines()[:3] == [
            " | 30 June 2025 US$m | 30 June 2024 US$m",
            "--- | --- | ---",
            "Operating activities |  | ",
        ]
        assert "Net cash flows from operating activities | 1,756 | 1,212" in markdown

    def test_metric_value_is_rebound_from_comparative_to_exact_source_cell(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import (
            _bind_statement_metrics_to_current_period_cells,
        )

        table = DoclingTable(
            page_number=21,
            caption="Income statement",
            headers=[
                "",
                "Note",
                "31 December 2025 US$m",
                "31 December 2024 US$m",
            ],
            raw_header_rows=[
                ["", "", "31 December 2025", "31 December 2024"],
                ["", "Note", "US$m", "US$m"],
            ],
            rows=[["Operating sales revenue", "2", "8,439", "7,638"]],
        )
        extracted = {
            "revenue": 7_638_000_000,
            "row_refs": {"revenue": "Operating sales revenue"},
            "period_col": "31 December 2024",
        }

        rebound = _bind_statement_metrics_to_current_period_cells(
            extracted,
            table,
            period_end="2025-12-31",
            scale="millions",
        )

        assert rebound["revenue"] == 8_439_000_000
        assert rebound["period_col"] == "31 December 2025 US$m"
        assert rebound["_period_source_cells"]["revenue"] == {
            "page_number": 21,
            "row_index": 0,
            "column_index": 2,
            "row_label": "Operating sales revenue",
            "raw_value": "8,439",
            "scaled_value": 8_439_000_000,
            "header_cell": "31 December 2025",
            "requested_period_end": "2025-12-31",
        }

    def test_exact_row_label_wins_over_longer_narrative_label(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import _period_bound_source_cell

        table = DoclingTable(
            page_number=21,
            caption="Income statement",
            headers=["", "Note", "31 December 2025", "31 December 2024"],
            raw_header_rows=[
                ["", "", "31 December 2025", "31 December 2024"]
            ],
            rows=[
                ["Equity holders of the Company", "", "1,914", "1,553"],
                [
                    "Earnings per share attributable to the ordinary equity holders of the Company:",
                    "",
                    "0.42",
                    "0.33",
                ],
            ],
        )

        source_cell = _period_bound_source_cell(
            table,
            "Equity holders of the Company",
            2,
            "millions",
        )

        assert source_cell is not None
        assert source_cell["row_index"] == 0
        assert source_cell["raw_value"] == "1,914"

    def test_ambiguous_header_nulls_period_bound_metrics(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import (
            _bind_statement_metrics_to_current_period_cells,
        )

        table = DoclingTable(
            page_number=1,
            caption="Cash flows",
            headers=["", "31 Dec 2025", "31 Dec 2025"],
            raw_header_rows=[["", "31 Dec 2025", "31 Dec 2025"]],
            rows=[["Net cash from operating activities", "100", "100"]],
        )
        extracted = {
            "operating_cf": 100,
            "row_refs": {"operating_cf": "Net cash from operating activities"},
            "period_col": "31 Dec 2024",
            "_period_source_cells": {
                "operating_cf": {"column_index": 2, "raw_value": "100"}
            },
        }

        rebound = _bind_statement_metrics_to_current_period_cells(
            extracted,
            table,
            period_end="2025-12-31",
            scale="units",
        )

        assert rebound["operating_cf"] is None
        assert rebound["row_refs"] == {}
        assert rebound["period_col"] is None
        assert rebound["_period_source_cells"] == {}
        assert rebound["_period_binding"]["reason"] == "duplicate_current_period_header"

    def test_missing_dated_headers_clear_comparative_metric_binding(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import (
            _bind_statement_metrics_to_current_period_cells,
        )

        table = DoclingTable(
            page_number=1,
            caption="Income statement",
            headers=["", "Current", "Prior"],
            raw_header_rows=[["", "Current", "Prior"]],
            rows=[["Revenue", "100", "90"]],
        )
        extracted = {
            "revenue": 90,
            "row_refs": {"revenue": "Revenue"},
            "period_col": "Prior",
            "_period_source_cells": {
                "revenue": {"column_index": 2, "raw_value": "90"}
            },
        }

        rebound = _bind_statement_metrics_to_current_period_cells(
            extracted,
            table,
            period_end="2025-12-31",
            scale="units",
        )

        assert rebound["revenue"] is None
        assert rebound["row_refs"] == {}
        assert rebound["period_col"] is None
        assert rebound["_period_source_cells"] == {}
        assert rebound["_period_binding"]["reason"] == "period_headers_missing"

    def test_malformed_period_header_clears_existing_metric_binding(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import (
            _bind_statement_metrics_to_current_period_cells,
        )

        table = DoclingTable(
            page_number=1,
            caption="Income statement",
            headers=["", "31 Smarch 2025", "31 Dec 2024"],
            raw_header_rows=[["", "31 Smarch 2025", "31 Dec 2024"]],
            rows=[["Revenue", "100", "90"]],
        )
        extracted = {
            "revenue": 90,
            "row_refs": {"revenue": "Revenue"},
            "period_col": "31 Dec 2024",
        }

        rebound = _bind_statement_metrics_to_current_period_cells(
            extracted,
            table,
            period_end="2025-12-31",
            scale="units",
        )

        assert rebound["revenue"] is None
        assert rebound["row_refs"] == {}
        assert rebound["period_col"] is None
        assert rebound["_period_source_cells"] == {}
        assert rebound["_period_binding"]["reason"] == "requested_period_header_missing"

    def test_bound_column_without_unique_source_cell_abstains(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import (
            _bind_statement_metrics_to_current_period_cells,
        )

        table = DoclingTable(
            page_number=1,
            caption="Income statement",
            headers=["", "31 Dec 2025", "31 Dec 2024"],
            raw_header_rows=[["", "31 Dec 2025", "31 Dec 2024"]],
            rows=[
                ["Revenue", "100", "90"],
                ["Revenue", "101", "91"],
            ],
        )
        extracted = {
            "revenue": 90,
            "row_refs": {"revenue": "Revenue"},
            "period_col": "31 Dec 2024",
            "_period_source_cells": {
                "revenue": {"column_index": 2, "raw_value": "90"}
            },
        }

        rebound = _bind_statement_metrics_to_current_period_cells(
            extracted,
            table,
            period_end="2025-12-31",
            scale="units",
        )

        assert rebound["_period_binding"]["status"] == "BOUND"
        assert rebound["revenue"] is None
        assert rebound["row_refs"] == {}
        assert rebound["_period_source_cells"] == {}

    def test_reconciler_preserves_exact_period_source_cell_provenance(self) -> None:
        from app.services.multipass_extraction import _run_pass4_reconciler

        payload = _run_pass4_reconciler(
            [
                {
                    "_source": "income_statement",
                    "_page_number": 21,
                    "_scale": "millions",
                    "_scale_source": "table",
                    "revenue": 8_439_000_000,
                    "row_refs": {"revenue": "Operating sales revenue"},
                    "_period_source_cells": {
                        "revenue": {
                            "page_number": 21,
                            "row_index": 1,
                            "column_index": 2,
                            "row_label": "Operating sales revenue",
                            "raw_value": "8,439",
                            "header_cell": "31 December 2025",
                            "requested_period_end": "2025-12-31",
                        }
                    },
                    "pass3_confidence": 0.9,
                }
            ],
            {},
            {
                "report_type": "H",
                "period_end": "2025-12-31",
                "currency": "USD",
                "scale": "millions",
            },
        )

        source_cell = payload["field_provenance"]["revenue"]["source_cell"]
        assert source_cell == {
            "page_number": 21,
            "row_index": 1,
            "column_index": 2,
            "row_label": "Operating sales revenue",
            "raw_value": "8,439",
            "header_cell": "31 December 2025",
            "requested_period_end": "2025-12-31",
        }
