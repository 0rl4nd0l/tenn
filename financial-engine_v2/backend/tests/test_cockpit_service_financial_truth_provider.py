from __future__ import annotations

from app.services.cockpit_service import _BackendFinancialTruthProvider


def test_financial_truth_provider_treats_successful_excerpt_fallback_as_warning() -> None:
    class BackendClient:
        def get_ticker_context(self, ticker: str, **kwargs):
            return {
                "ticker": ticker,
                "docs": [],
                "financials": [],
                "latest_financial_snapshot": {},
                "announcement_context": [
                    {
                        "title": "Sale of Wealth Management business",
                        "excerpt": "Perpetual announced a binding sale agreement.",
                        "context_source": "documents_pdf_excerpt",
                    }
                ],
                "extraction_failures": [],
                "low_confidence_financials": [],
                "errors": [
                    "announcement_context: relation does not exist"
                ],
                "announcement_context_fallback_used": True,
            }

    result = _BackendFinancialTruthProvider(BackendClient()).retrieve(
        query="Analyse PPT",
        entities={"primary_ticker": "PPT"},
        intent="mixed",
    )

    assert result["status"] == "ok"
    assert result["errors"] == []
    assert result["announcement_context"]
    assert result["warnings"] == [
        "announcement_context: materialized context unavailable; "
        "documents_pdf_excerpt fallback returned context"
    ]


def test_financial_truth_provider_keeps_missing_fallback_blocking_without_rows() -> None:
    class BackendClient:
        def get_ticker_context(self, ticker: str, **kwargs):
            return {
                "ticker": ticker,
                "docs": [],
                "financials": [],
                "latest_financial_snapshot": {},
                "announcement_context": [],
                "extraction_failures": [],
                "low_confidence_financials": [],
                "errors": [
                    "announcement_context: relation does not exist"
                ],
                "announcement_context_fallback_used": True,
            }

    result = _BackendFinancialTruthProvider(BackendClient()).retrieve(
        query="Analyse PPT",
        entities={"primary_ticker": "PPT"},
        intent="mixed",
    )

    assert result["status"] == "partial_error"
    assert result["errors"] == ["announcement_context: relation does not exist"]
    assert result["warnings"] == []
