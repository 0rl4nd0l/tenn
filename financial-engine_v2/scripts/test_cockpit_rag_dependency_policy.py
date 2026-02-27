#!/usr/bin/env python3
import builtins
import contextlib
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.integrations.qual_context_bootstrap import (  # noqa: E402
    build_qual_context_reader,
    resolve_rag_dependency_policy,
)


def _base_qc_cfg() -> dict[str, object]:
    return {
        "embed_backend": "sentence-transformers",
        "embed_model": "bge-large-en-v1.5",
        "corpus_filter": "company",
        "exclude_corpus_filter": "",
        "top_k": 8,
        "max_text_chars": 1200,
        "ollama_endpoint": "http://127.0.0.1:11434",
        "hash_dim": 384,
        "st_device": "auto",
        "st_batch_size": 16,
    }


def _create_qual_context_db(path: Path, embedding_dim: int) -> None:
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS context_chunks (
                chunk_id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                file TEXT NOT NULL,
                section TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding_json TEXT NOT NULL
            )
            """
        )
        vec = [0.0] * max(1, int(embedding_dim))
        cur.execute(
            """
            INSERT OR REPLACE INTO context_chunks(chunk_id, company, file, section, text, embedding_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("chunk-1", "BHP", "/tmp/doc.pdf", "fulltext_context", "test", json.dumps(vec)),
        )
        conn.commit()
    finally:
        conn.close()


@contextlib.contextmanager
def _block_sentence_transformers_import() -> object:
    original_import = builtins.__import__
    removed_modules: dict[str, object] = {}
    for key in list(sys.modules.keys()):
        if key == "sentence_transformers" or key.startswith("sentence_transformers."):
            removed_modules[key] = sys.modules.pop(key)

    def guarded_import(name: str, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "sentence_transformers" or name.startswith("sentence_transformers."):
            raise ImportError("No module named 'sentence_transformers'")
        return original_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded_import
    try:
        yield
    finally:
        builtins.__import__ = original_import
        sys.modules.update(removed_modules)


class CockpitRagDependencyPolicyTests(unittest.TestCase):
    def test_auto_policy_maps_by_profile(self):
        self.assertEqual(resolve_rag_dependency_policy("auto", "prod"), "error")
        self.assertEqual(resolve_rag_dependency_policy("auto", "production"), "error")
        self.assertEqual(resolve_rag_dependency_policy("auto", "live"), "error")
        self.assertEqual(resolve_rag_dependency_policy("auto", "default"), "fallback_hash")
        self.assertEqual(resolve_rag_dependency_policy("auto", "dev"), "fallback_hash")

    def test_invalid_policy_raises(self):
        with self.assertRaises(ValueError):
            resolve_rag_dependency_policy("unknown-policy", "default")

    def test_error_policy_fails_when_sentence_transformers_missing(self):
        qc_cfg = _base_qc_cfg()
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "qual_context.sqlite"
            _create_qual_context_db(db_path, embedding_dim=384)
            with _block_sentence_transformers_import():
                with self.assertRaises(RuntimeError) as ctx:
                    build_qual_context_reader(
                        repo_root=REPO_ROOT,
                        qc_cfg=qc_cfg,
                        db_path=db_path,
                        dependency_policy="error",
                    )
        self.assertIn("RAG startup validation failed", str(ctx.exception))

    def test_fallback_hash_policy_switches_backend_when_sentence_transformers_missing(self):
        qc_cfg = _base_qc_cfg()
        startup_notices: list[str] = []
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "qual_context.sqlite"
            _create_qual_context_db(db_path, embedding_dim=384)
            with _block_sentence_transformers_import():
                reader = build_qual_context_reader(
                    repo_root=REPO_ROOT,
                    qc_cfg=qc_cfg,
                    db_path=db_path,
                    dependency_policy="fallback_hash",
                    startup_notices=startup_notices,
                )
        self.assertEqual(reader.embed_backend.lower(), "hash")
        self.assertEqual(reader.embed_model.lower(), "hash")
        self.assertTrue(startup_notices)
        self.assertIn("fallback to 'hash'", startup_notices[0].lower())

    def test_fallback_hash_policy_rejects_embedding_dim_mismatch(self):
        qc_cfg = _base_qc_cfg()
        startup_notices: list[str] = []
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "qual_context.sqlite"
            _create_qual_context_db(db_path, embedding_dim=1024)
            with _block_sentence_transformers_import():
                with self.assertRaises(RuntimeError) as ctx:
                    build_qual_context_reader(
                        repo_root=REPO_ROOT,
                        qc_cfg=qc_cfg,
                        db_path=db_path,
                        dependency_policy="fallback_hash",
                        startup_notices=startup_notices,
                    )
        self.assertIn("embedding dimension mismatch", str(ctx.exception).lower())

    def test_fallback_hash_policy_does_not_mask_non_dependency_failures(self):
        qc_cfg = _base_qc_cfg()
        missing_db_path = Path("/tmp") / f"missing_qual_context_{os.getpid()}.sqlite"
        if missing_db_path.exists():
            missing_db_path.unlink()
        with self.assertRaises(RuntimeError) as ctx:
            build_qual_context_reader(
                repo_root=REPO_ROOT,
                qc_cfg=qc_cfg,
                db_path=missing_db_path,
                dependency_policy="fallback_hash",
            )
        self.assertIn("RAG startup validation failed", str(ctx.exception))
        self.assertIn("db not found", str(ctx.exception).lower())

    def test_cuda_strict_mode_fails_when_gpu_not_visible(self):
        qc_cfg = _base_qc_cfg()
        qc_cfg["st_device"] = "cuda_strict"
        torch_stub = types.SimpleNamespace(
            cuda=types.SimpleNamespace(
                is_available=lambda: False,
                device_count=lambda: 0,
            )
        )
        st_stub = types.ModuleType("sentence_transformers")
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "qual_context.sqlite"
            _create_qual_context_db(db_path, embedding_dim=384)
            with mock.patch.dict(sys.modules, {"sentence_transformers": st_stub, "torch": torch_stub}):
                with self.assertRaises(RuntimeError) as ctx:
                    build_qual_context_reader(
                        repo_root=REPO_ROOT,
                        qc_cfg=qc_cfg,
                        db_path=db_path,
                        dependency_policy="error",
                    )
        self.assertIn("cuda strict mode", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
