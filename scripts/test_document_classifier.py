import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import pytest

canvas_mod = pytest.importorskip("reportlab.pdfgen.canvas")


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
CLASSIFIER = load_module(str(SCRIPTS_DIR / "document_classifier.py"), "document_classifier")
EXTRACT = load_module(
    str(SCRIPTS_DIR / "extract_financial_metrics.py"),
    "extract_financial_metrics_for_classifier_tests",
)


class TestDocumentClassifier(unittest.TestCase):
    def _write_pdf(self, path: Path, pages: list[str]) -> None:
        pdf = canvas_mod.Canvas(str(path))
        for page_text in pages:
            y = 800
            for line in page_text.splitlines():
                pdf.drawString(72, y, line)
                y -= 18
            pdf.showPage()
        pdf.save()

    def test_classifies_financial_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "half-year-report.pdf"
            self._write_pdf(
                pdf_path,
                [
                    "Half Year Financial Report\nConsolidated Financial Statements\n"
                    "Statement of Financial Position\nIncome Statement\nCash Flow Statement"
                ],
            )

            result = CLASSIFIER.classify_document(pdf_path)

        self.assertTrue(result["is_financial"])
        self.assertEqual(result["document_type"], "financial_report")

    def test_classifies_announcement(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "market-announcement.pdf"
            self._write_pdf(
                pdf_path,
                [
                    "ASX Announcement\nCompany Announcement\nMarket announcement regarding dividend policy"
                ],
            )

            result = CLASSIFIER.classify_document(pdf_path)

        self.assertFalse(result["is_financial"])
        self.assertEqual(result["document_type"], "announcement")

    def test_classifies_presentation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "investor-presentation.pdf"
            self._write_pdf(
                pdf_path,
                [
                    "Investor Presentation\nConference slides\nTimetable and speaker notes"
                ],
            )

            result = CLASSIFIER.classify_document(pdf_path)

        self.assertFalse(result["is_financial"])
        self.assertEqual(result["document_type"], "presentation")


class TestDocumentClassifierIntegration(unittest.TestCase):
    def _write_pdf(self, path: Path, pages: list[str]) -> None:
        pdf = canvas.Canvas(str(path))
        for page_text in pages:
            y = 800
            for line in page_text.splitlines():
                pdf.drawString(72, y, line)
                y -= 18
            pdf.showPage()
        pdf.save()

    def test_nonfinancial_document_skips_docling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "AAA" / "financial_performance"
            docs_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = docs_dir / "investor-presentation.pdf"
            self._write_pdf(pdf_path, ["Investor Presentation\nConference slides"])
            out_json = Path(tmpdir) / "out.json"
            out_csv = Path(tmpdir) / "out.csv"
            out_context = Path(tmpdir) / "context.json"
            out_rejected = Path(tmpdir) / "rejected.json"
            out_blocks = Path(tmpdir) / "blocks.json"
            out_diag = Path(tmpdir) / "diagnostics.json"
            argv = [
                "extract_financial_metrics.py",
                "--pdf-dir",
                str(Path(tmpdir)),
                "--extractor",
                "docling",
                "--out-json",
                str(out_json),
                "--out-csv",
                str(out_csv),
                "--out-context-json",
                str(out_context),
                "--out-rejected-json",
                str(out_rejected),
                "--out-blocks-json",
                str(out_blocks),
                "--out-document-diagnostics-json",
                str(out_diag),
                "--no-sqlite",
            ]

            with mock.patch.object(sys, "argv", argv):
                with mock.patch.object(EXTRACT, "_get_docling_converter", return_value=(object(), None)):
                    with mock.patch.object(EXTRACT, "_docling_cuda_available", return_value=False):
                        with mock.patch.object(EXTRACT, "resolve_docling_runtime_settings", return_value=("fast", 0)):
                            with mock.patch.object(
                                EXTRACT,
                                "extract_table_metrics_docling",
                                side_effect=AssertionError("docling should not run"),
                            ):
                                with mock.patch.object(
                                    EXTRACT,
                                    "extract_table_metrics",
                                    side_effect=AssertionError("pdftotext fallback should not run"),
                                ):
                                    with mock.patch.object(
                                        EXTRACT,
                                        "classify_document",
                                        return_value={
                                            "is_financial": False,
                                            "document_type": "presentation",
                                        },
                                    ):
                                        rc = EXTRACT.main()
            diagnostics = json.loads(out_diag.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(diagnostics[0]["extractor_selected"], "skipped_non_financial")
        self.assertEqual(diagnostics[0]["skip_reason"], "non_financial_document")
        self.assertEqual(
            diagnostics[0]["document_classifier"],
            {
                "is_financial": False,
                "document_type": "presentation",
            },
        )

    def test_force_extract_bypasses_document_classifier_skip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "AAA" / "financial_performance"
            docs_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = docs_dir / "investor-presentation.pdf"
            self._write_pdf(pdf_path, ["Investor Presentation\nConference slides"])
            out_json = Path(tmpdir) / "out.json"
            out_csv = Path(tmpdir) / "out.csv"
            out_context = Path(tmpdir) / "context.json"
            out_rejected = Path(tmpdir) / "rejected.json"
            out_blocks = Path(tmpdir) / "blocks.json"
            out_diag = Path(tmpdir) / "diagnostics.json"
            docling_calls = {"count": 0}

            def fake_docling(*args, **kwargs):
                docling_calls["count"] += 1
                pdf = Path(args[0])
                return [], [], EXTRACT.build_split_result(
                    [],
                    [EXTRACT._build_parse_failure_context_row(pdf, reason="docling_called_for_test", message="")],
                    [],
                    diagnostics={
                        "docling_row_count_before_filtering": 0,
                        "reconciliation_repairs": 0,
                        "tsr_tables_processed": 0,
                    },
                )

            argv = [
                "extract_financial_metrics.py",
                "--pdf-dir",
                str(Path(tmpdir)),
                "--extractor",
                "docling",
                "--force-extract",
                "--out-json",
                str(out_json),
                "--out-csv",
                str(out_csv),
                "--out-context-json",
                str(out_context),
                "--out-rejected-json",
                str(out_rejected),
                "--out-blocks-json",
                str(out_blocks),
                "--out-document-diagnostics-json",
                str(out_diag),
                "--no-sqlite",
            ]

            with mock.patch.object(sys, "argv", argv):
                with mock.patch.object(EXTRACT, "_get_docling_converter", return_value=(object(), None)):
                    with mock.patch.object(EXTRACT, "_docling_cuda_available", return_value=False):
                        with mock.patch.object(EXTRACT, "resolve_docling_runtime_settings", return_value=("fast", 0)):
                            with mock.patch.object(EXTRACT, "extract_table_metrics_docling", side_effect=fake_docling):
                                with mock.patch.object(
                                    EXTRACT,
                                    "evaluate_docling_fallback",
                                    return_value={
                                        "should_fallback": False,
                                        "reasons": [],
                                        "fallback_reason": None,
                                        "consistency_report": {"failed_checks": []},
                                    },
                                ):
                                    with mock.patch.object(
                                        EXTRACT,
                                        "classify_document",
                                        return_value={
                                            "is_financial": False,
                                            "document_type": "presentation",
                                        },
                                    ):
                                        rc = EXTRACT.main()
            diagnostics = json.loads(out_diag.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(docling_calls["count"], 1)
        self.assertEqual(diagnostics[0]["extractor_selected"], "docling")
        self.assertIsNone(diagnostics[0]["skip_reason"])


if __name__ == "__main__":
    unittest.main()
