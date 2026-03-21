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

    def __init__(self, payload: dict | None = None) -> None:
        self.payload = payload if payload is not None else {"results": []}

    def rag_query(
        self,
        q: str,
        *,
        top_k: int = 10,
        ticker: str | None = None,
        timeout: float = 15.0,
        **kwargs,
    ) -> dict:
        return dict(self.payload)


class CockpitBackendOnlyRagPolicyTests(unittest.TestCase):
    def test_hash_backend_is_rejected(self):
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=_BackendStub(),
            embed_backend="hash",
            embed_model="hash",
        )
        with self.assertRaises(RuntimeError) as ctx:
            reader.validate_runtime()
        self.assertEqual(str(ctx.exception), "Cockpit RAG must use backend API. Local embeddings disabled.")

    def test_sentence_transformers_backend_is_rejected(self):
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=_BackendStub(),
            embed_backend="sentence-transformers",
            embed_model="bge-large-en-v1.5",
        )
        with self.assertRaises(RuntimeError) as ctx:
            reader.validate_runtime()
        self.assertEqual(str(ctx.exception), "Cockpit RAG must use backend API. Local embeddings disabled.")

    def test_query_parses_results_list_shape(self):
        """Backend returns {"results": [{"score": ..., "payload": {...}}]} — hits are unwrapped."""
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=_BackendStub(
                {
                    "results": [
                        {
                            "score": 0.77,
                            "payload": {
                                "title": "Results list shape",
                                "text": "backend result item",
                                "article_id": "x1",
                            },
                        }
                    ],
                }
            ),
            embed_backend="ollama",
            embed_model="nomic-embed-text",
            corpus_filter="news",
        )
        payload = reader.query(
            query="BHP update",
            company="",
            deep_mode=False,
            top_k=2,
            ticker_filter="BHP",
        )
        self.assertTrue(payload.get("ok"))
        hits = payload.get("hits", [])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].get("title"), "Results list shape")
        self.assertAlmostEqual(hits[0].get("semantic_score"), 0.77)


if __name__ == "__main__":
    unittest.main()
