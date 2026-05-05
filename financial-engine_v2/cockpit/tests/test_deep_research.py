"""Tests for DeepResearchRunner (cockpit-side, mocked backend)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cockpit.core.research.deep_research import DeepResearchRunner


def _make_runner(*, backend_result=None, backend_error=None, backend_api_result=None):
    """Build a DeepResearchRunner with mocked dependencies."""
    mock_router = MagicMock()
    mock_backend_api = MagicMock()
    if backend_api_result:
        mock_backend_api.get_ticker_context.return_value = backend_api_result
    else:
        mock_backend_api.get_ticker_context.return_value = {
            "financials": [{"revenue": 50000}],
            "docs": [],
            "announcement_context": [],
        }
    mock_router.backend_api_client = mock_backend_api
    mock_router.get_price_context_for_window.return_value = {"price": {"close": 45.0}}

    mock_backend = MagicMock()
    if backend_error:
        mock_backend.synthesize_research.side_effect = backend_error
    else:
        mock_backend.synthesize_research.return_value = backend_result or {
            "summary": "BHP is strong",
            "key_metrics": {"revenue": "$50B"},
            "sentiment": "bullish",
            "confidence": 0.85,
            "recent_developments": [],
            "risks": [],
            "catalysts": [],
            "data_gaps": [],
        }

    mock_dossier = MagicMock()
    mock_dossier.recall.return_value = {"findings": []}

    runner = DeepResearchRunner(
        tool_router=mock_router,
        backend_client=mock_backend,
        dossier_service=mock_dossier,
    )
    return runner, mock_backend, mock_dossier


class TestDeepResearchRunner:
    def test_happy_path_returns_structured_result(self):
        runner, mock_backend, _ = _make_runner()
        result = runner.run("BHP")
        assert result["ok"] is True
        assert result["ticker"] == "BHP"
        assert result["research"]["summary"] == "BHP is strong"
        assert "financials" in result["sources_used"]
        mock_backend.synthesize_research.assert_called_once()

    def test_backend_failure_returns_graceful_fallback(self):
        runner, _, _ = _make_runner(backend_error=RuntimeError("Backend unreachable"))
        result = runner.run("BHP")
        assert result["ok"] is False
        assert "Backend synthesis call failed" in result["error"]
        assert "LLM synthesis failed" in result["research"]["summary"]
        assert result["research"]["confidence"] == 0.0

    def test_empty_ticker_returns_error(self):
        runner, _, _ = _make_runner()
        result = runner.run("")
        assert result["ok"] is False
        assert "ticker is required" in result["error"]

    def test_backend_none_returns_fallback(self):
        """DeepResearchRunner with no backend client degrades gracefully."""
        mock_router = MagicMock()
        mock_router.backend_api_client = None  # Force error path
        mock_router.get_price_context_for_window.return_value = {}

        runner = DeepResearchRunner(
            tool_router=mock_router,
            backend_client=None,
        )
        result = runner.run("CSL")
        assert result["ok"] is True
        assert "No data available" in result["research"]["summary"]

    def test_dossier_auto_save_on_success(self):
        runner, _, mock_dossier = _make_runner()
        runner.run("BHP")
        mock_dossier.save.assert_called_once()
        call_args = mock_dossier.save.call_args
        assert call_args[0][0] == "BHP"  # ticker
        assert call_args[0][1] == "BHP is strong"  # summary

    def test_dossier_not_saved_on_synthesis_failure(self):
        runner, _, mock_dossier = _make_runner(backend_error=RuntimeError("fail"))
        runner.run("BHP")
        mock_dossier.save.assert_not_called()

    def test_no_hybrid_router_reference(self):
        """Confirm HybridRouter is not referenced anywhere in DeepResearchRunner."""
        import inspect

        source = inspect.getsource(DeepResearchRunner)
        assert "hybrid_router" not in source.lower()
        assert "HybridRouter" not in source

    def test_commentary_query_uses_supported_rag_source(self):
        runner, mock_backend, _ = _make_runner()
        mock_backend.rag_query.return_value = {
            "results": [
                {
                    "payload": {
                        "text": "Management reiterated guidance and margin expansion.",
                        "source": "filing",
                    }
                }
            ]
        }

        result = runner.run("BHP")

        mock_backend.rag_query.assert_called_once()
        assert mock_backend.rag_query.call_args.kwargs["source"] == "asx_docs"
        assert "commentary" in result["sources_used"]
