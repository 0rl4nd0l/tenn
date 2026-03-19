import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock
from pathlib import Path


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
COMPARE = load_module(str(ROOT / "scripts" / "compare_docling_accuracy.py"), "compare_docling_accuracy")


class TestCompareDoclingAccuracyNormalization(unittest.TestCase):
    def test_parse_accounting_number_variants(self):
        self.assertEqual(COMPARE.parse_accounting_number("(123)"), -123.0)
        self.assertEqual(COMPARE.parse_accounting_number("123"), 123.0)
        self.assertEqual(COMPARE.parse_accounting_number("-123"), -123.0)
        self.assertEqual(COMPARE.parse_accounting_number("1,234"), 1234.0)
        self.assertEqual(COMPARE.parse_accounting_number("(1,234)"), -1234.0)

    def test_compare_normalizes_expense_sign_before_comparison(self):
        rows_pdf = [
            {
                "metric": "depreciation_and_amortisation",
                "statement_period_end": "2025-06-30",
                "value": "123",
            }
        ]
        rows_docling = [
            {
                "metric": "depreciation_and_amortisation",
                "statement_period_end": "2025-06-30",
                "value": "(123)",
            }
        ]

        result = COMPARE.compare(rows_pdf, rows_docling)
        self.assertEqual(result["agree"], 1)
        self.assertEqual(result["disagree"], 0)

    def test_compare_normalizes_metric_names_and_period_tolerance(self):
        rows_pdf = [
            {
                "metric": "total revenue",
                "statement_period_end": "2025-06-30",
                "value": "123",
            }
        ]
        rows_docling = [
            {
                "metric": "revenue attributable",
                "statement_period_end": "2025-07-03",
                "value": 123,
            }
        ]

        result = COMPARE.compare(rows_pdf, rows_docling)
        self.assertEqual(result["agree"], 1)
        self.assertEqual(result["disagree"], 0)
        self.assertEqual(result["docling_only"], 0)
        self.assertEqual(result["pdf_only"], 0)


