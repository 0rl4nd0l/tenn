#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.integrations.qual_context import QualContextReader  # noqa: E402


class _ModuleStub:
    def __init__(self, rows):
        self.rows = rows
        self.last_kwargs = None

    @staticmethod
    def ticker_blob_contains(blob, symbol):  # noqa: ANN001, ANN201
        blob_text = str(blob or "")
        token = str(symbol or "").strip().upper()
        return f"|{token}|" in blob_text

    def query_sqlite(self, **kwargs):  # noqa: ANN003, ANN201
        self.last_kwargs = dict(kwargs)
        return list(self.rows)


class CockpitNewsQualContextTests(unittest.TestCase):
    def _reader(self, db_path: Path, ticker_mode: str) -> QualContextReader:
        return QualContextReader(
            repo_root=REPO_ROOT,
            db_path=str(db_path),
            embed_backend="hash",
            embed_model="hash",
            corpus_filter="news",
            ticker_match_mode=ticker_mode,
            recall_top_k_multiplier=10,
            top_k=4,
            hash_dim=64,
            st_device="cpu",
        )

    def test_soft_mode_keeps_news_rows_with_company_news(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            db_path.touch()
            module = _ModuleStub(
                rows=[
                    (
                        0.88,
                        {
                            "company": "NEWS",
                            "corpus": "news",
                            "ticker": "",
                            "title": "ASX:BHP rises on guidance",
                            "text": "ASX:BHP rose after management upgraded FY26 guidance.",
                        },
                    ),
                    (
                        0.67,
                        {
                            "company": "NEWS",
                            "corpus": "news",
                            "ticker": "|CBA|",
                            "title": "CBA update",
                            "text": "Commonwealth Bank update.",
                        },
                    ),
                ]
            )
            reader = self._reader(db_path, ticker_mode="soft")
            reader._load_module = lambda: module  # type: ignore[method-assign]

            payload = reader.query(
                query="BHP guidance",
                company="",
                deep_mode=False,
                top_k=3,
                ticker_filter="BHP",
                source_filter="",
            )
            self.assertTrue(payload.get("ok"))
            self.assertEqual(payload.get("ticker_match_mode"), "soft")
            self.assertEqual(int(payload.get("candidate_count", 0)), 2)
            self.assertEqual(int(payload.get("filtered_count", 0)), 1)
            hits = payload.get("hits", [])
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].get("company"), "NEWS")
            self.assertIn(hits[0].get("ticker_match_rank"), {1, 2, 3})
            self.assertEqual(str(module.last_kwargs.get("ticker_filter")), "")

    def test_strict_mode_passes_ticker_filter_to_sql_query(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            db_path.touch()
            module = _ModuleStub(
                rows=[
                    (
                        0.71,
                        {
                            "company": "BHP",
                            "corpus": "news",
                            "ticker": "|BHP|",
                            "title": "BHP hits record output",
                            "text": "BHP delivered higher output in Q2.",
                        },
                    )
                ]
            )
            reader = self._reader(db_path, ticker_mode="strict")
            reader._load_module = lambda: module  # type: ignore[method-assign]

            payload = reader.query(
                query="BHP output",
                company="",
                deep_mode=False,
                top_k=2,
                ticker_filter="BHP",
                source_filter="",
            )
            self.assertTrue(payload.get("ok"))
            self.assertEqual(payload.get("ticker_match_mode"), "strict")
            self.assertEqual(str(module.last_kwargs.get("ticker_filter")), "BHP")
            self.assertEqual(int(payload.get("candidate_count", 0)), 1)
            self.assertEqual(int(payload.get("filtered_count", 0)), 1)


if __name__ == "__main__":
    unittest.main()
