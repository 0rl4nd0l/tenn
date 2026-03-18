#!/usr/bin/env python3
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if "httpx" not in sys.modules:
    httpx_stub = types.ModuleType("httpx")

    class _HTTPStatusError(Exception):
        pass

    httpx_stub.HTTPStatusError = _HTTPStatusError  # type: ignore[attr-defined]
    httpx_stub.ConnectError = OSError  # type: ignore[attr-defined]
    sys.modules["httpx"] = httpx_stub
if "app.core.config" not in sys.modules:
    config_stub = types.ModuleType("app.core.config")
    config_stub.settings = types.SimpleNamespace(
        celery_broker_url="memory://",
        celery_result_backend="cache+memory://",
        enable_importance_classification=False,
        importance_output_root=None,
        importance_materialize_output=False,
        importance_include_pdf_text=False,
        importance_link_mode="symlink",
        importance_sort_source_docs=False,
    )
    sys.modules["app.core.config"] = config_stub
if "app.core.db" not in sys.modules:
    db_stub = types.ModuleType("app.core.db")
    db_stub.SessionLocal = lambda: mock.MagicMock()
    def get_db():
        db = db_stub.SessionLocal()
        try:
            yield db
        finally:
            pass
    db_stub.get_db = get_db
    sys.modules["app.core.db"] = db_stub
if "app.models.documents" not in sys.modules:
    documents_stub = types.ModuleType("app.models.documents")
    documents_stub.Document = type("Document", (), {"document_id": None, "pdf_sha256": ""})
    sys.modules["app.models.documents"] = documents_stub
if "app.services.announcement_importance" not in sys.modules:
    importance_stub = types.ModuleType("app.services.announcement_importance")
    importance_stub.classify_documents_and_materialize = lambda *args, **kwargs: None
    sys.modules["app.services.announcement_importance"] = importance_stub
if "app.services.pipeline" not in sys.modules:
    pipeline_stub = types.ModuleType("app.services.pipeline")
    pipeline_stub.discover_and_insert_documents = lambda *args, **kwargs: {}
    pipeline_stub.download_pdf_for_document = lambda *args, **kwargs: None
    pipeline_stub.process_document = lambda *args, **kwargs: {"extraction_status": "ok"}
    pipeline_stub.backfill_ticker_sync = lambda *args, **kwargs: {}
    sys.modules["app.services.pipeline"] = pipeline_stub

os.chdir(ROOT)

from app.services.pipeline_service import PipelineJobSpec, run_pipeline_sync  # noqa: E402


class PipelineServiceExtractionAccountingTests(unittest.TestCase):
    def _base_discovery(self) -> dict:
        return {
            "ticker": "BHP",
            "found": 2,
            "inserted": 2,
            "new_document_ids": ["11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"],
            "provider_metrics": {},
            "provider_failures_sample": [],
        }

    def test_counts_failed_extractions_as_errors(self):
        db = mock.MagicMock()
        db.close = mock.MagicMock()
        with (
            mock.patch("app.services.pipeline_service.SessionLocal", return_value=db),
            mock.patch(
                "app.services.pipeline_service.pipeline_core.discover_and_insert_documents",
                return_value=self._base_discovery(),
            ),
            mock.patch("app.services.pipeline_service.pipeline_core.download_pdf_for_document"),
            mock.patch(
                "app.services.pipeline_service.pipeline_core.process_document",
                side_effect=[{"extraction_status": "ok"}, {"extraction_status": "failed"}],
            ),
            mock.patch("app.services.pipeline_service.settings.enable_importance_classification", False),
        ):
            result = run_pipeline_sync(PipelineJobSpec(ticker="BHP", years=1, process_documents=True))

        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["processed_ok_count"], 1)
        self.assertEqual(result["extraction_failed_count"], 1)
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(result["errors"][0]["error"], "extraction_failed")

    def test_processed_ok_matches_processed_when_processing_disabled(self):
        db = mock.MagicMock()
        db.close = mock.MagicMock()
        with (
            mock.patch("app.services.pipeline_service.SessionLocal", return_value=db),
            mock.patch(
                "app.services.pipeline_service.pipeline_core.discover_and_insert_documents",
                return_value=self._base_discovery(),
            ),
            mock.patch("app.services.pipeline_service.pipeline_core.download_pdf_for_document"),
            mock.patch("app.services.pipeline_service.settings.enable_importance_classification", False),
        ):
            result = run_pipeline_sync(PipelineJobSpec(ticker="BHP", years=1, process_documents=False))

        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["processed_ok_count"], 2)
        self.assertEqual(result["extraction_failed_count"], 0)
        self.assertEqual(result["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
