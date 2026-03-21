import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import pytest


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_PATH = SCRIPT_DIR / "section_capture_layer.py"
if not MODULE_PATH.exists():
    pytest.skip(
        "INCOMPLETE MIGRATION — section_capture_layer.py exists on main "
        "(commits 710fe968, af7f8e57) but was not merged into cloud/session-20260319. "
        "Merge main or cherry-pick those commits to restore section capture layer tests. "
        "See backend/tests/test_extraction_capability_guards.py for the tracking xfail.",
        allow_module_level=True,
    )
MOD = load_module(str(MODULE_PATH), "section_capture_layer")


class TestSectionCaptureLayer(unittest.TestCase):
    def test_backfill_missing_currency_prefers_file_hint(self):
        df = pd.DataFrame(
            [
                {"file": "/tmp/docs/BHP/financial_performance/demo_a.pdf", "metric": "revenue", "currency": "US$"},
                {"file": "/tmp/docs/BHP/financial_performance/demo_a.pdf", "metric": "ebit", "currency": ""},
                {"file": "/tmp/docs/BHP/financial_performance/demo_a.pdf", "metric": "net_income", "currency": "UNKNOWN"},
            ]
        )
        out, stats = MOD._backfill_missing_currency(df)
        self.assertEqual(int(stats["rows_filled_from_file_hint"]), 2)
        self.assertEqual(int(stats["rows_missing_after"]), 0)
        self.assertEqual(set(out["currency"].astype(str).tolist()), {"US$"})

    def test_backfill_missing_currency_falls_back_to_ticker_hint(self):
        df = pd.DataFrame(
            [
                {"file": "/tmp/docs/RIO/financial_performance/a.pdf", "metric": "revenue", "currency": "US$"},
                {"file": "/tmp/docs/RIO/financial_performance/b.pdf", "metric": "ebit", "currency": "US$"},
                {"file": "/tmp/docs/RIO/financial_performance/c.pdf", "metric": "net_income", "currency": "US$"},
                {"file": "/tmp/docs/RIO/financial_performance/d.pdf", "metric": "eps", "currency": "US$"},
                {"file": "/tmp/docs/RIO/financial_performance/e.pdf", "metric": "total_assets", "currency": "US$"},
                {"file": "/tmp/docs/RIO/financial_performance/target.pdf", "metric": "net_income", "currency": ""},
            ]
        )
        out, stats = MOD._backfill_missing_currency(df)
        target = out[out["file"].astype(str).str.endswith("/target.pdf")]
        self.assertEqual(int(stats["rows_filled_from_ticker_hint"]), 1)
        self.assertEqual(str(target.iloc[0]["currency"]), "US$")

    def test_merge_canonical_rows_filters_low_confidence_unmapped_and_missing_period(self):
        canonical_df = pd.DataFrame(
            [
                {
                    "file": "/tmp/demo.pdf",
                    "statement_period_end": "2024-06-30",
                    "metric": "revenue",
                    "metric_base": "revenue",
                    "metric_variant": "",
                    "balance_position": "",
                    "raw_value": "100",
                    "value": 100.0,
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                }
            ]
        )
        candidate_rows = [
            {
                "file": "/tmp/demo.pdf",
                "statement_period_end": "2024-06-30",
                "metric": "cashflow_unmapped",
                "metric_base": "cashflow_unmapped",
                "metric_variant": "",
                "balance_position": "",
                "raw_value": "48",
                "value": 48.0,
                "canonical_confidence_score": 4,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "statement_period_end": "2024-06-30",
                "metric": "operating_cash_flow",
                "metric_base": "operating_cash_flow",
                "metric_variant": "",
                "balance_position": "",
                "raw_value": "60",
                "value": 60.0,
                "canonical_confidence_score": 1,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "statement_period_end": "",
                "metric": "operating_cash_flow",
                "metric_base": "operating_cash_flow",
                "metric_variant": "",
                "balance_position": "",
                "raw_value": "61",
                "value": 61.0,
                "canonical_confidence_score": 4,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "statement_period_end": "2024-06-30",
                "metric": "operating_cash_flow",
                "metric_base": "operating_cash_flow",
                "metric_variant": "",
                "balance_position": "",
                "raw_value": "62",
                "value": 62.0,
                "canonical_confidence_score": 4,
                "inside_table": True,
            },
        ]

        merged = MOD._merge_canonical_rows(canonical_df, candidate_rows)
        metrics = set(merged["metric"].astype(str).str.lower().tolist())
        self.assertEqual(metrics, {"revenue", "operating_cash_flow"})
        self.assertEqual(len(merged), 2)

    def test_merge_canonical_rows_drops_ambiguous_cashflow_context_period_duplicate(self):
        canonical_df = pd.DataFrame(
            [
                {
                    "file": "/tmp/demo.pdf",
                    "statement_period_end": "2024-12-31",
                    "metric": "operating_cash_flow",
                    "metric_base": "operating_cash_flow",
                    "metric_variant": "",
                    "balance_position": "",
                    "raw_value": "149",
                    "value": 149.0,
                    "source_mode": "table_extract",
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                }
            ]
        )
        candidate_rows = [
            {
                "file": "/tmp/demo.pdf",
                "statement_period_end": "2023-12-31",
                "metric": "operating_cash_flow",
                "metric_base": "operating_cash_flow",
                "metric_variant": "",
                "balance_position": "",
                "raw_value": "149",
                "value": 149.0,
                "source_mode": "cashflow_context_line",
                "canonical_confidence_score": 4,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "statement_period_end": "2023-12-31",
                "metric": "operating_cash_flow",
                "metric_base": "operating_cash_flow",
                "metric_variant": "",
                "balance_position": "",
                "raw_value": "150",
                "value": 150.0,
                "source_mode": "cashflow_context_line",
                "canonical_confidence_score": 4,
                "inside_table": True,
            },
        ]

        merged = MOD._merge_canonical_rows(canonical_df, candidate_rows)
        ocf = merged[merged["metric"].astype(str).str.lower() == "operating_cash_flow"].copy()
        period_values = sorted(
            (str(r["statement_period_end"]), float(r["value"]))
            for r in ocf[["statement_period_end", "value"]].to_dict(orient="records")
        )
        self.assertEqual(period_values, [("2023-12-31", 150.0), ("2024-12-31", 149.0)])

    def test_section_index_detects_statement_pages_and_excludes_notes(self):
        prepared_pages = {
            1: [
                {"text": "Consolidated Statement of Comprehensive Income", "numeric_words": []},
                {"text": "Revenue", "numeric_words": []},
                {"text": "EBIT", "numeric_words": []},
            ],
            2: [
                {"text": "Consolidated Statement of Financial Position", "numeric_words": []},
                {"text": "Total assets", "numeric_words": []},
                {"text": "Total liabilities", "numeric_words": []},
            ],
            3: [
                {"text": "Consolidated Statement of Cash Flows", "numeric_words": []},
                {"text": "Operating activities", "numeric_words": []},
                {"text": "Financing activities", "numeric_words": []},
            ],
            4: [
                {"text": "Notes to the financial statements", "numeric_words": []},
                {"text": "Adjusted reconciliation", "numeric_words": []},
                {"text": "Statement of cash flows", "numeric_words": []},
            ],
        }

        index = MOD.build_section_index_for_pdf(Path("/tmp/demo.pdf"), prepared_pages)
        self.assertEqual(index["file_id"], "demo")
        self.assertEqual(index["sections"]["income_statement"]["pages"], [1])
        self.assertEqual(index["sections"]["balance_sheet"]["pages"], [2])
        self.assertEqual(index["sections"]["cash_flow"]["pages"], [3])
        self.assertNotIn(4, index["sections"]["cash_flow"]["pages"])

    def test_missing_sections_requires_full_income_core_for_cashflow(self):
        metrics = {"revenue", "ebit"}  # net_income missing, still income-signaled
        missing = MOD._missing_sections_for_period(metrics)
        self.assertNotIn("cash_flow", missing)

    def test_force_section_pass_adds_candidates_and_outputs_summary(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            pdf_dir = td_path / "pdfs"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = pdf_dir / "demo.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")

            canonical_path = td_path / "canonical.csv"
            pd.DataFrame(
                [
                    {
                        "file": str(pdf_path.resolve()),
                        "statement_period_end": "2024-06-30",
                        "metric": "revenue",
                        "value": 100.0,
                        "canonical_confidence_score": 3,
                        "integrity_score": 2,
                    },
                    {
                        "file": str(pdf_path.resolve()),
                        "statement_period_end": "2024-06-30",
                        "metric": "ebit",
                        "value": 20.0,
                        "canonical_confidence_score": 3,
                        "integrity_score": 2,
                    },
                    {
                        "file": str(pdf_path.resolve()),
                        "statement_period_end": "2024-06-30",
                        "metric": "net_income",
                        "value": 15.0,
                        "canonical_confidence_score": 3,
                        "integrity_score": 2,
                    },
                ]
            ).to_csv(canonical_path, index=False)

            prepared_pages = {
                2: [
                    {"text": "Consolidated Statement of Financial Position", "numeric_words": []},
                    {"text": "Total assets", "numeric_words": []},
                ],
                3: [
                    {"text": "Consolidated Statement of Cash Flows", "numeric_words": []},
                    {"text": "Operating activities", "numeric_words": []},
                ],
            }

            new_rows = [
                {
                    "file": str(pdf_path.resolve()),
                    "statement_period_end": "2024-06-30",
                    "metric": "total_assets",
                    "metric_base": "total_assets",
                    "value": 900.0,
                    "page_number": 2,
                    "statement_title": "Consolidated statement of financial position",
                    "table_header_text": "Total assets",
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                },
                {
                    "file": str(pdf_path.resolve()),
                    "statement_period_end": "2024-06-30",
                    "metric": "total_liabilities",
                    "metric_base": "total_liabilities",
                    "value": 500.0,
                    "page_number": 2,
                    "statement_title": "Consolidated statement of financial position",
                    "table_header_text": "Total liabilities",
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                },
                {
                    "file": str(pdf_path.resolve()),
                    "statement_period_end": "2024-06-30",
                    "metric": "total_equity",
                    "metric_base": "total_equity",
                    "value": 400.0,
                    "page_number": 2,
                    "statement_title": "Consolidated statement of financial position",
                    "table_header_text": "Total equity",
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                },
                {
                    "file": str(pdf_path.resolve()),
                    "statement_period_end": "2024-06-30",
                    "metric": "cash_and_equivalents",
                    "metric_base": "cash_and_equivalents",
                    "value": 80.0,
                    "page_number": 2,
                    "statement_title": "Consolidated statement of financial position",
                    "table_header_text": "Cash and cash equivalents",
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                },
                {
                    "file": str(pdf_path.resolve()),
                    "statement_period_end": "2024-06-30",
                    "metric": "total_debt",
                    "metric_base": "total_debt",
                    "value": 120.0,
                    "page_number": 2,
                    "statement_title": "Consolidated statement of financial position",
                    "table_header_text": "Total debt",
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                },
                {
                    "file": str(pdf_path.resolve()),
                    "statement_period_end": "2024-06-30",
                    "metric": "operating_cash_flow",
                    "metric_base": "operating_cash_flow",
                    "value": 60.0,
                    "page_number": 3,
                    "statement_title": "Consolidated statement of cash flows",
                    "table_header_text": "Operating activities",
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                },
                {
                    "file": str(pdf_path.resolve()),
                    "statement_period_end": "2024-06-30",
                    "metric": "capital_expenditure",
                    "metric_base": "capital_expenditure",
                    "value": 25.0,
                    "page_number": 3,
                    "statement_title": "Consolidated statement of cash flows",
                    "table_header_text": "Investing activities",
                    "canonical_confidence_score": 3,
                    "inside_table": True,
                },
            ]
            for rr in new_rows:
                rr["currency"] = "AUD"

            original_funcs = {
                "_prepare_bbox_pages": MOD.EXTRACT._prepare_bbox_pages,
                "classify_pdf_source_kind": MOD.EXTRACT.classify_pdf_source_kind,
                "segment_statement_blocks": MOD.EXTRACT.segment_statement_blocks,
                "extract_metrics_from_blocks": MOD.EXTRACT.extract_metrics_from_blocks,
                "split_rows_by_scope": MOD.EXTRACT.split_rows_by_scope,
                "resolve_canonical_conflicts": MOD.EXTRACT.resolve_canonical_conflicts,
                "apply_balance_sheet_identity_guard": MOD.EXTRACT.apply_balance_sheet_identity_guard,
                "dedupe": MOD.EXTRACT.dedupe,
            }
            try:
                MOD.EXTRACT._prepare_bbox_pages = lambda _pdf: prepared_pages
                MOD.EXTRACT.classify_pdf_source_kind = lambda _pdf: "consolidated"
                MOD.EXTRACT.segment_statement_blocks = (
                    lambda _pdf, source_kind=None, prepared_pages=None: [
                        {"title": "Consolidated statement of financial position", "context_text": "", "page_number": 2},
                        {"title": "Consolidated statement of cash flows", "context_text": "", "page_number": 3},
                    ]
                )
                MOD.EXTRACT.extract_metrics_from_blocks = (
                    lambda _pdf, _blocks, strict_metric_rows_only=True, prepared_pages=None: list(new_rows)
                )
                MOD.EXTRACT.split_rows_by_scope = lambda rows: {"canonical_rows": rows, "context_rows": []}
                MOD.EXTRACT.resolve_canonical_conflicts = lambda rows: (rows, [])
                MOD.EXTRACT.apply_balance_sheet_identity_guard = lambda rows: (rows, [])
                MOD.EXTRACT.dedupe = lambda rows: rows

                result = MOD.run_section_capture_layer(
                    pdf_dir=pdf_dir,
                    canonical_path=canonical_path,
                    out_dir=td_path,
                    force_section_pass=True,
                )
            finally:
                for name, fn in original_funcs.items():
                    setattr(MOD.EXTRACT, name, fn)

            self.assertTrue(result["section_pass_enabled"])
            self.assertGreaterEqual(int(result["candidate_rows_added"]), 1)
            self.assertTrue((td_path / "section_capture_improvement_summary.json").exists())
            self.assertTrue((td_path / "canonical_section_capture.csv").exists())

            merged = pd.read_csv(td_path / "canonical_section_capture.csv")
            metrics = set(merged["metric"].astype(str).str.lower().tolist())
            self.assertIn("total_assets", metrics)
            self.assertIn("operating_cash_flow", metrics)

            summary = json.loads((td_path / "section_capture_improvement_summary.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(int(summary["candidate_rows_added"]), 1)

    def test_auto_trigger_enables_section_pass_when_forensic_detects_structural_gap(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            pdf_dir = td_path / "pdfs"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = pdf_dir / "demo.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")

            canonical_path = td_path / "canonical.csv"
            pd.DataFrame(
                [
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2023-06-30", "metric": "revenue", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2023-06-30", "metric": "ebit", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2023-06-30", "metric": "net_income", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2023-12-31", "metric": "revenue", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2023-12-31", "metric": "ebit", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2023-12-31", "metric": "net_income", "value": 1.0},
                ]
            ).to_csv(canonical_path, index=False)

            prepared_pages = {
                2: [{"text": "Consolidated Statement of Financial Position", "numeric_words": []}],
                3: [{"text": "Consolidated Statement of Cash Flows", "numeric_words": []}],
            }

            original_funcs = {
                "_prepare_bbox_pages": MOD.EXTRACT._prepare_bbox_pages,
                "classify_pdf_source_kind": MOD.EXTRACT.classify_pdf_source_kind,
                "segment_statement_blocks": MOD.EXTRACT.segment_statement_blocks,
                "extract_metrics_from_blocks": MOD.EXTRACT.extract_metrics_from_blocks,
                "split_rows_by_scope": MOD.EXTRACT.split_rows_by_scope,
                "resolve_canonical_conflicts": MOD.EXTRACT.resolve_canonical_conflicts,
                "apply_balance_sheet_identity_guard": MOD.EXTRACT.apply_balance_sheet_identity_guard,
                "dedupe": MOD.EXTRACT.dedupe,
            }
            try:
                MOD.EXTRACT._prepare_bbox_pages = lambda _pdf: prepared_pages
                MOD.EXTRACT.classify_pdf_source_kind = lambda _pdf: "consolidated"
                MOD.EXTRACT.segment_statement_blocks = lambda _pdf, source_kind=None, prepared_pages=None: []
                MOD.EXTRACT.extract_metrics_from_blocks = (
                    lambda _pdf, _blocks, strict_metric_rows_only=True, prepared_pages=None: []
                )
                MOD.EXTRACT.split_rows_by_scope = lambda rows: {"canonical_rows": rows, "context_rows": []}
                MOD.EXTRACT.resolve_canonical_conflicts = lambda rows: (rows, [])
                MOD.EXTRACT.apply_balance_sheet_identity_guard = lambda rows: (rows, [])
                MOD.EXTRACT.dedupe = lambda rows: rows

                result = MOD.run_section_capture_layer(
                    pdf_dir=pdf_dir,
                    canonical_path=canonical_path,
                    out_dir=td_path,
                    force_section_pass=False,
                )
            finally:
                for name, fn in original_funcs.items():
                    setattr(MOD.EXTRACT, name, fn)

            self.assertTrue(result["section_pass_enabled"])
            self.assertTrue(result["section_pass_auto_triggered"])
            self.assertEqual(int(result["candidate_rows_added"]), 0)


if __name__ == "__main__":
    unittest.main()
