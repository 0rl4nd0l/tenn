#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.chat import ChatController  # noqa: E402


class _ActionRegistryStub:
    def preview(self, action_id: str, args: dict):  # noqa: D401, ANN001
        raise RuntimeError("preview not used in this test")


class _ToolResult:
    def __init__(self, payload: dict, ok: bool = True) -> None:
        self.payload = payload
        self.ok = ok


class _ToolRouterStub:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.qual_context_reader = None
        self.qual_context_enabled = True

    def gather_local_context(self, ticker: str | None, query: str, deep_mode: bool = False):  # noqa: ANN001, ARG002
        payload = dict(self.payload)
        payload["ticker"] = ticker
        payload["query"] = query
        return _ToolResult(payload)

    def fetch_web(self, url: str, enabled: bool, max_chars: int | None = None):  # noqa: ANN001, ARG002
        return _ToolResult({"url": url, "error": "web unavailable in unit test"}, ok=False)

    def web_enrich(
        self,
        query: str,
        enabled: bool,
        max_results: int = 4,  # noqa: ARG002
        max_chars_per_page: int = 3500,  # noqa: ARG002
        preferred_domains: list[str] | None = None,  # noqa: ARG002
        strict_official: bool = False,  # noqa: ARG002
    ):
        return _ToolResult({"query": query, "pages": [], "error": "web unavailable in unit test"}, ok=False)


class _OllamaFrameworkStub:
    def chat(self, prompt: str, timeout: float = 120.0, on_chunk=None) -> str:  # noqa: ANN001, ARG002
        return (
            "To conduct a deep analysis of MGR, we need to carefully examine the data. "
            "Here’s a structured approach:\n"
            "### 1. Liquidity Pressure\n"
            "### 2. Cash Runway\n"
            "### 3. Refinancing Risk\n"
        )


class _OllamaMissingHeadersStub:
    def chat(self, prompt: str, timeout: float = 120.0, on_chunk=None) -> str:  # noqa: ANN001, ARG002
        return (
            "MGR has moderate refinancing pressure.\n"
            "- 2026-02-18: MGR 1H26 Property Compendium indicates active debt management.\n"
            "- score 0.651 | 2026-02-18 | MGR liquidity update presentation.\n"
            "- 2025-12-31: funding posture remains under review.\n"
            "- score 0.612 | 2025-08-20 | capital resources excerpt.\n"
        )


class CockpitDeepAnalysisGroundingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = ChatController(
            ollama_client=None,
            tool_router=None,
            action_registry=_ActionRegistryStub(),
        )
        self.local_payload = {
            "ticker": "MGR",
            "docs": [
                {
                    "published_at": "2026-02-18 00:00:00.000000",
                    "title": "MGR 1H26 Property Compendium",
                    "document_id": "doc-1",
                }
            ],
            "qual_context": {
                "ok": True,
                "hits": [
                    {
                        "score": 0.651,
                        "title": "MGR liquidity update presentation",
                        "published_at": "2026-02-18",
                        "text": "Liquidity and capital resources remain a priority with refinancing actions in progress.",
                    }
                ],
            },
            "price": {},
            "price_state": {"ok": False, "error": "price unavailable"},
            "financials": [],
        }

    def test_framework_only_answer_is_detected(self):
        answer = (
            "To conduct a deep analysis of MGR, we need to carefully examine the data. "
            "Here’s a structured approach:\n"
            "### 1. Liquidity Pressure\n"
            "### 2. Cash Runway\n"
            "### 3. Refinancing Risk\n"
        )
        self.assertTrue(
            self.controller._looks_like_framework_only_analysis(  # noqa: SLF001
                answer=answer,
                ticker="MGR",
                local_payload=self.local_payload,
            )
        )

    def test_grounded_answer_with_anchors_is_not_flagged(self):
        answer = (
            "Verdict: MGR has moderate refinancing pressure.\n"
            "Evidence:\n"
            "- 2026-02-18: MGR 1H26 Property Compendium indicates active debt management.\n"
            "- qual score 0.651 from MGR liquidity update presentation flags liquidity focus.\n"
        )
        self.assertFalse(
            self.controller._looks_like_framework_only_analysis(  # noqa: SLF001
                answer=answer,
                ticker="MGR",
                local_payload=self.local_payload,
            )
        )

    def test_grounded_deep_brief_contains_evidence_sections(self):
        text = self.controller._build_grounded_deep_analysis_brief(  # noqa: SLF001
            ticker="MGR",
            message="deep analysis analyse MGR with focus on liquidity pressure",
            local_payload=self.local_payload,
        )
        self.assertIn("Verdict:", text)
        self.assertIn("Evidence:", text)
        self.assertIn("Risks:", text)
        self.assertIn("Counterpoints:", text)
        self.assertIn("Unknowns:", text)
        self.assertIn("[source:", text.lower())
        self.assertFalse(self.controller._violates_deep_output_contract(text))  # noqa: SLF001

    def test_deep_output_contract_detects_missing_headers(self):
        text = (
            "MGR has refinancing pressure.\n"
            "Evidence bullets:\n"
            "- 2026-02-18: filing anchor\n"
            "- score 0.651 | semantic anchor\n"
            "- 2025-12-31: debt maturity note\n"
            "- score 0.590 | covenant discussion\n"
        )
        self.assertTrue(self.controller._violates_deep_output_contract(text))  # noqa: SLF001

    def test_deep_output_contract_requires_source_anchors(self):
        text = (
            "Verdict:\n"
            "MGR has moderate refinancing pressure.\n\n"
            "Evidence:\n"
            "- 2026-02-18 (score 0.651): debt management commentary.\n"
            "- 2026-02-18 (score 0.642): liquidity commentary.\n"
            "- 2026-02-18 (score 0.633): capital resources commentary.\n"
            "- 2026-02-18 (score 0.621): maturity profile commentary.\n\n"
            "Risks:\n"
            "- refinancing concentration risk.\n\n"
            "Counterpoints:\n"
            "- diversified portfolio and access to capital.\n\n"
            "Unknowns:\n"
            "- debt ladder detail not explicitly disclosed.\n"
        )
        self.assertTrue(self.controller._violates_deep_output_contract(text))  # noqa: SLF001

    def test_grounded_deep_brief_dedupes_qual_hits_and_cleans_paths(self):
        payload = {
            "ticker": "MGR",
            "docs": [],
            "qual_context": {
                "ok": True,
                "hits": [
                    {
                        "score": 0.621,
                        "published_at": "2026-02-18",
                        "file": "/home/l4nd0/tenn/financial-engine_v2/data/marketindex/pdfs/18-02-26_742am_MGR_mgr-1h26-results-presentation_2A1654097.pdf",
                        "text": "liquidity and refinancing context",
                    },
                    {
                        "score": 0.619,
                        "published_at": "2026-02-18",
                        "file": "/home/l4nd0/tenn/financial-engine_v2/data/marketindex/pdfs/18-02-26_742am_MGR_mgr-1h26-results-presentation_2A1654097.pdf",
                        "text": "duplicate of same source",
                    },
                    {
                        "score": 0.611,
                        "published_at": "2026-02-18",
                        "file": "/home/l4nd0/tenn/financial-engine_v2/data/marketindex/pdfs/18-02-26_737am_MGR_mgr-1h26-interim-report_2A1654094.pdf",
                        "text": "second unique source",
                    },
                ],
            },
            "price": {},
            "price_state": {"ok": False, "error": "price unavailable"},
            "financials": [],
        }
        text = self.controller._build_grounded_deep_analysis_brief(  # noqa: SLF001
            ticker="MGR",
            message="deep analysis analyse MGR with focus on liquidity pressure",
            local_payload=payload,
        )
        score_lines = [line for line in text.splitlines() if line.strip().startswith("- score ")]
        self.assertEqual(len(score_lines), 2)
        for line in score_lines:
            self.assertNotIn("/home/l4nd0", line)
            self.assertIn("[source:", line.lower())

    def test_build_chat_response_replaces_framework_only_output(self):
        controller = ChatController(
            ollama_client=_OllamaFrameworkStub(),
            tool_router=_ToolRouterStub(self.local_payload),
            action_registry=_ActionRegistryStub(),
        )
        response = controller.build_chat_response(
            "deep analysis analyse MGR with focus on liquidity pressure",
            enable_web=True,
            analysis_mode="deep",
        )
        self.assertIn("Verdict:", response.text)
        self.assertIn("Evidence:", response.text)
        self.assertNotIn("structured approach", response.text.lower())

    def test_build_chat_response_replaces_missing_header_output(self):
        controller = ChatController(
            ollama_client=_OllamaMissingHeadersStub(),
            tool_router=_ToolRouterStub(self.local_payload),
            action_registry=_ActionRegistryStub(),
        )
        response = controller.build_chat_response(
            "deep analysis analyse MGR with focus on liquidity pressure",
            enable_web=True,
            analysis_mode="deep",
        )
        self.assertIn("Verdict:", response.text)
        self.assertIn("Evidence:", response.text)
        self.assertIn("Unknowns:", response.text)
        self.assertNotIn("structured approach", response.text.lower())

    def test_grounded_deep_brief_includes_claim_level_liquidity_signal(self):
        payload = {
            "ticker": "MGR",
            "docs": [],
            "doc_snippets": [
                {
                    "title": "MGR 1H26 Interim Report",
                    "published_at": "2026-02-18 00:00:00.000000",
                    "excerpt": (
                        "Key outcomes included over $1bn of cash and undrawn debt facilities as at 31 December 2025, "
                        "with no debt due for repayment over the next 12 months."
                    ),
                }
            ],
            "qual_context": {
                "ok": True,
                "hits": [],
            },
            "price": {},
            "price_state": {"ok": False, "error": "price unavailable"},
            "financials": [],
        }
        text = self.controller._build_grounded_deep_analysis_brief(  # noqa: SLF001
            ticker="MGR",
            message="deep analysis analyse MGR with focus on liquidity pressure",
            local_payload=payload,
        )
        self.assertIn("undrawn debt facilities", text.lower())
        self.assertIn("[source:", text.lower())
        self.assertIn("Signal extraction identified concrete liquidity/refinancing snippets", text)

    def test_grounded_deep_brief_includes_data_quality_evidence(self):
        payload = {
            "ticker": "MGR",
            "docs": [],
            "qual_context": {"ok": True, "hits": []},
            "data_quality": {
                "extraction_failed_count_recent": 1,
                "low_conf_financial_count_recent": 1,
                "confidence_threshold": 0.4,
                "recent_failures": [
                    {
                        "published_at": "2026-02-18",
                        "title": "MGR 1H26 Interim Report",
                        "error": "table parse failed",
                        "document_id": "doc-xyz",
                    }
                ],
                "recent_low_conf_rows": [
                    {
                        "ticker": "MGR",
                        "period_end": "2025-12-31",
                        "period_type": "HY",
                        "confidence_metrics": 0.22,
                    }
                ],
            },
            "price": {},
            "price_state": {"ok": False, "error": "price unavailable"},
            "financials": [],
        }
        text = self.controller._build_grounded_deep_analysis_brief(  # noqa: SLF001
            ticker="MGR",
            message="deep analysis analyse MGR",
            local_payload=payload,
        )
        self.assertIn("Extraction failed for MGR 1H26 Interim Report", text)
        self.assertIn("[source: extraction_runs/documents]", text)
        self.assertIn("[source: asx_periodic_financials]", text)

    def test_grounded_deep_brief_includes_price_horizon_evidence(self):
        payload = {
            "ticker": "MGR",
            "docs": [],
            "qual_context": {"ok": True, "hits": []},
            "price": {},
            "price_state": {"ok": False, "error": "price unavailable"},
            "price_horizons": {
                "1y": {
                    "ok": True,
                    "total_return_pct": 12.5,
                    "max_drawdown_pct": -8.2,
                    "volatility_ann_pct": 21.4,
                    "history_points": 252,
                }
            },
            "financials": [],
        }
        text = self.controller._build_grounded_deep_analysis_brief(  # noqa: SLF001
            ticker="MGR",
            message="deep analysis analyse MGR",
            local_payload=payload,
        )
        self.assertIn("[source: price_horizon_1y]", text)
        self.assertIn("total_return=12.50%", text)

    def test_grounded_deep_brief_includes_web_fact_evidence(self):
        payload = {
            "ticker": "MGR",
            "docs": [],
            "qual_context": {"ok": True, "hits": []},
            "web_facts": [
                {
                    "url": "https://www.asx.com.au/example",
                    "claim": "On 2026-02-20 the company announced a A$500m refinancing facility.",
                    "numbers": ["A$500m"],
                    "dates": ["2026-02-20"],
                }
            ],
            "price": {},
            "price_state": {"ok": False, "error": "price unavailable"},
            "financials": [],
        }
        text = self.controller._build_grounded_deep_analysis_brief(  # noqa: SLF001
            ticker="MGR",
            message="deep analysis analyse MGR",
            local_payload=payload,
        )
        self.assertIn("Web fact:", text)
        self.assertIn("[source: https://www.asx.com.au/example]", text)


if __name__ == "__main__":
    unittest.main()
