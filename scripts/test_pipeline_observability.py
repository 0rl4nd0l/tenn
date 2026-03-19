import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
EXTRACT = _load_module(str(ROOT / "scripts" / "extract_financial_metrics.py"), "extract_financial_metrics")
FALLBACK = _load_module(str(ROOT / "scripts" / "extractor_fallback_policy.py"), "extractor_fallback_policy")
TSR = _load_module(str(ROOT / "scripts" / "table_structure_reconciliation.py"), "table_structure_reconciliation")
COMPARE = _load_module(str(ROOT / "scripts" / "compare_docling_accuracy.py"), "compare_docling_accuracy")


class _FakeValues:
    def tolist(self):
        return [["Revenue", "100"]]


class _FakeDataFrame:
    columns = ["Metric", "FY24"]
    values = _FakeValues()


class TestPipelineObservability(unittest.TestCase):
    def _row(self, **overrides):
        row = {
            "file": "/tmp/test.pdf",
            "source_file": "/tmp/test.pdf",
            "metric": "revenue",
            "metric_base": "revenue",
            "value": 100.0,
            "value_type": "amount",
            "currency": "AUD",
            "statement_scope": "consolidated_statement",
            "statement_type": "consolidated_statement",
            "statement_title": "Statement of profit or loss",
            "statement_scope_header": "Statement of profit or loss",
            "statement_family": "income_statement",
            "row_label": "Revenue",
            "line": "Revenue",
            "inside_table": True,
        }
        row.update(overrides)
        return row

    def test_fallback_reason_populated_when_fallback_occurs(self):
        split = {
            "canonical_rows": [
                {
                    "metric": "revenue",
                    "metric_base": "revenue",
                    "value": 100.0,
                    "value_type": "amount",
                    "currency": "",
                }
            ]
        }

        decision = FALLBACK.evaluate_docling_fallback(split)

        self.assertTrue(decision["should_fallback"])
        self.assertEqual(decision["fallback_reason"], "currency_detection_failed")
        self.assertIn("currency_detection_failed", decision["reasons"])

    def test_split_rows_by_scope_returns_routing_summary(self):
        rows = [
            self._row(file="/tmp/no-table.pdf", source_file="/tmp/no-table.pdf", inside_table=False),
            self._row(
                file="/tmp/no-period.pdf",
                source_file="/tmp/no-period.pdf",
                statement_period_end="",
                period_end="",
            ),
        ]

        split = EXTRACT.split_rows_by_scope(rows)
        summary = split["routing_summary"]

        self.assertEqual(summary["context_rows"], 1)
        self.assertEqual(summary["rejected_rows"], 1)
        self.assertEqual(summary["rejection_reasons"]["missing_statement_period_end"], 1)
        self.assertEqual(summary["rejection_reasons"]["not_inside_table"], 1)

    def test_split_rows_by_scope_filters_low_quality_context_rows(self):
        rows = [
            self._row(
                file="/tmp/no-period.pdf",
                source_file="/tmp/no-period.pdf",
                statement_period_end="",
                period_end="",
                value=100.0,
                source_mode="docling_table",
            ),
            self._row(
                file="/tmp/zero.pdf",
                source_file="/tmp/zero.pdf",
                statement_scope="other",
                value=0.0,
                statement_period_end="2025-06-30",
                period_end="2025-06-30",
                source_mode="docling_table",
            ),
        ]

        split = EXTRACT.split_rows_by_scope(rows, docling_row_count_before_filtering=2)

        self.assertEqual(split["routing_summary"]["context_rows"], 0)
        self.assertEqual(split["context_rows"], [])

    def test_tsr_tables_processed_increments(self):
        _, meta = TSR.reconcile_table_dataframe(_FakeDataFrame())

        self.assertEqual(meta["tsr_tables_processed"], 1)

    def test_pipeline_diagnostics_include_new_fields(self):
        document = "financial-engine_v2/data/asx/docs/ABC/financial_performance/demo.pdf"
        pdf_result = {
            "canonical_rows": [
                {
                    "file": document,
                    "metric": "revenue",
                    "statement_period_end": "2025-06-30",
                    "value": 100.0,
                }
            ],
            "document_diagnostics": [],
        }
        docling_result = {
            "canonical_rows": [
                {
                    "file": document,
                    "metric": "revenue",
                    "statement_period_end": "2025-06-30",
                    "value": 100.0,
                }
            ],
            "document_diagnostics": [
                {
                    "ticker": "ABC",
                    "document": document,
                    "extractor_selected": "pdftotext",
                    "fallback_triggered": True,
                    "fallback_suppressed": False,
                    "fallback_suppression_reason": None,
                    "document_classifier": {
                        "is_financial": True,
                        "document_type": "financial_report",
                    },
                    "fallback_reason": "critical_metrics_missing",
                    "docling_row_count_before_filtering": 7,
                    "context_rows": 2,
                    "rejected_rows": 1,
                    "rejection_reasons": {
                        "missing_statement_period_end": 2,
                        "not_inside_table": 1,
                    },
                    "tsr_tables_processed": 3,
                    "reconciliation_repairs": 1,
                    "tsr_duplicate_rows_demoted": 2,
                    "consistency_failures": 0,
                    "normalization_corrections": 4,
                }
            ],
        }

        benchmark_documents = [
            {
                "ticker": "ABC",
                "document": document,
                "source_kind": "canonical_report",
            }
        ]
        documents = COMPARE.build_pipeline_documents(
            "ABC",
            pdf_result,
            docling_result,
            benchmark_documents=benchmark_documents,
        )
        self.assertEqual(len(documents), 1)
        record = documents[0]
        self.assertEqual(record["source_kind"], "canonical_report")
        self.assertEqual(
            record["document_classifier"],
            {
                "is_financial": True,
                "document_type": "financial_report",
            },
        )
        self.assertEqual(record["docling_row_count_before_filtering"], 7)
        self.assertEqual(record["fallback_reason"], "critical_metrics_missing")
        self.assertFalse(record["fallback_suppressed"])
        self.assertIsNone(record["fallback_suppression_reason"])
        self.assertEqual(record["context_rows"], 2)
        self.assertEqual(record["rejected_rows"], 1)
        self.assertEqual(record["tsr_tables_processed"], 3)
        self.assertEqual(record["diagnostics"]["tsr_duplicate_rows_demoted"], 2)
        self.assertEqual(record["diagnostics"]["failure_type"], "partial")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "pipeline_diagnostics.json"
            payload = COMPARE.write_pipeline_diagnostics(
                documents,
                out_path,
                documents_skipped=[
                    {
                        "ticker": "ABC",
                        "document": "financial-engine_v2/data/asx/docs/ABC/financial_performance/demo-presentation.pdf",
                        "source_kind": "other",
                        "skip_reason": "non_financial_document",
                    }
                ],
                financial_documents_processed=1,
                nonfinancial_documents_skipped=1,
            )
            self.assertTrue(out_path.exists())
            self.assertEqual(payload["summary"]["fallback_rate"], 1.0)
            self.assertEqual(payload["summary"]["financial_documents_processed"], 1)
            self.assertEqual(payload["summary"]["nonfinancial_documents_skipped"], 1)
            self.assertIn("docling_row_count_before_filtering", payload["documents"][0])
            self.assertIn("document_classifier", payload["documents"][0])
            self.assertIn("fallback_reason", payload["documents"][0])
            self.assertIn("fallback_suppressed", payload["documents"][0])
            self.assertIn("fallback_suppression_reason", payload["documents"][0])
            self.assertIn("context_rows", payload["documents"][0])
            self.assertIn("rejected_rows", payload["documents"][0])
            self.assertIn("rejection_reasons", payload["documents"][0])
            self.assertIn("tsr_tables_processed", payload["documents"][0])
            self.assertEqual(payload["documents_skipped"][0]["skip_reason"], "non_financial_document")

    def test_pipeline_diagnostics_summary_uses_written_document_population(self):
        documents = [
            {
                "ticker": "ABC",
                "document": "financial-engine_v2/data/asx/docs/ABC/financial_performance/demo.pdf",
                "fallback_triggered": False,
                "accuracy": {"docling_only": 0, "pdftotext_only": 0},
                "diagnostics": {"consistency_failures": 0, "reconciliation_repairs": 0},
            }
        ]

        payload = COMPARE.build_pipeline_diagnostics_payload(
            documents,
            documents_skipped=[{"document": "skip.pdf", "skip_reason": "non_financial_document"}],
            financial_documents_processed=99,
            nonfinancial_documents_skipped=42,
        )

        self.assertEqual(payload["summary"]["financial_documents_processed"], len(documents))
        self.assertEqual(payload["summary"]["nonfinancial_documents_skipped"], 1)

    def test_write_pipeline_diagnostics_rejects_summary_mismatch(self):
        bad_payload = {
            "documents": [{"document": "a.pdf"}],
            "documents_skipped": [],
            "summary": {
                "agreement_rate": 0.0,
                "fallback_rate": 0.0,
                "consistency_failure_rate": 0.0,
                "reconciliation_rate": 0.0,
                "financial_documents_processed": 99,
                "nonfinancial_documents_skipped": 0,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(
            COMPARE,
            "build_pipeline_diagnostics_payload",
            return_value=bad_payload,
        ):
            out_path = Path(tmpdir) / "pipeline_diagnostics.json"
            with self.assertRaisesRegex(RuntimeError, "pipeline diagnostics summary mismatch"):
                COMPARE.write_pipeline_diagnostics([], out_path)
            self.assertFalse(out_path.exists())


if __name__ == "__main__":
    unittest.main()
