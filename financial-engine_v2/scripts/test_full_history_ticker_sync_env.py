#!/usr/bin/env python3
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))


class _Field:
    def __eq__(self, other):  # noqa: ANN001
        return self


if "httpx" not in sys.modules:
    sys.modules["httpx"] = types.ModuleType("httpx")
if "_run_metadata" not in sys.modules:
    run_metadata_stub = types.ModuleType("_run_metadata")
    run_metadata_stub.build_run_metadata = lambda *args, **kwargs: {}
    sys.modules["_run_metadata"] = run_metadata_stub
if "app.core.config" not in sys.modules:
    cfg_stub = types.ModuleType("app.core.config")
    cfg_stub.settings = SimpleNamespace(
        database_url="sqlite:////tmp/runtime.db",
        data_root="/tmp/runtime-data",
        docs_root="/tmp/runtime-data/asx/docs",
    )
    sys.modules["app.core.config"] = cfg_stub
if "app.core.db" not in sys.modules:
    db_stub = types.ModuleType("app.core.db")
    db_stub.SessionLocal = lambda: None
    sys.modules["app.core.db"] = db_stub
if "app.models" not in sys.modules:
    models_stub = types.ModuleType("app.models")
    models_stub.Document = type("Document", (), {"ticker": _Field()})
    sys.modules["app.models"] = models_stub
if "app.providers.universe" not in sys.modules:
    universe_stub = types.ModuleType("app.providers.universe")
    universe_stub.ASX20 = ["BHP"]
    sys.modules["app.providers.universe"] = universe_stub
pipeline_stub = sys.modules.get("app.services.pipeline") or types.ModuleType("app.services.pipeline")
pipeline_stub.backfill_ticker_sync = lambda *args, **kwargs: {}
sys.modules["app.services.pipeline"] = pipeline_stub
if "health_guard" not in sys.modules:
    health_stub = types.ModuleType("health_guard")
    health_stub.assert_healthy = lambda *args, **kwargs: None
    health_stub.load_health_snapshot = lambda *args, **kwargs: {}
    sys.modules["health_guard"] = health_stub
if "ticker_quarantine" not in sys.modules:
    quarantine_stub = types.ModuleType("ticker_quarantine")
    quarantine_stub.add_to_quarantine = lambda *args, **kwargs: None
    quarantine_stub.load_quarantine = lambda *args, **kwargs: set()
    sys.modules["ticker_quarantine"] = quarantine_stub


def _load_module():
    path = REPO_ROOT / "scripts" / "full_history_ticker_sync.py"
    spec = importlib.util.spec_from_file_location("full_history_ticker_sync", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FullHistoryTickerSyncEnvTests(unittest.TestCase):
    def test_build_child_backend_env_uses_active_runtime_settings(self) -> None:
        mod = _load_module()
        mod.settings = SimpleNamespace(
            database_url="sqlite:////tmp/runtime.db",
            data_root="/tmp/runtime-data",
            docs_root="/tmp/runtime-data/asx/docs",
        )

        with mock.patch.dict(
            os.environ,
            {"PYTHONPATH": "existing/path"},
            clear=True,
        ):
            env = mod._build_child_backend_env()

        self.assertEqual(env["DATABASE_URL"], "sqlite:////tmp/runtime.db")
        self.assertEqual(env["DATA_ROOT"], "/tmp/runtime-data")
        self.assertEqual(env["DOCS_ROOT"], "/tmp/runtime-data/asx/docs")
        self.assertEqual(env["PYTHONPATH"], f"backend{os.pathsep}existing/path")

    def test_build_child_backend_env_preserves_explicit_overrides(self) -> None:
        mod = _load_module()
        mod.settings = SimpleNamespace(
            database_url="sqlite:////tmp/runtime.db",
            data_root="/tmp/runtime-data",
            docs_root="/tmp/runtime-data/asx/docs",
        )

        with mock.patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://example/override",
                "DATA_ROOT": "/override/data",
                "DOCS_ROOT": "/override/docs",
            },
            clear=True,
        ):
            env = mod._build_child_backend_env()

        self.assertEqual(env["DATABASE_URL"], "postgresql://example/override")
        self.assertEqual(env["DATA_ROOT"], "/override/data")
        self.assertEqual(env["DOCS_ROOT"], "/override/docs")
        self.assertEqual(env["PYTHONPATH"], "backend")

    def test_marketindex_recovery_row_summary_counts_blocked_markers(self) -> None:
        mod = _load_module()

        rows = [
            SimpleNamespace(
                ticker="BHP",
                pdf_sha256="blocked_marketindex_headed_required",
                document_id="doc-1",
                source_url="https://www.marketindex.com.au/asx/bhp/announcements/example-2A0000001",
            ),
            SimpleNamespace(
                ticker="BHP",
                pdf_sha256="clean_pdf_hash",
                document_id="doc-2",
                source_url="https://www.marketindex.com.au/asx/bhp/announcements/example-2A0000002",
            ),
        ]

        summary = mod._summarize_marketindex_headed_recovery_rows(rows, ["BHP"])

        self.assertEqual(summary["requires_headed_recovery_count"], 1)
        self.assertEqual(
            summary["recommended_command"],
            "python3 scripts/recover_marketindex_headed.py --ticker BHP",
        )
        self.assertEqual(summary["samples"][0]["stage"], "post_backfill_report")


if __name__ == "__main__":
    unittest.main()
