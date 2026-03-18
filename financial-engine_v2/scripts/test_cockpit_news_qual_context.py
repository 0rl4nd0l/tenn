#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.integrations.qual_context import QualContextReader  # noqa: E402


class _BackendStub:
    def __init__(self, result: dict):
        self.result = dict(result)
        self.last_kwargs = None

    def query_rag(self, *, query: str, ticker: str | None = None, top_k: int = 8, timeout: float = 12.0):  # noqa: ARG002
        self.last_kwargs = {
            "query": query,
            "ticker": ticker,
            "top_k": top_k,
        }
        return dict(self.result)


class CockpitNewsQualContextTests(unittest.TestCase):
    def test_query_routes_to_backend_and_preserves_hits(self):
        backend = _BackendStub(
            {
                "ok": True,
                "payload": {
                    "ok": True,
                    "hits": [
                        {
                            "score": 0.91,
                            "title": "ASX:BHP guidance update",
                            "text": "BHP updated market guidance.",
                            "corpus": "news",
                        }
                    ],
                    "candidate_count": 3,
                    "filtered_count": 1,
                },
            }
        )
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=backend,
            embed_backend="ollama",
            embed_model="nomic-embed-text",
            corpus_filter="news",
            ticker_match_mode="soft",
            top_k=4,
        )
        reader.validate_runtime()
        payload = reader.query(
            query="BHP guidance",
            company="",
            deep_mode=False,
            top_k=3,
            ticker_filter="BHP",
            source_filter="",
        )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(backend.last_kwargs, {"query": "BHP guidance", "ticker": "BHP", "top_k": 3})
        self.assertEqual(int(payload.get("candidate_count", 0)), 3)
        self.assertEqual(int(payload.get("filtered_count", 0)), 1)
        hits = payload.get("hits", [])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].get("corpus"), "news")
        self.assertIsNotNone(hits[0].get("semantic_score"))
        self.assertIsNotNone(hits[0].get("final_score"))

    def test_query_fails_fast_when_backend_errors(self):
        backend = _BackendStub({"ok": False, "error": "backend unavailable"})
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=backend,
            embed_backend="ollama",
            embed_model="nomic-embed-text",
            corpus_filter="news",
            ticker_match_mode="soft",
            top_k=4,
        )
        payload = reader.query(
            query="BHP guidance",
            company="",
            deep_mode=False,
            top_k=3,
            ticker_filter="BHP",
            source_filter="",
        )

        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("hits"), [])
        self.assertEqual(payload.get("error"), "backend unavailable")


if __name__ == "__main__":
    unittest.main()
