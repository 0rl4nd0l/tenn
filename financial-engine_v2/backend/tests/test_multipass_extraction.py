"""
Unit tests for the 4-pass multipass extraction pipeline.
LLM calls are mocked — these test logic, not model quality.
"""
import pytest
from unittest.mock import patch, MagicMock


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

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_response):
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

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_response):
        result = _run_pass1_classifier(title="", first_page_text="", llm_client=None)

    assert result["classifier_confidence"] < 0.6


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
        rows=[["Row", "Current", "Prior"], ["Net cash from operations", "3,241", "2,876"]],
        headers=["Row", "Current", "Prior"],
    )
    result = _run_pass2_locator([cashflow_table])
    assert result["cashflow_statement"] is cashflow_table
    assert result["income_statement"] is None


def test_pass2_higher_score_wins_on_conflict():
    """When two tables match the same type, the one with more keyword matches wins."""
    from app.services.multipass_extraction import _run_pass2_locator
    from app.services.docling_extract import DoclingTable

    weak = DoclingTable(page_number=1, caption="cash",
                        rows=[["cash flow", "100"]], headers=[])
    strong = DoclingTable(page_number=3, caption="Cash Flow Statement — Financing Activities",
                          rows=[["net cash from operations", "1000"],
                                ["financing activities", "200"]], headers=[])
    result = _run_pass2_locator([weak, strong])
    assert result["cashflow_statement"] is strong


# ---------------------------------------------------------------------------
# Pass 3a — Scale normalisation and negative values
# ---------------------------------------------------------------------------

def test_pass3a_applies_thousands_multiplier():
    """Metric values must be multiplied by 1000 when scale=thousands."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Cash Flow Statement",
        rows=[["", "H1 2025"], ["Net cash from operations", "3,241"]],
        headers=["", "H1 2025"],
    )
    labelled = {"cashflow_statement": table, "income_statement": None,
                "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {"report_type": "H", "period_end": "2024-12-31",
             "currency": "AUD", "scale": "thousands"}

    mock_raw = {
        "operating_cf": 3241,
        "investing_cf": None, "financing_cf": None, "cash_end": None,
        "pass3_confidence": 0.95, "row_refs": {"operating_cf": "Net cash from operations"},
    }

    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_raw):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert len(results) == 1
    assert results[0]["operating_cf"] == 3_241_000  # multiplied by 1000


def test_pass3a_negative_values_preserved():
    """Negative values (already negative from LLM) must remain negative after scaling."""
    from unittest.mock import patch
    from app.services.multipass_extraction import _run_pass3a_metric_extractor
    from app.services.docling_extract import DoclingTable

    table = DoclingTable(
        page_number=2, caption="Cash Flow",
        rows=[["", "H1"], ["Investing activities", "(412)"]],
        headers=[],
    )
    labelled = {"cashflow_statement": table, "income_statement": None,
                "balance_sheet": None, "highlights": None, "unmatched": []}
    pass1 = {"report_type": "H", "period_end": "2024-12-31",
             "currency": "AUD", "scale": "thousands"}

    mock_raw = {
        "operating_cf": None, "investing_cf": -412,
        "financing_cf": None, "cash_end": None,
        "pass3_confidence": 0.9, "row_refs": {},
    }
    with patch("app.services.multipass_extraction._llm_json_call", return_value=mock_raw):
        results = _run_pass3a_metric_extractor(labelled, pass1, llm_client=None)

    assert results[0]["investing_cf"] == -412_000


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
        {"_source": "cashflow_statement", "operating_cf": 3_241_000, "investing_cf": -412_000,
         "financing_cf": None, "cash_end": None, "pass3_confidence": 0.9, "row_refs": {}},
        {"_source": "income_statement", "revenue": 27_841_000_000, "ebit": 9_100_000_000,
         "np_attributable": None, "pass3_confidence": 0.88, "row_refs": {}},
    ]
    pass3b = {"risk_summary": None, "risk_bullets": None,
              "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.0}
    pass1 = {"report_type": "H", "period_end": "2024-12-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)

    assert result["metrics"]["operating_cf"] == 3_241_000
    assert result["metrics"]["revenue"] == 27_841_000_000
    assert result["period_end"] == "2024-12-31"


def test_pass4_higher_priority_source_wins():
    """income_statement must override highlights when both provide revenue."""
    from app.services.multipass_extraction import _run_pass4_reconciler

    pass3a = [
        {"_source": "highlights", "revenue": 45_200_000, "pass3_confidence": 0.7, "row_refs": {}},
        {"_source": "income_statement", "revenue": 45_192_000, "pass3_confidence": 0.92, "row_refs": {}},
    ]
    pass3b = {"risk_summary": None, "risk_bullets": None,
              "guidance_summary": None, "material_changes": None, "confidence_narrative": 0.0}
    pass1 = {"report_type": "H", "period_end": "2024-12-31"}

    result = _run_pass4_reconciler(pass3a, pass3b, pass1)
    assert result["metrics"]["revenue"] == 45_192_000  # income_statement wins
