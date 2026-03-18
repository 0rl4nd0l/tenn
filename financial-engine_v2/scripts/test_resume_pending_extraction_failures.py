#!/usr/bin/env python3
import argparse
import importlib.util
import json
import os
import sys
import tempfile
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
if "httpx" not in sys.modules:
    httpx_stub = types.ModuleType("httpx")
    httpx_stub.HTTPStatusError = Exception  # type: ignore[attr-defined]
    httpx_stub.ConnectError = OSError  # type: ignore[attr-defined]
    httpx_stub.TimeoutException = TimeoutError  # type: ignore[attr-defined]
    httpx_stub.NetworkError = OSError  # type: ignore[attr-defined]
    sys.modules["httpx"] = httpx_stub
if "sqlalchemy" not in sys.modules:
    sqlalchemy_stub = types.ModuleType("sqlalchemy")
    sqlalchemy_stub.or_ = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    sys.modules["sqlalchemy"] = sqlalchemy_stub


class _Field:
    def __eq__(self, other):  # noqa: ANN001
        return self

    def is_(self, other):  # noqa: ANN001
        return self

    def desc(self):
        return self

    def nullslast(self):
        return self


if "app.core.db" not in sys.modules:
    db_stub = types.ModuleType("app.core.db")
    db_stub.SessionLocal = lambda: None
    def get_db():
        db = db_stub.SessionLocal()
        try:
            yield db
        finally:
            pass
    db_stub.get_db = get_db
    sys.modules["app.core.db"] = db_stub
if "app.core.config" not in sys.modules:
    cfg_stub = types.ModuleType("app.core.config")
    cfg_stub.settings = SimpleNamespace(
        celery_broker_url="memory://",
        celery_result_backend="cache+memory://",
        enable_embeddings=True,
        enable_qdrant=True,
        importance_output_root=None,
        importance_materialize_output=False,
        importance_include_pdf_text=False,
        importance_link_mode="symlink",
        importance_sort_source_docs=False,
    )
    sys.modules["app.core.config"] = cfg_stub
if "app.models.documents" not in sys.modules:
    docs_stub = types.ModuleType("app.models.documents")
    docs_stub.Document = type(
        "Document",
        (),
        {"ticker": _Field(), "pdf_sha256": _Field(), "published_at": _Field()},
    )
    sys.modules["app.models.documents"] = docs_stub
if "app.providers.universe" not in sys.modules:
    universe_stub = types.ModuleType("app.providers.universe")
    universe_stub.ASX20 = ["BHP"]
    sys.modules["app.providers.universe"] = universe_stub
if "app.services.announcement_importance" not in sys.modules:
    importance_stub = types.ModuleType("app.services.announcement_importance")
    importance_stub.classify_documents_and_materialize = lambda *args, **kwargs: {"classified_count": 0}
    sys.modules["app.services.announcement_importance"] = importance_stub
if "app.services.pipeline" not in sys.modules:
    pipeline_stub = types.ModuleType("app.services.pipeline")
    pipeline_stub.discover_and_insert_documents = lambda *args, **kwargs: {}
    pipeline_stub.download_pdf_for_document = lambda *args, **kwargs: None
    pipeline_stub.process_document = lambda *args, **kwargs: {"extraction_status": "ok"}
    pipeline_stub.backfill_ticker_sync = lambda *args, **kwargs: {}
    sys.modules["app.services.pipeline"] = pipeline_stub


def _load_module():
    path = REPO_ROOT / "scripts" / "resume_pending_downloads.py"
    spec = importlib.util.spec_from_file_location("resume_pending_downloads", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeRow:
    def __init__(self, document_id: str, source_url: str = "https://example.com/doc.pdf") -> None:
        self.document_id = document_id
        self.source_url = source_url
        self.pdf_sha256 = ""


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def order_by(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def limit(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return self

    def all(self):
        return list(self._rows)


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, model):  # noqa: ANN001
        return _FakeQuery(self._rows)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


class ResumePendingExtractionFailureTests(unittest.TestCase):
    def test_extraction_failure_is_counted_and_fails_exit_code(self):
        mod = _load_module()
        document_stub = type(
            "Document",
            (),
            {"ticker": _Field(), "pdf_sha256": _Field(), "published_at": _Field()},
        )
        with tempfile.TemporaryDirectory() as td:
            report_path = Path(td) / "resume_report.json"
            fake_db = _FakeDB(rows=[_FakeRow("11111111-1111-1111-1111-111111111111")])
            args = argparse.Namespace(
                ticker=["BHP"],
                limit_per_ticker=0,
                process_documents=True,
                with_embeddings=False,
                report=str(report_path),
                max_retries=1,
                retry_delay_seconds=0.0,
                skip_importance_classification=True,
            )
            with (
                mock.patch.object(mod, "parse_args", return_value=args),
                mock.patch.object(mod, "SessionLocal", return_value=fake_db),
                mock.patch.object(mod, "Document", document_stub),
                mock.patch.object(mod, "download_pdf_for_document", return_value=None),
                mock.patch.object(mod, "process_document", return_value={"extraction_status": "failed"}),
            ):
                with self.assertRaises(SystemExit) as ctx:
                    mod.main()
            self.assertEqual(int(ctx.exception.code), 1)

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["totals"]["processed"], 1)
            self.assertEqual(payload["totals"]["extraction_failed_count"], 1)
            self.assertEqual(payload["totals"]["errors"], 1)
            self.assertEqual(payload["results"][0]["extraction_failed_count"], 1)
            self.assertEqual(payload["results"][0]["error_count"], 1)
            self.assertEqual(payload["results"][0]["errors"][0]["error"], "extraction_failed")


if __name__ == "__main__":
    unittest.main()