class TestCompareDoclingAccuracyInterpreter(unittest.TestCase):
    def test_run_extract_uses_single_pdf_mode_with_resolved_docling_python(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "sample.pdf"
            out_prefix = Path(tmpdir) / "out"
            pdf_path.write_bytes(b"%PDF-1.4")

            commands = []

            class CompletedProcess:
                returncode = 0
                stderr = ""

            def fake_run(cmd, cwd, capture_output, text, timeout):
                commands.append(
                    {
                        "cmd": list(cmd),
                        "cwd": cwd,
                        "timeout": timeout,
                    }
                )
                return CompletedProcess()

            with mock.patch("subprocess.run", side_effect=fake_run), mock.patch.object(
                COMPARE,
                "resolve_python",
                return_value="/tmp/docling-python",
            ):
                result = COMPARE.run_extract(pdf_path, out_prefix, "docling", allow_empty=True)

        self.assertTrue(result["ok"])
        self.assertEqual(commands[0]["cmd"][0], "/tmp/docling-python")
        self.assertEqual(commands[0]["cmd"][1], str(ROOT / "scripts" / "extract_financial_metrics.py"))
        self.assertIn("--pdf", commands[0]["cmd"])
        self.assertNotIn("--pdf-dir", commands[0]["cmd"])
        self.assertEqual(commands[0]["cmd"][commands[0]["cmd"].index("--pdf") + 1], str(pdf_path))


class TestCompareDoclingAccuracyBenchmarkCorpus(unittest.TestCase):
    def test_collect_benchmark_corpus_excludes_nonfinancial_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_dir = Path(tmpdir)
            financial_pdf = pdf_dir / "2025-annual-report.pdf"
            appendix_pdf = pdf_dir / "2025-appendix-4e.pdf"
            presentation_pdf = pdf_dir / "2025-results-presentation.pdf"
            for path in (financial_pdf, appendix_pdf, presentation_pdf):
                path.write_bytes(b"%PDF-1.4")

            kinds = {
                str(financial_pdf): "canonical_report",
                str(appendix_pdf): "appendix_report",
                str(presentation_pdf): "other",
            }

            with mock.patch.object(
                COMPARE,
                "classify_document_source_kind",
                side_effect=lambda pdf: kinds[str(pdf)],
            ):
                corpus = COMPARE.collect_benchmark_corpus(pdf_dir)

        self.assertEqual(corpus["total_pdf_count"], 3)
        self.assertEqual(corpus["financial_documents_processed"], 2)
        self.assertEqual(corpus["nonfinancial_documents_skipped"], 1)
        self.assertEqual(
            [entry["document"] for entry in corpus["documents"]],
            [str(financial_pdf), str(appendix_pdf)],
        )
        self.assertEqual(len(corpus["documents_skipped"]), 1)
        self.assertEqual(corpus["documents_skipped"][0]["document"], str(presentation_pdf))
        self.assertEqual(corpus["documents_skipped"][0]["skip_reason"], "non_financial_document")

    def test_collect_benchmark_corpus_can_include_nonfinancial_documents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_dir = Path(tmpdir)
            financial_pdf = pdf_dir / "2025-annual-report.pdf"
            presentation_pdf = pdf_dir / "2025-results-presentation.pdf"
            for path in (financial_pdf, presentation_pdf):
                path.write_bytes(b"%PDF-1.4")

            kinds = {
                str(financial_pdf): "canonical_report",
                str(presentation_pdf): "other",
            }

            with mock.patch.object(
                COMPARE,
                "classify_document_source_kind",
                side_effect=lambda pdf: kinds[str(pdf)],
            ):
                corpus = COMPARE.collect_benchmark_corpus(pdf_dir, include_nonfinancial=True)

        self.assertEqual(corpus["total_pdf_count"], 2)
        self.assertEqual(corpus["financial_documents_processed"], 1)
        self.assertEqual(corpus["nonfinancial_documents_skipped"], 0)
        self.assertEqual(
            [entry["document"] for entry in corpus["documents"]],
            [str(financial_pdf), str(presentation_pdf)],
        )
        self.assertEqual(corpus["documents_skipped"], [])

    def test_filter_extraction_result_by_documents_keeps_only_selected_documents(self):
        allowed_document = "/tmp/financial.pdf"
        skipped_document = "/tmp/presentation.pdf"
        result = {
            "canonical_rows": [
                {"file": allowed_document, "metric": "revenue", "statement_period_end": "2025-06-30", "value": 100},
                {"file": skipped_document, "metric": "revenue", "statement_period_end": "2025-06-30", "value": 200},
            ],
            "document_diagnostics": [
                {"document": allowed_document, "fallback_triggered": False},
                {"document": skipped_document, "fallback_triggered": True},
            ],
            "ok": True,
        }

        filtered = COMPARE.filter_extraction_result_by_documents(result, {allowed_document})

        self.assertEqual(filtered["canonical_rows"], [result["canonical_rows"][0]])
        self.assertEqual(filtered["document_diagnostics"], [result["document_diagnostics"][0]])
        self.assertTrue(filtered["ok"])

    def test_compare_normalizes_comma_separators_before_comparison(self):
        rows_pdf = [
            {
                "metric": "revenue",
                "statement_period_end": "2025-06-30",
                "value": "1,234",
            }
        ]
        rows_docling = [
            {
                "metric": "revenue",
                "statement_period_end": "2025-06-30",
                "value": 1234,
            }
        ]

        result = COMPARE.compare(rows_pdf, rows_docling)
        self.assertEqual(result["agree"], 1)
        self.assertEqual(result["disagree"], 0)


class TestCompareDoclingAccuracyPerPdfBenchmark(unittest.TestCase):
    def test_benchmark_ticker_documents_runs_each_pdf_in_single_pdf_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ticker_dir = Path(tmpdir) / "BIG"
            ticker_dir.mkdir()
            benchmark_documents = []
            original_paths = []
            for name in ("alpha.pdf", "beta.pdf", "gamma.pdf"):
                pdf = ticker_dir / name
                pdf.write_bytes(b"%PDF-1.4")
                original_paths.append(str(pdf))
                benchmark_documents.append(
                    {
                        "ticker": "BIG",
                        "document": str(pdf),
                        "source_kind": "canonical_report",
                    }
                )

            calls = []

            def fake_run_extract(pdf_path, out_prefix, extractor, **kwargs):
                pdf_path = Path(pdf_path)
                calls.append(
                    {
                        "extractor": extractor,
                        "pdf_path": str(pdf_path),
                        "pdf_name": pdf_path.name,
                    }
                )
                return {
                    "ok": True,
                    "canonical_rows": [
                        {
                            "file": str(pdf_path),
                            "source_file": str(pdf_path),
                            "metric": f"{extractor}_metric",
                            "statement_period_end": "2025-06-30",
                            "value": 1,
                        }
                    ],
                    "document_diagnostics": [
                        {
                            "document": str(pdf_path),
                            "extractor_selected": extractor,
                        }
                    ],
                    "path": str(out_prefix / "canonical.json"),
                }

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = COMPARE.benchmark_ticker_documents(
                    "BIG",
                    benchmark_documents,
                    Path(tmpdir) / "out",
                    timeout_sec=30,
                    extract_runner=fake_run_extract,
                )

        self.assertEqual(len(calls), 6)
        self.assertEqual([call["pdf_path"] for call in calls[::2]], original_paths)
        self.assertEqual(
            [row["file"] for row in result["pdftotext_result"]["canonical_rows"]],
            original_paths,
        )
        self.assertEqual(
            [row["file"] for row in result["docling_result"]["canonical_rows"]],
            original_paths,
        )
        self.assertEqual(
            [entry["document"] for entry in result["pdftotext_result"]["document_diagnostics"]],
            original_paths,
        )
        self.assertEqual(
            [entry["document"] for entry in result["docling_result"]["document_diagnostics"]],
            original_paths,
        )
        self.assertEqual(
            [entry["document"] for entry in result["successful_documents"]],
            original_paths,
        )
        self.assertEqual(result["failed_documents"], [])
        progress_output = stdout.getvalue()
        self.assertIn("ticker=BIG pdf_index=1 total_pdfs=3", progress_output)
        self.assertIn("ticker=BIG pdf_index=3 total_pdfs=3", progress_output)

    def test_benchmark_ticker_documents_logs_and_skips_individual_pdf_failures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ticker_dir = Path(tmpdir) / "BIG"
            ticker_dir.mkdir()
            benchmark_documents = []
            original_paths = {}
            for name in ("alpha.pdf", "beta.pdf", "gamma.pdf"):
                pdf = ticker_dir / name
                pdf.write_bytes(b"%PDF-1.4")
                original_paths[name] = str(pdf)
                benchmark_documents.append(
                    {
                        "ticker": "BIG",
                        "document": str(pdf),
                        "source_kind": "canonical_report",
                    }
                )

            def fake_run_extract(pdf_path, out_prefix, extractor, **kwargs):
                pdf_path = Path(pdf_path)
                if pdf_path.name == "beta.pdf" and extractor == "docling":
                    return {
                        "ok": False,
                        "canonical_rows": [],
                        "document_diagnostics": [],
                        "returncode": 124,
                        "stderr": "timeout",
                        "path": str(out_prefix / "canonical.json"),
                    }
                return {
                    "ok": True,
                    "canonical_rows": [
                        {
                            "file": str(pdf_path),
                            "source_file": str(pdf_path),
                            "metric": "revenue",
                            "statement_period_end": "2025-06-30",
                            "value": 100,
                        }
                    ],
                    "document_diagnostics": [
                        {
                            "document": str(pdf_path),
                            "extractor_selected": extractor,
                        }
                    ],
                    "path": str(out_prefix / "canonical.json"),
                }

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = COMPARE.benchmark_ticker_documents(
                    "BIG",
                    benchmark_documents,
                    Path(tmpdir) / "out",
                    timeout_sec=30,
                    extract_runner=fake_run_extract,
                )

        self.assertEqual(
            [row["file"] for row in result["pdftotext_result"]["canonical_rows"]],
            [original_paths["alpha.pdf"], original_paths["gamma.pdf"]],
        )
        self.assertEqual(
            [row["file"] for row in result["docling_result"]["canonical_rows"]],
            [original_paths["alpha.pdf"], original_paths["gamma.pdf"]],
        )
        self.assertEqual(
            [entry["document"] for entry in result["successful_documents"]],
            [original_paths["alpha.pdf"], original_paths["gamma.pdf"]],
        )
        self.assertEqual(len(result["failed_documents"]), 1)
        self.assertEqual(result["failed_documents"][0]["document"], original_paths["beta.pdf"])
        self.assertEqual(result["failed_documents"][0]["extractor"], "docling")
        self.assertEqual(result["failed_documents"][0]["pdf_index"], 2)
        self.assertEqual(result["failed_documents"][0]["total_pdfs"], 3)
        self.assertIn("FAILED", stdout.getvalue())

    def test_main_tolerates_individual_pdf_failures_and_writes_failure_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs"
            ticker_dir = docs_dir / "BIG"
            ticker_dir.mkdir(parents=True)
            original_paths = {}
            for name in ("alpha.pdf", "beta.pdf", "gamma.pdf"):
                pdf = ticker_dir / name
                pdf.write_bytes(b"%PDF-1.4")
                original_paths[name] = str(pdf)

            def fake_run_extract(pdf_path, out_prefix, extractor, **kwargs):
                pdf_path = Path(pdf_path)
                if pdf_path.name == "beta.pdf" and extractor == "docling":
                    return {
                        "ok": False,
                        "canonical_rows": [],
                        "document_diagnostics": [],
                        "returncode": 124,
                        "stderr": "timeout",
                        "path": str(out_prefix / "canonical.json"),
                    }
                return {
                    "ok": True,
                    "canonical_rows": [
                        {
                            "file": str(pdf_path),
                            "source_file": str(pdf_path),
                            "metric": "revenue",
                            "statement_period_end": "2025-06-30",
                            "value": 100,
                        }
                    ],
                    "document_diagnostics": [
                        {
                            "document": str(pdf_path),
                            "extractor_selected": extractor,
                        }
                    ],
                    "path": str(out_prefix / "canonical.json"),
                }

            out_dir = Path(tmpdir) / "reports"
            pipeline_path = Path(tmpdir) / "pipeline_diagnostics.json"
            stdout = io.StringIO()
            with mock.patch.dict("os.environ", {"DOCILING_PYTHON": "/tmp/docling-python"}, clear=True), mock.patch.object(COMPARE, "DOCS", docs_dir), mock.patch.object(
                COMPARE,
                "classify_document_source_kind",
                return_value="canonical_report",
            ), mock.patch.object(COMPARE, "run_extract", side_effect=fake_run_extract), mock.patch.object(
                sys,
                "argv",
                [
                    "compare_docling_accuracy.py",
                    "--tickers",
                    "BIG",
                    "--out-dir",
                    str(out_dir),
                    "--max-workers",
                    "1",
                    "--pipeline-diagnostics-out",
                    str(pipeline_path),
                ],
            ), redirect_stdout(stdout):
                rc = COMPARE.main()

            report = json.loads((out_dir / "comparison_report.json").read_text(encoding="utf-8"))
            pipeline_exists = pipeline_path.exists()

        self.assertEqual(rc, 0)
        self.assertEqual(report["tickers"], ["BIG"])
        self.assertEqual(len(report["failed_documents"]), 1)
        self.assertEqual(report["failed_documents"][0]["document"], original_paths["beta.pdf"])
        self.assertEqual(report["failed_documents"][0]["extractor"], "docling")
        self.assertEqual(report["summary"]["total_agree"], 1)
        self.assertTrue(pipeline_exists)
        self.assertIn("[runtime] using python interpreter: /tmp/docling-python", stdout.getvalue())
        self.assertIn("failed_pdfs=1", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
