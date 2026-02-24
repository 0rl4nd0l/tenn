#!/usr/bin/env python3
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.tools import ToolRouter  # noqa: E402


class _DbReaderStub:
    def __init__(self) -> None:
        self.last_error = None
        self.database_url = "sqlite:///memory"

    def get_docs(self, ticker: str, limit: int = 10):  # noqa: ARG002
        return [
            {
                "document_id": "doc-1",
                "ticker": ticker,
                "published_at": "2026-02-18 00:00:00.000000",
                "title": f"{ticker} Interim Results",
                "source_url": "https://www.asx.com.au/markets/announcements",
                "pdf_path": "",
            }
        ]

    def get_announcement_context(self, ticker: str, limit: int = 10):  # noqa: ARG002
        return []

    def get_financials(self, ticker: str, limit: int = 5):  # noqa: ARG002
        return [
            {
                "ticker": ticker,
                "period_end": "2025-12-31",
                "period_type": "HY",
                "revenue": 1000.0,
                "ebit": 220.0,
                "np_attributable": 130.0,
            }
        ]

    def get_extraction_failures(self, limit: int = 50, ticker: str | None = None):  # noqa: ARG002
        return [
            {
                "ticker": ticker or "BHP",
                "published_at": "2026-02-18",
                "title": "BHP Interim Results",
                "status": "failed",
                "error": "parse error",
                "created_at": "2026-02-18T02:00:00Z",
                "document_id": "doc-1",
            }
        ]

    def get_low_confidence_financials(  # noqa: ARG002
        self,
        threshold: float = 0.4,
        limit: int = 100,
        ticker: str | None = None,
    ):
        return [
            {
                "ticker": ticker or "BHP",
                "period_end": "2025-12-31",
                "period_type": "HY",
                "confidence_metrics": 0.21,
                "source_document_id": "doc-1",
            }
        ]


class _FileIndexerStub:
    def list_recent_reports(self, limit: int = 10):  # noqa: ARG002
        return []

    def search_text(self, pattern: str, limit: int = 20):  # noqa: ARG002
        return []


class _BackendApiStub:
    RANGE_POINTS = {"3mo": 70, "1y": 260, "3y": 780, "5y": 1260, "10y": 2520}

    def get_price(self, ticker: str, exchange: str, range_: str, interval: str, timeout: float = 12.0):  # noqa: ARG002
        points = self.RANGE_POINTS.get(range_, 260)
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        history = []
        close = 20.0
        for i in range(points):
            close += 0.03 + (0.01 if i % 7 == 0 else 0.0)
            history.append(
                {
                    "timestamp": (start + timedelta(days=i)).isoformat(),
                    "close": round(close, 4),
                }
            )
        payload = {
            "provider": "stub",
            "ticker": ticker,
            "symbol": f"{ticker}.AX",
            "currency": "AUD",
            "current": {
                "price": history[-1]["close"],
                "previous_close": history[-2]["close"],
                "market_time": history[-1]["timestamp"],
            },
            "history": history,
            "range": range_,
            "interval": interval,
        }
        return {"ok": True, "payload": payload}


class _QualReaderStub:
    def __init__(self, corpus: str, hits: int) -> None:
        self.corpus = corpus
        self.hits = hits

    def query(self, *, query: str, company: str, deep_mode: bool, top_k: int = 8):  # noqa: ARG002
        rows = []
        for idx in range(min(self.hits, top_k)):
            rows.append(
                {
                    "score": 0.9 - (idx * 0.05),
                    "company": company,
                    "corpus": self.corpus,
                    "title": f"{self.corpus}-{idx}",
                    "published_at": "2026-02-18",
                    "text": f"{self.corpus} evidence {idx}",
                }
            )
        return {"ok": True, "hits": rows}


class CockpitToolsAdditionalContextTests(unittest.TestCase):
    def _router(self, *, company_reader=None, news_reader=None) -> ToolRouter:
        return ToolRouter(
            db_reader=_DbReaderStub(),
            file_indexer=_FileIndexerStub(),
            web_fetcher=None,
            repo_root=REPO_ROOT,
            web_default_enabled=False,
            backend_api_client=_BackendApiStub(),
            qual_context_company_reader=company_reader,
            qual_context_news_reader=news_reader,
        )

    def test_deep_context_includes_data_quality_and_price_horizons(self):
        router = self._router()
        payload = router.gather_local_context("BHP", "deep analysis", deep_mode=True).payload
        self.assertIn("data_quality", payload)
        self.assertIn("price_horizons", payload)
        self.assertEqual(payload["data_quality"]["extraction_failed_count_recent"], 1)
        self.assertEqual(payload["data_quality"]["low_conf_financial_count_recent"], 1)
        self.assertEqual(set(payload["price_horizons"].keys()), {"1y", "3y", "5y", "10y"})

    def test_deep_context_merges_company_and_news_rag_with_interleave(self):
        router = self._router(company_reader=_QualReaderStub("company", 3), news_reader=_QualReaderStub("news", 2))
        payload = router.gather_local_context("BHP", "deep analysis", deep_mode=True).payload
        self.assertIn("qual_context_company", payload)
        self.assertIn("qual_context_news", payload)
        merged = payload.get("qual_context", {})
        hits = merged.get("hits", [])
        self.assertGreaterEqual(len(hits), 4)
        self.assertEqual(hits[0].get("source_corpus"), "company")
        self.assertEqual(hits[1].get("source_corpus"), "news")
        self.assertEqual(merged.get("merge_policy"), "quota_interleave")

    def test_deep_context_falls_back_to_company_only_when_news_absent(self):
        router = self._router(company_reader=_QualReaderStub("company", 3), news_reader=None)
        payload = router.gather_local_context("BHP", "deep analysis", deep_mode=True).payload
        self.assertIn("qual_context_company", payload)
        self.assertNotIn("qual_context_news", payload)
        merged = payload.get("qual_context", {})
        hits = merged.get("hits", [])
        self.assertTrue(hits)
        self.assertTrue(all(row.get("source_corpus") == "company" for row in hits if isinstance(row, dict)))


if __name__ == "__main__":
    unittest.main()
