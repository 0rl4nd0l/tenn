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
    def __init__(self, payload: dict | None = None) -> None:
        self.payload = payload or {"ok": True, "payload": {"ok": True, "hits": []}}

    def query_rag(self, *, query: str, ticker: str | None = None, top_k: int = 8, timeout: float = 12.0):  # noqa: ARG002
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

    def test_query_uses_results_fallback_shape(self):
        reader = QualContextReader(
            repo_root=REPO_ROOT,
            backend_api_client=_BackendStub(
                {
                    "ok": True,
                    "payload": {
                        "ok": True,
                        "results": [
                            {
                                "score": 0.77,
                                "title": "Fallback results shape",
                                "text": "backend result item",
                            }
                        ],
                    },
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
        self.assertEqual(len(payload.get("hits", [])), 1)
        self.assertEqual(payload["hits"][0].get("title"), "Fallback results shape")


if __name__ == "__main__":
    unittest.main()
