"""Tests for backend research synthesis service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.research_synthesis import (
    _empty_brief,
    _parse_synthesis,
    synthesize_research,
)


class TestParseSynthesis:
    def test_valid_json(self):
        raw = '{"summary": "BHP is strong", "key_metrics": {}, "sentiment": "bullish", "confidence": 0.8, "recent_developments": [], "risks": [], "catalysts": [], "data_gaps": []}'
        result = _parse_synthesis(raw)
        assert result["summary"] == "BHP is strong"
        assert result["sentiment"] == "bullish"
        assert result["confidence"] == 0.8

    def test_json_with_markdown_fences(self):
        raw = '```json\n{"summary": "test", "key_metrics": {}}\n```'
        result = _parse_synthesis(raw)
        assert result["summary"] == "test"

    def test_malformed_json_falls_back_to_text(self):
        raw = "This is not valid JSON at all"
        result = _parse_synthesis(raw)
        assert result["summary"] == raw[:500]
        assert result["confidence"] == 0.3
        assert "non-JSON response" in result["data_gaps"][0]

    def test_empty_string(self):
        result = _parse_synthesis("")
        assert result["summary"] == ""
        assert result["confidence"] == 0.3


class TestEmptyBrief:
    def test_default_reason(self):
        result = _empty_brief("BHP")
        assert "BHP" in result["summary"]
        assert result["confidence"] == 0.0

    def test_custom_reason(self):
        result = _empty_brief("CSL", reason="Backend offline")
        assert "Backend offline" in result["summary"]
        assert "Backend offline" in result["risks"]


class TestSynthesizeResearch:
    def test_empty_sources_returns_empty_brief(self):
        result = synthesize_research("BHP", {})
        assert "No data gathered" in result["summary"]
        assert result["confidence"] == 0.0

    @patch("app.services.research_synthesis._call_llm")
    def test_happy_path(self, mock_llm):
        mock_llm.return_value = '{"summary": "BHP revenue up 12%", "key_metrics": {"revenue": "$50B"}, "sentiment": "bullish", "confidence": 0.8, "recent_developments": ["iron ore prices up"], "risks": ["China slowdown"], "catalysts": ["dividend"], "data_gaps": []}'
        result = synthesize_research("BHP", {"financials": [{"revenue": 50000}]})
        assert result["summary"] == "BHP revenue up 12%"
        assert result["sentiment"] == "bullish"
        mock_llm.assert_called_once()

    @patch("app.services.research_synthesis._call_llm")
    def test_llm_failure_returns_fallback(self, mock_llm):
        mock_llm.side_effect = RuntimeError("llama.cpp connection refused")
        result = synthesize_research("BHP", {"financials": [{}]})
        assert "LLM synthesis failed" in result["summary"]
        assert result["confidence"] == 0.0
        assert "Synthesis failed" in result["data_gaps"][0] or "LLM synthesis failed" in result["summary"]
