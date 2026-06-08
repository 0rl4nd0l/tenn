#!/usr/bin/env python3
import os
import sqlite3
import sys
import tempfile
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

    def get_ticker_context(  # noqa: ARG002
        self,
        ticker: str,
        docs_limit: int = 10,
        financials_limit: int = 5,
        announcements_limit: int = 10,
        failures_limit: int = 8,
        low_confidence_threshold: float = 0.4,
        low_confidence_limit: int = 8,
    ):
        return {
            "docs": [
                {
                    "document_id": "doc-1",
                    "ticker": ticker,
                    "published_at": "2026-02-18 00:00:00.000000",
                    "title": f"{ticker} Interim Results",
                    "source_url": "https://www.asx.com.au/markets/announcements",
                    "pdf_path": "",
                }
            ],
            "announcement_context": [],
            "financials": [
                {
                    "ticker": ticker,
                    "period_end": "2025-12-31",
                    "period_type": "HY",
                    "revenue": 1000.0,
                    "ebit": 220.0,
                    "np_attributable": 130.0,
                }
            ],
            "extraction_failures": [
                {
                    "ticker": ticker,
                    "published_at": "2026-02-18",
                    "title": f"{ticker} Interim Results",
                    "status": "failed",
                    "error": "parse error",
                    "created_at": "2026-02-18T02:00:00Z",
                    "document_id": "doc-1",
                }
            ],
            "low_confidence_financials": [
                {
                    "ticker": ticker,
                    "period_end": "2025-12-31",
                    "period_type": "HY",
                    "confidence_metrics": 0.21,
                    "source_document_id": "doc-1",
                }
            ],
            "errors": [],
        }

    def get_price(
        self,
        ticker: str,
        exchange: str,
        range_: str,
        interval: str,
        timeout: float = 12.0,
    ):  # noqa: ARG002
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

    def query(  # noqa: ARG002
        self,
        *,
        query: str,
        company: str,
        deep_mode: bool,
        top_k: int = 8,
        ticker_filter: str = "",
        source_filter: str = "",
        **kwargs,
    ):
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
        return {
            "ok": True,
            "hits": rows,
            "candidate_count": len(rows),
            "filtered_count": len(rows),
            "ticker_match_mode": "soft" if self.corpus == "news" else "strict",
        }


