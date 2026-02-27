#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.integrations.qual_context import QualContextReader, compute_news_weighted_score  # noqa: E402


class _ModuleStub:
    def __init__(self, rows):
        self.rows = list(rows)

    @staticmethod
    def ticker_blob_contains(blob, symbol):  # noqa: ANN001, ANN201
        blob_text = str(blob or "")
        token = str(symbol or "").strip().upper()
        return f"|{token}|" in blob_text

    def query_sqlite(self, **kwargs):  # noqa: ANN003, ANN201
        return list(self.rows)


class NewsWeightedRankingTests(unittest.TestCase):
    def _reader(self, db_path: Path) -> QualContextReader:
        return QualContextReader(
            repo_root=REPO_ROOT,
            db_path=str(db_path),
            embed_backend="hash",
            embed_model="hash",
            corpus_filter="news",
            ticker_match_mode="soft",
            recall_top_k_multiplier=10,
            top_k=4,
            hash_dim=64,
            st_device="cpu",
        )

    def test_recency_prioritization(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            db_path.touch()
            module = _ModuleStub(
                rows=[
                    (
                        0.79,
                        {
                            "company": "NEWS",
                            "corpus": "news",
                            "ticker": "",
                            "title": "ASX:BHP outlook unchanged",
                            "text": "ASX:BHP maintained outlook.",
                            "published_at": "2026-02-18T12:00:00Z",
                        },
                    ),
                    (
                        0.75,
                        {
                            "company": "NEWS",
                            "corpus": "news",
                            "ticker": "",
                            "title": "ASX:BHP production update",
                            "text": "ASX:BHP provided a fresh production update.",
                            "published_at": "2026-02-25T11:00:00Z",
                        },
                    ),
                ]
            )
            reader = self._reader(db_path=db_path)
            reader._load_module = lambda: module  # type: ignore[method-assign]
            reader.news_weighting_config = {
                "enable_signal_weighting": True,
                "recency_half_life_hours": 24.0,
                "recency_max_boost": 0.35,
                "ticker_match_boosts": {"exact": 0.0, "strong": 0.0, "weak": 0.0},
                "au_domain_boost": 0.0,
                "title_keyword_boost": 0.0,
                "title_keywords": [],
                "now_utc": "2026-02-25T12:00:00Z",
            }

            payload = reader.query(
                query="BHP update",
                company="",
                deep_mode=False,
                top_k=2,
                ticker_filter="BHP",
                source_filter="",
            )
            self.assertTrue(payload.get("ok"))
            hits = payload.get("hits", [])
            self.assertEqual(len(hits), 2)
            self.assertEqual(hits[0].get("published_at"), "2026-02-25T11:00:00Z")
            self.assertGreater(float(hits[0].get("final_score", 0.0)), float(hits[1].get("final_score", 0.0)))

    def test_ticker_exact_boost(self):
        cfg = {
            "enable_signal_weighting": True,
            "recency_max_boost": 0.0,
            "ticker_match_boosts": {"exact": 0.25, "strong": 0.10, "weak": 0.03},
            "au_domain_boost": 0.0,
            "title_keyword_boost": 0.0,
            "title_keywords": [],
            "now_utc": "2026-02-25T12:00:00Z",
        }
        exact = compute_news_weighted_score(0.6, "2026-02-25T10:00:00Z", "exact", "", "", cfg)
        weak = compute_news_weighted_score(0.6, "2026-02-25T10:00:00Z", "weak", "", "", cfg)
        self.assertGreater(exact, weak)

    def test_domain_boost(self):
        cfg = {
            "enable_signal_weighting": True,
            "recency_max_boost": 0.0,
            "ticker_match_boosts": {"exact": 0.0, "strong": 0.0, "weak": 0.0},
            "au_domain_boost": 0.07,
            "au_domain_suffixes": [".com.au", ".au"],
            "title_keyword_boost": 0.0,
            "title_keywords": [],
            "now_utc": "2026-02-25T12:00:00Z",
        }
        au = compute_news_weighted_score(0.5, "2026-02-25T10:00:00Z", "none", "", "afr.com.au", cfg)
        non_au = compute_news_weighted_score(0.5, "2026-02-25T10:00:00Z", "none", "", "reuters.com", cfg)
        self.assertGreater(au, non_au)

    def test_keyword_boost(self):
        cfg = {
            "enable_signal_weighting": True,
            "recency_max_boost": 0.0,
            "ticker_match_boosts": {"exact": 0.0, "strong": 0.0, "weak": 0.0},
            "au_domain_boost": 0.0,
            "title_keyword_boost": 0.08,
            "title_keywords": ["guidance", "downgrade"],
            "now_utc": "2026-02-25T12:00:00Z",
        }
        with_keyword = compute_news_weighted_score(
            0.45,
            "2026-02-25T10:00:00Z",
            "none",
            "BHP raises guidance after strong quarter",
            "example.com",
            cfg,
        )
        without_keyword = compute_news_weighted_score(
            0.45,
            "2026-02-25T10:00:00Z",
            "none",
            "BHP reports quarterly update",
            "example.com",
            cfg,
        )
        self.assertGreater(with_keyword, without_keyword)

    def test_disable_weighting_fallback(self):
        cfg = {
            "enable_signal_weighting": False,
            "recency_half_life_hours": 1,
            "recency_max_boost": 9.0,
            "ticker_match_boosts": {"exact": 9.0, "strong": 9.0, "weak": 9.0},
            "au_domain_boost": 9.0,
            "title_keyword_boost": 9.0,
            "title_keywords": ["guidance"],
            "now_utc": "2026-02-25T12:00:00Z",
        }
        semantic = 0.4321
        scored = compute_news_weighted_score(
            semantic,
            "2026-02-25T11:00:00Z",
            "exact",
            "guidance",
            "afr.com.au",
            cfg,
        )
        self.assertAlmostEqual(scored, semantic, places=8)


if __name__ == "__main__":
    unittest.main()
