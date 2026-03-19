import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
EXTRACT = load_module(str(ROOT / "scripts" / "extract_financial_metrics.py"), "extract_financial_metrics")


def _base_row(pdf_path: Path) -> dict:
    return {
        "file": str(pdf_path),
        "source_file": str(pdf_path),
        "metric": "revenue",
        "metric_base": "revenue",
        "metric_variant": "",
        "value_type": "amount",
        "value": 123.0,
        "raw_value": "123",
        "currency": "AUD",
        "period": "FY2025",
        "period_scope": "flow",
        "period_type": "annual",
        "reporting_cadence": "annual",
        "reporting_period_months": 12,
        "statement_period_end": "2025-06-30",
        "period_end_date": "2025-06-30",
        "statement_type": "income_statement",
        "statement_scope": "income_statement",
        "statement_family": "income_statement",
        "row_label": "Revenue",
        "line": "Revenue 123",
        "line_no": 1,
        "inside_table": True,
        "canonical_tier": "strict",
    }


def _fake_extract_table_metrics(pdf_path: Path, **kwargs):
    row = _base_row(pdf_path)
    return [], [], EXTRACT.build_split_result([row], [], [])


def _mark_primary(rows):
    for row in rows:
        row["primary_metric_value"] = True


def _build_argv(output_dir: Path, input_args: list[str]) -> list[str]:
    return [
        "extract_financial_metrics.py",
        *input_args,
        "--out-json",
        str(output_dir / "canonical.json"),
        "--out-csv",
        str(output_dir / "canonical.csv"),
        "--out-all-variants-json",
        str(output_dir / "all_variants.json"),
        "--out-primary-csv",
        str(output_dir / "primary.csv"),
        "--out-primary-json",
        str(output_dir / "primary.json"),
        "--out-all-datapoints-json",
        str(output_dir / "all_datapoints.json"),
        "--out-coverage-enhanced-json",
        str(output_dir / "coverage_enhanced.json"),
        "--out-coverage-backfill-audit-json",
        str(output_dir / "coverage_backfill_audit.json"),
        "--out-context-csv",
        str(output_dir / "context.csv"),
        "--out-context-json",
        str(output_dir / "context.json"),
        "--out-rejected-json",
        str(output_dir / "rejected.json"),
        "--out-blocks-json",
        str(output_dir / "blocks.json"),
        "--out-high-csv",
        str(output_dir / "high.csv"),
        "--out-high-json",
        str(output_dir / "high.json"),
        "--financial-gates-report",
        str(output_dir / "financial_gates.json"),
        "--coverage-gates-report",
        str(output_dir / "coverage_gates.json"),
        "--coverage-enhanced-gates-report",
        str(output_dir / "coverage_enhanced_gates.json"),
        "--no-sqlite",
        "--no-enforce-financial-gates",
        "--no-enforce-coverage-gates",
    ]


class TestSinglePdfExtraction(unittest.TestCase):
    def test_directory_mode_matches_single_pdf_mode_for_canonical_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir) / "docs" / "AAA"
            docs_dir.mkdir(parents=True)
            pdf_path = docs_dir / "annual-report.pdf"
            pdf_path.write_bytes(b"%PDF-1.4")

            def run_once(output_dir: Path, input_args: list[str], *, patch_find_pdfs: bool) -> tuple[list[dict], str]:
                with ExitStack() as stack:
                    stack.enter_context(mock.patch.object(EXTRACT.shutil, "which", return_value="/usr/bin/pdftotext"))
                    stack.enter_context(mock.patch.object(EXTRACT, "classify_pdf_source_kind", return_value="canonical_report"))
                    stack.enter_context(
                        mock.patch.object(
                            EXTRACT,
                            "classify_document",
                            return_value={"is_financial": True, "document_type": "annual_report"},
                        )
                    )
                    stack.enter_context(mock.patch.object(EXTRACT, "extract_table_metrics", side_effect=_fake_extract_table_metrics))
                    stack.enter_context(mock.patch.object(EXTRACT, "extract_pdf_text", return_value=""))
                    stack.enter_context(mock.patch.object(EXTRACT, "normalize_metric_rows", side_effect=lambda rows: None))
                    stack.enter_context(
                        mock.patch.object(EXTRACT, "resolve_duplicate_metrics", side_effect=lambda rows: (rows, [], {}))
                    )
                    stack.enter_context(
                        mock.patch.object(EXTRACT, "resolve_canonical_conflicts", side_effect=lambda rows: (rows, []))
                    )
                    stack.enter_context(mock.patch.object(EXTRACT, "annotate_period_metadata", side_effect=lambda rows: None))
                    stack.enter_context(mock.patch.object(EXTRACT, "annotate_integrity_metadata", side_effect=lambda rows: None))
                    stack.enter_context(mock.patch.object(EXTRACT, "mark_primary_metric_rows", side_effect=_mark_primary))
                    stack.enter_context(
                        mock.patch.object(
                            EXTRACT,
                            "build_coverage_enhanced_rows",
                            side_effect=lambda primary_rows, rows, context_rows: (list(primary_rows), []),
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(
                            EXTRACT,
                            "build_all_datapoints_rows",
                            side_effect=lambda primary_rows, rows, context_rows, rejected_rows: list(rows),
                        )
                    )
                    stack.enter_context(mock.patch.object(EXTRACT, "score_confidence", return_value=0.95))
                    stack.enter_context(
                        mock.patch.object(
                            EXTRACT,
                            "build_financial_metrics_gate_report",
                            return_value={
                                "gate_pass": True,
                                "duplicates": 0,
                                "conflicts": 0,
                                "empty_currency": 0,
                                "failed_gates": [],
                            },
                        )
                    )
                    stack.enter_context(
                        mock.patch.object(
                            EXTRACT,
                            "build_financial_coverage_gate_report",
                            return_value={"gate_pass": True, "checks_failed": 0, "checks_total": 0},
                        )
                    )
                    if patch_find_pdfs:
                        stack.enter_context(
                            mock.patch.object(
                                EXTRACT,
                                "find_pdfs",
                                side_effect=AssertionError("single-pdf mode should not scan directories"),
                            )
                        )
                    argv = _build_argv(output_dir, input_args)
                    stack.enter_context(mock.patch.object(sys, "argv", argv))
                    rc = EXTRACT.main()

                self.assertEqual(rc, 0)
                canonical_json = json.loads((output_dir / "canonical.json").read_text(encoding="utf-8"))
                canonical_csv = (output_dir / "canonical.csv").read_text(encoding="utf-8")
                return canonical_json, canonical_csv

            dir_output = Path(tmpdir) / "dir"
            single_output = Path(tmpdir) / "single"
            dir_json, dir_csv = run_once(dir_output, ["--pdf-dir", str(docs_dir)], patch_find_pdfs=False)
            single_json, single_csv = run_once(single_output, ["--pdf", str(pdf_path)], patch_find_pdfs=True)

        self.assertEqual(dir_json, single_json)
        self.assertEqual(dir_csv, single_csv)


if __name__ == "__main__":
    unittest.main()
