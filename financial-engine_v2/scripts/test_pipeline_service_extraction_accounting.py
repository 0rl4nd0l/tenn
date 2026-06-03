#!/usr/bin/env python3
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

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

    def test_unknown_extraction_status_is_counted_as_error(self):
        db = mock.MagicMock()
        db.close = mock.MagicMock()
        discovery = self._base_discovery()
        discovery["new_document_ids"] = ["11111111-1111-1111-1111-111111111111"]
        with (
            mock.patch("app.services.pipeline_service.SessionLocal", return_value=db),
            mock.patch(
                "app.services.pipeline_service.pipeline_core.discover_and_insert_documents",
                return_value=discovery,
            ),
            mock.patch("app.services.pipeline_service.pipeline_core.download_pdf_for_document"),
            mock.patch(
                "app.services.pipeline_service.pipeline_core.process_document",
                return_value={"extraction_status": "weird"},
            ),
            mock.patch("app.services.pipeline_service.settings.enable_importance_classification", False),
        ):
            result = run_pipeline_sync(PipelineJobSpec(ticker="BHP", years=1, process_documents=True))

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["processed_ok_count"], 0)
        self.assertEqual(result["extraction_unknown_count"], 1)
        self.assertEqual(result["extraction_status_counts"], {"weird": 1})
        self.assertEqual(result["errors"][0]["error"], "extraction_status_unknown")

    def test_marketindex_blocker_uses_status_fields_not_pdf_hash(self):
        db = mock.MagicMock()
        db.close = mock.MagicMock()
        doc = mock.MagicMock()
        db.query.return_value.filter.return_value.first.return_value = doc
        discovery = self._base_discovery()
        discovery["new_document_ids"] = ["11111111-1111-1111-1111-111111111111"]
        with (
            mock.patch("app.services.pipeline_service.SessionLocal", return_value=db),
            mock.patch(
                "app.services.pipeline_service.pipeline_core.discover_and_insert_documents",
                return_value=discovery,
            ),
            mock.patch(
                "app.services.pipeline_service.pipeline_core.download_pdf_for_document",
                side_effect=RuntimeError("marketindex_headed_required: headed browser required"),
            ),
            mock.patch("app.services.pipeline_service.settings.enable_importance_classification", False),
        ):
            result = run_pipeline_sync(PipelineJobSpec(ticker="BHP", years=1, process_documents=False))

        self.assertEqual(result["skipped_download"], 1)
        self.assertEqual(doc.pdf_sha256, "")
        self.assertEqual(doc.download_status, "blocked")
        self.assertEqual(doc.download_error_code, "blocked_marketindex_headed_required")

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