class CockpitToolsAdditionalContextTests(unittest.TestCase):
    def _router(
        self,
        *,
        company_reader=None,
        news_reader=None,
        news_context_db_path: Path | None = None,
        news_context_corpus_filter: str = "news",
    ) -> ToolRouter:
        return ToolRouter(
            db_reader=_DbReaderStub(),
            file_indexer=_FileIndexerStub(),
            web_fetcher=None,
            repo_root=REPO_ROOT,
            web_default_enabled=False,
            backend_api_client=_BackendApiStub(),
            qual_context_company_reader=company_reader,
            qual_context_news_reader=news_reader,
            news_context_db_path=str(news_context_db_path or ""),
            news_context_corpus_filter=news_context_corpus_filter,
        )

    def test_deep_context_includes_data_quality_and_price_horizons(self):
        router = self._router()
        payload = router.gather_local_context(
            "BHP", "deep analysis", deep_mode=True
        ).payload
        self.assertIn("data_quality", payload)
        self.assertIn("price_horizons", payload)
        self.assertEqual(payload["data_quality"]["extraction_failed_count_recent"], 1)
        self.assertEqual(payload["data_quality"]["low_conf_financial_count_recent"], 1)
        self.assertEqual(
            set(payload["price_horizons"].keys()), {"1y", "3y", "5y", "10y"}
        )

    def test_deep_context_merges_company_and_news_rag_with_interleave(self):
        router = self._router(
            company_reader=_QualReaderStub("company", 3),
            news_reader=_QualReaderStub("news", 2),
        )
        payload = router.gather_local_context(
            "BHP", "deep analysis", deep_mode=True
        ).payload
        self.assertIn("qual_context_company", payload)
        self.assertIn("qual_context_news", payload)
        self.assertEqual(payload["qual_context_news"].get("ticker_match_mode"), "soft")
        self.assertEqual(payload["qual_context_news"].get("candidate_count"), 2)
        merged = payload.get("qual_context", {})
        hits = merged.get("hits", [])
        self.assertGreaterEqual(len(hits), 4)
        self.assertEqual(hits[0].get("source_corpus"), "company")
        self.assertEqual(hits[1].get("source_corpus"), "news")
        self.assertEqual(merged.get("merge_policy"), "quota_interleave")

    def test_generic_ticker_overview_skips_news_context(self):
        router = self._router(
            company_reader=_QualReaderStub("company", 2),
            news_reader=_QualReaderStub("news", 2),
        )
        payload = router.gather_local_context(
            "BHP", "tell me about BHP", deep_mode=False
        ).payload
        self.assertIn("qual_context_company", payload)
        self.assertNotIn("qual_context_news", payload)
        merged = payload.get("qual_context", {})
        hits = merged.get("hits", [])
        self.assertTrue(
            all(
                row.get("source_corpus") != "news"
                for row in hits
                if isinstance(row, dict)
            )
        )

    def test_news_queries_still_include_news_context(self):
        router = self._router(
            company_reader=_QualReaderStub("company", 2),
            news_reader=_QualReaderStub("news", 2),
        )
        payload = router.gather_local_context(
            "BHP", "latest BHP news", deep_mode=False
        ).payload
        self.assertIn("qual_context_news", payload)
        merged = payload.get("qual_context", {})
        hits = merged.get("hits", [])
        self.assertTrue(
            any(
                row.get("source_corpus") == "news"
                for row in hits
                if isinstance(row, dict)
            )
        )

    def test_deep_context_falls_back_to_company_only_when_news_absent(self):
        router = self._router(
            company_reader=_QualReaderStub("company", 3), news_reader=None
        )
        payload = router.gather_local_context(
            "BHP", "deep analysis", deep_mode=True
        ).payload
        self.assertIn("qual_context_company", payload)
        if "qual_context_news" in payload:
            self.assertIsInstance(payload["qual_context_news"].get("hits"), list)
        merged = payload.get("qual_context", {})
        hits = merged.get("hits", [])
        self.assertTrue(hits)
        self.assertTrue(
            any(
                row.get("source_corpus") == "company"
                for row in hits
                if isinstance(row, dict)
            )
        )

    def test_news_sqlite_fallback_populates_news_hits_when_reader_absent(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE context_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        corpus TEXT NOT NULL,
                        title TEXT NOT NULL,
                        text TEXT NOT NULL,
                        source TEXT NOT NULL,
                        url TEXT NOT NULL,
                        published_at TEXT NOT NULL,
                        doc_date TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        company TEXT NOT NULL
                    )
                    """
                )
                conn.executemany(
                    """
                    INSERT INTO context_chunks(
                        chunk_id, corpus, title, text, source, url, published_at, doc_date, ticker, company
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            "news_eodhd:art_bhp_1:0",
                            "news_eodhd",
                            "BHP production update",
                            "BHP production and guidance update for FY26.",
                            "eodhd",
                            "https://example.com/bhp-1",
                            "2026-03-02T05:00:00Z",
                            "2026-03-02",
                            "|BHP|",
                            "BHP",
                        ),
                        (
                            "news_eodhd:art_bhp_1:1",
                            "news_eodhd",
                            "BHP production update",
                            "Second chunk duplicate for same article should dedupe.",
                            "eodhd",
                            "https://example.com/bhp-1",
                            "2026-03-02T05:00:00Z",
                            "2026-03-02",
                            "|BHP|",
                            "BHP",
                        ),
                        (
                            "news_newspaper4k:art_bhp_2:0:abcd1234",
                            "news_newspaper4k",
                            "BHP market reaction",
                            "Analysts react to BHP update across ASX.",
                            "stockhead.com.au",
                            "https://example.com/bhp-2",
                            "2026-03-01T11:00:00Z",
                            "2026-03-01",
                            "|BHP|",
                            "BHP",
                        ),
                        (
                            "news_newspaper4k:art_cba_1:0:efgh5678",
                            "news_newspaper4k",
                            "CBA lending outlook",
                            "CBA outlook article should not appear for BHP query.",
                            "afr.com",
                            "https://example.com/cba-1",
                            "2026-03-01T11:00:00Z",
                            "2026-03-01",
                            "|CBA|",
                            "CBA",
                        ),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

            router = self._router(
                company_reader=None,
                news_reader=None,
                news_context_db_path=db_path,
                news_context_corpus_filter="news",
            )
            payload = router.gather_local_context(
                "BHP", "guidance update", deep_mode=False
            ).payload
            news_payload = payload.get("qual_context_news", {})
            self.assertTrue(news_payload.get("ok"))
            self.assertEqual(news_payload.get("source"), "news_sqlite_context")
            hits = news_payload.get("hits", [])
            self.assertEqual(len(hits), 2)
            self.assertTrue(
                all(
                    "BHP" in str(row.get("ticker", "")) or row.get("company") == "BHP"
                    for row in hits
                )
            )
            merged = payload.get("qual_context", {})
            merged_hits = merged.get("hits", [])
            self.assertTrue(merged_hits)
            self.assertTrue(
                any(
                    row.get("source_corpus", "").startswith("news")
                    for row in merged_hits
                    if isinstance(row, dict)
                )
            )

    def test_get_news_context_uses_sqlite_path_fallback_when_reader_absent(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE context_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        corpus TEXT NOT NULL,
                        title TEXT NOT NULL,
                        text TEXT NOT NULL,
                        source TEXT NOT NULL,
                        url TEXT NOT NULL,
                        published_at TEXT NOT NULL,
                        doc_date TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        company TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO context_chunks(
                        chunk_id, corpus, title, text, source, url, published_at, doc_date, ticker, company
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "news_newspaper4k:art_bhp_direct:0",
                        "news_newspaper4k",
                        "BHP guidance update",
                        "BHP issued an updated production and guidance outlook.",
                        "afr.com",
                        "https://example.com/bhp-direct",
                        "2026-03-04T01:00:00Z",
                        "2026-03-04",
                        "|BHP|",
                        "BHP",
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            router = self._router(
                company_reader=None,
                news_reader=None,
                news_context_db_path=db_path,
                news_context_corpus_filter="news",
            )
            payload = router.get_news_context(
                "latest BHP guidance update", top_k=3, ticker="BHP"
            )

            self.assertTrue(payload.get("ok"))
            self.assertEqual(payload.get("_source"), "sqlite_fallback")
            hits = payload.get("hits", [])
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].get("title"), "BHP guidance update")

    def test_get_news_context_sqlite_path_fallback_honors_date_bounds(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE context_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        corpus TEXT NOT NULL,
                        title TEXT NOT NULL,
                        text TEXT NOT NULL,
                        source TEXT NOT NULL,
                        url TEXT NOT NULL,
                        published_at TEXT NOT NULL,
                        doc_date TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        company TEXT NOT NULL
                    )
                    """
                )
                conn.executemany(
                    """
                    INSERT INTO context_chunks(
                        chunk_id, corpus, title, text, source, url, published_at, doc_date, ticker, company
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            "news_newspaper4k:art_bhp_old:0",
                            "news_newspaper4k",
                            "BHP January update",
                            "Older BHP news outside the requested window.",
                            "afr.com",
                            "https://example.com/bhp-old",
                            "2026-01-15T01:00:00Z",
                            "2026-01-15",
                            "|BHP|",
                            "BHP",
                        ),
                        (
                            "news_newspaper4k:art_bhp_march:0",
                            "news_newspaper4k",
                            "BHP March guidance update",
                            "BHP guidance update inside the requested window.",
                            "afr.com",
                            "https://example.com/bhp-march",
                            "2026-03-04T01:00:00Z",
                            "2026-03-04",
                            "|BHP|",
                            "BHP",
                        ),
                        (
                            "news_newspaper4k:art_bhp_april:0",
                            "news_newspaper4k",
                            "BHP April update",
                            "Future BHP news outside the requested window.",
                            "afr.com",
                            "https://example.com/bhp-april",
                            "2026-04-02T01:00:00Z",
                            "2026-04-02",
                            "|BHP|",
                            "BHP",
                        ),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

            router = self._router(
                company_reader=None,
                news_reader=None,
                news_context_db_path=db_path,
                news_context_corpus_filter="news",
            )
            payload = router.get_news_context(
                "BHP guidance",
                top_k=5,
                ticker="BHP",
                date_from="2026-03-01",
                date_to="2026-03-31",
            )

            self.assertTrue(payload.get("ok"))
            hits = payload.get("hits", [])
            self.assertEqual([hit.get("title") for hit in hits], ["BHP March guidance update"])

    def test_news_sqlite_fallback_ranks_primary_company_above_broad_sector_mention(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE context_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        corpus TEXT NOT NULL,
                        title TEXT NOT NULL,
                        text TEXT NOT NULL,
                        source TEXT NOT NULL,
                        url TEXT NOT NULL,
                        published_at TEXT NOT NULL,
                        doc_date TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        company TEXT NOT NULL,
                        ticker_relevance_json TEXT NOT NULL
                    )
                    """
                )
                conn.executemany(
                    """
                    INSERT INTO context_chunks(
                        chunk_id, corpus, title, text, source, url, published_at, doc_date, ticker, company, ticker_relevance_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            "news_newspaper4k:art_sector_1:0:abcd1234",
                            "news_newspaper4k",
                            "How I Invest and Trade ASX Mining Shares",
                            "A broad mining overview mentions BHP alongside RIO and NST in the sector basket.",
                            "stockhead.com.au",
                            "https://example.com/sector-1",
                            "2026-03-03T10:00:00Z",
                            "2026-03-03",
                            "|BHP|RIO|NST|",
                            "RIO",
                            '{"BHP":{"confidence":0.45,"label":"sector_context","primary":false,"score":0.22}}',
                        ),
                        (
                            "news_eodhd:art_bhp_1:0",
                            "news_eodhd",
                            "ASX:BHP lifts guidance after strong quarter",
                            "BHP lifted guidance after stronger production and maintained output expectations.",
                            "eodhd",
                            "https://example.com/bhp-1",
                            "2026-03-01T09:00:00Z",
                            "2026-03-01",
                            "|BHP|",
                            "BHP",
                            '{"BHP":{"confidence":0.99,"label":"primary_company","primary":true,"score":0.93}}',
                        ),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

            router = self._router(
                company_reader=None,
                news_reader=None,
                news_context_db_path=db_path,
                news_context_corpus_filter="news",
            )
            payload = router.gather_local_context(
                "BHP", "guidance", deep_mode=False
            ).payload
            news_payload = payload.get("qual_context_news", {})
            self.assertTrue(news_payload.get("ok"))
            hits = news_payload.get("hits", [])
            self.assertEqual(len(hits), 2)
            self.assertEqual(
                hits[0].get("title"), "ASX:BHP lifts guidance after strong quarter"
            )
            self.assertGreater(
                float(hits[0].get("final_score") or 0.0),
                float(hits[1].get("final_score") or 0.0),
            )
            self.assertEqual(hits[0].get("ticker_relation_type"), "primary_company")
            self.assertEqual(hits[1].get("ticker_relation_type"), "sector_context")


if __name__ == "__main__":
    unittest.main()
