#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.integrations.qual_context_bootstrap import (  # noqa: E402
    build_qual_context_reader,
    context_enabled,
)


class _BackendStub:
    def rag_query(self, q: str, *, top_k: int = 10, ticker: str | None = None, timeout: float = 15.0, **kwargs):  # noqa: ARG002
        return {
            "results": [
                {"score": 0.9, "payload": {"title": "stub hit", "ticker": ticker}},
            ]
        }


class CockpitRagBackendOnlyPolicyTests(unittest.TestCase):
    def test_context_enabled_defaults_to_false(self):
        self.assertFalse(context_enabled({}, default=False))
        self.assertTrue(context_enabled({}, default=True))

    def test_context_enabled_honors_explicit_bool_values(self):
        self.assertTrue(context_enabled({"enabled": True}, default=False))
        self.assertFalse(context_enabled({"enabled": False}, default=True))
        self.assertTrue(context_enabled({"enabled": "true"}, default=False))
        self.assertFalse(context_enabled({"enabled": "off"}, default=True))

    def test_build_reader_defaults_to_ollama_nomic(self):
        reader = build_qual_context_reader(
            repo_root=REPO_ROOT,
            qc_cfg={},
            backend_api_client=_BackendStub(),
            context_name="qualitative_context",
        )
        self.assertEqual(reader.embed_backend, "ollama")
        self.assertEqual(reader.embed_model, "nomic-embed-text")

    def test_build_reader_rejects_non_ollama_backend(self):
        with self.assertRaises(RuntimeError) as ctx:
            build_qual_context_reader(
                repo_root=REPO_ROOT,
                qc_cfg={"embed_backend": "hash", "embed_model": "hash"},
                backend_api_client=_BackendStub(),
                context_name="qualitative_context",
            )
        self.assertEqual(str(ctx.exception), "Cockpit RAG must use backend API. Local embeddings disabled.")

    def test_build_reader_requires_backend_query_method(self):
        with self.assertRaises(RuntimeError) as ctx:
            build_qual_context_reader(
                repo_root=REPO_ROOT,
                qc_cfg={"embed_backend": "ollama"},
                backend_api_client=object(),
                context_name="qualitative_context",
            )
        self.assertIn("backend_api_client.rag_query", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
