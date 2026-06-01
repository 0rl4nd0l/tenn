#!/usr/bin/env python3
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "broad_extraction_test.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("broad_extraction_test", str(SCRIPT_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {SCRIPT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _touch_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n")
    return path


class BroadExtractionDocsRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_explicit_docs_root_is_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = Path(tmp) / "docs"
            pdf = _touch_pdf(
                docs_root
                / "BHP"
                / "financial_performance"
                / "2026-01-01_report_11111111-1111-4111-8111-111111111111.pdf"
            )

            with mock.patch.dict(os.environ, {"DOCS_ROOT": "/does/not/matter"}, clear=True):
                self.assertEqual(self.mod.resolve_docs_root(docs_root), docs_root)
                self.assertEqual(self.mod.discover_pdfs(docs_root), [pdf])

    def test_data_root_is_used_when_it_contains_financial_pdfs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "runtime-data"
            docs_root = data_root / "asx" / "docs"
            pdf = _touch_pdf(
                docs_root
                / "MIN"
                / "financial_performance"
                / "2026-02-20_half-year_22222222-2222-4222-8222-222222222222.pdf"
            )

            with mock.patch.dict(os.environ, {"DATA_ROOT": str(data_root)}, clear=True):
                self.assertEqual(self.mod.resolve_docs_root(), docs_root)
                self.assertEqual(self.mod.discover_pdfs(), [pdf])

    def test_missing_explicit_docs_root_returns_empty_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing"

            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(self.mod.discover_pdfs(missing_root), [])

    def test_external_pdf_record_path_is_stable_logical_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = Path(tmp) / "data" / "asx" / "docs"
            pdf = _touch_pdf(
                docs_root
                / "A2M"
                / "financial_performance"
                / "2026-02-16_appendix-4d_33333333-3333-4333-8333-333333333333.pdf"
            )

            self.assertEqual(
                self.mod._source_path_for_record(pdf, docs_root),
                "data/asx/docs/A2M/financial_performance/"
                "2026-02-16_appendix-4d_33333333-3333-4333-8333-333333333333.pdf",
            )

    def test_empty_summary_has_stable_shape(self) -> None:
        summary = self.mod.compute_summary([])

        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["success_rate"], 0)
        self.assertEqual(
            sorted(summary["metric_coverage"]),
            sorted(self.mod.METRIC_FIELDS),
        )
        self.assertEqual(summary["sanity_checks"]["period_end_valid"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
