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
    """Stub matching BackendApiClient.rag_query() — the real production interface."""

    def __init__(self, result: dict) -> None:
        self.result = dict(result)
        self.last_kwargs: dict | None = None

    def rag_query(
        self,
        q: str,
        *,
        top_k: int = 10,
        ticker: str | None = None,
        provider: str | None = None,
        language: str = "en",
        date_from: str | None = None,
        date_to: str | None = None,
        timeout: float = 15.0,
    ) -> dict:
        self.last_kwargs = {"q": q, "ticker": ticker, "top_k": top_k}
        return dict(self.result)


class CockpitNewsQualContextTests(unittest.TestCase):
    def test_validate_runtime_passes_when_client_has_rag_query(self):
        """validate_runtime() must accept a client with rag_query(), not query_rag()."""
        backend = _BackendStub({"results": []})
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=backend,
            embed_backend="ollama",
            embed_model="nomic-embed-text",
        )
        reader.validate_runtime()  # must not raise

    def test_validate_runtime_rejects_client_without_rag_query(self):
        """validate_runtime() must reject a client that only has the old query_rag() name."""

        class _OldStyleClient:
            def query_rag(self, *, query, ticker=None, top_k=8, timeout=12.0):
                return {}

        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=_OldStyleClient(),
            embed_backend="ollama",
            embed_model="nomic-embed-text",
        )
        with self.assertRaises(RuntimeError) as ctx:
            reader.validate_runtime()
        self.assertIn("rag_query", str(ctx.exception))

    def test_query_calls_rag_query_with_correct_positional_arg(self):
        """query() must call backend.rag_query(q=...) — not query_rag(query=...)."""
        backend = _BackendStub(
            {
                "results": [
                    {
                        "score": 0.91,
                        "payload": {
                            "article_id": "abc123",
                            "title": "ASX:BHP guidance update",
                            "text": "BHP updated market guidance.",
                            "provider": "eodhd",
                            "language": "en",
                            "published_at": "2026-03-20T09:00:00Z",
                            "tickers": ["BHP"],
                        },
                    }
                ]
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
        payload = reader.query(
            query="BHP guidance",
            company="",
            deep_mode=False,
            top_k=3,
            ticker_filter="BHP",
            source_filter="",
        )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(backend.last_kwargs, {"q": "BHP guidance", "ticker": "BHP", "top_k": 3})

    def test_query_parses_results_list_from_backend_response(self):
        """`{"results": [...]}` response is correctly unwrapped into hits."""
        backend = _BackendStub(
            {
                "results": [
                    {
                        "score": 0.91,
                        "payload": {
                            "article_id": "abc123",
                            "title": "ASX:BHP guidance update",
                            "text": "BHP updated market guidance.",
                            "provider": "eodhd",
                        },
                    }
                ]
            }
        )
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=backend,
            embed_backend="ollama",
            embed_model="nomic-embed-text",
            corpus_filter="news",
            top_k=4,
        )
        payload = reader.query(query="BHP guidance", top_k=3, ticker_filter="BHP")

        self.assertTrue(payload.get("ok"))
        hits = payload.get("hits", [])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].get("title"), "ASX:BHP guidance update")
        self.assertAlmostEqual(hits[0].get("semantic_score"), 0.91)
        self.assertAlmostEqual(hits[0].get("final_score"), 0.91)
        self.assertIsNone(hits[0].get("score"))  # score lives in semantic_score, not raw key

    def test_query_returns_empty_hits_when_results_is_empty(self):
        backend = _BackendStub({"results": []})
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=backend,
            embed_backend="ollama",
            embed_model="nomic-embed-text",
            corpus_filter="news",
        )
        payload = reader.query(query="BHP guidance", top_k=3, ticker_filter="BHP")

        self.assertEqual(payload.get("hits"), [])

    def test_query_fails_gracefully_when_backend_raises(self):
        class _ErrorBackend:
            def rag_query(self, q: str, **kwargs):
                raise RuntimeError("backend down")

        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=_ErrorBackend(),
            embed_backend="ollama",
            embed_model="nomic-embed-text",
        )
        payload = reader.query(query="BHP guidance", top_k=3, ticker_filter="BHP")

        self.assertFalse(payload.get("ok"))
        self.assertEqual(payload.get("hits"), [])
        self.assertIn("backend down", str(payload.get("error")))


if __name__ == "__main__":
    unittest.main()
