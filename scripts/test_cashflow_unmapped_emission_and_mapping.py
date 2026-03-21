import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

import pytest


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_PATH = SCRIPT_DIR / "cashflow_layout_adapter.py"
if not MODULE_PATH.exists():
    pytest.skip(
        "INCOMPLETE MIGRATION — cashflow_layout_adapter.py exists on main "
        "(commits 710fe968, af7f8e57) but was not merged into cloud/session-20260319. "
        "Merge main or cherry-pick those commits to restore unmapped emission tests. "
        "See backend/tests/test_extraction_capability_guards.py for the tracking xfail.",
        allow_module_level=True,
    )
CF_ADAPTER = load_module(str(MODULE_PATH), "cashflow_layout_adapter_unmapped")


class TestCashflowUnmappedEmissionAndMapping(unittest.TestCase):
    def test_unmapped_numeric_rows_emitted_and_minimal_mapping_applied(self):
        rows_raw = [
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Purchases of property, plant and equipment",
                "line": "(1,250)",
                "raw_value": "(1,250)",
                "value": -1250.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Investing activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Cash generated from operations",
                "line": "2,300",
                "raw_value": "2,300",
                "value": 2300.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Operating activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Additions to property, plant and equipment",
                "line": "(2,000)",
                "raw_value": "(2,000)",
                "value": -2000.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Investing activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Capital expenditure",
                "line": "(300)",
                "raw_value": "(300)",
                "value": -300.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Investing activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Capital expenditures",
                "line": "(325)",
                "raw_value": "(325)",
                "value": -325.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Investing activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Impairments of property, plant and equipment",
                "line": "(111)",
                "raw_value": "(111)",
                "value": -111.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Investing activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Total cash and cash equivalents",
                "line": "900",
                "raw_value": "900",
                "value": 900.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Cash and cash equivalents",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Reconciliation of net debt",
                "line": "77",
                "raw_value": "77",
                "value": 77.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Reconciliation",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
        ]

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow", "page_start": 9, "block_id": "b1"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: list(rows_raw),
            split_rows_by_scope=lambda rows: {"canonical_rows": rows, "context_rows": [], "rejected_rows": []},
            dedupe=lambda rows: rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )

        rows, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={9: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={9},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda text: "reconciliation" in str(text).lower() or "notes to the financial statements" in str(text).lower(),
        )

        metrics = [str(r.get("metric", "")).strip().lower() for r in rows]
        self.assertIn("capital_expenditure", metrics)
        self.assertIn("operating_cash_flow", metrics)
        self.assertIn("cashflow_unmapped", metrics)
        self.assertNotIn("reconciliation of net debt", "\n".join(str(r.get("row_label", "")) for r in rows).lower())

        # Guard: total cash line should not be remapped to capex/ocf.
        total_cash_rows = [r for r in rows if "total cash and cash equivalents" in str(r.get("row_label", "")).lower()]
        self.assertEqual(len(total_cash_rows), 1)
        self.assertEqual(str(total_cash_rows[0].get("metric", "")).lower(), "cashflow_unmapped")

        impairment_rows = [r for r in rows if "impairments of property, plant and equipment" in str(r.get("row_label", "")).lower()]
        self.assertEqual(len(impairment_rows), 1)
        self.assertEqual(str(impairment_rows[0].get("metric", "")).lower(), "cashflow_unmapped")

        capex_labels = [
            "purchases of property, plant and equipment",
            "additions to property, plant and equipment",
            "capital expenditure",
            "capital expenditures",
        ]
        for label in capex_labels:
            matched = [r for r in rows if label in str(r.get("row_label", "")).lower()]
            self.assertGreaterEqual(len(matched), 1)
            self.assertTrue(
                any(str(r.get("metric", "")).lower() == "capital_expenditure" for r in matched)
            )
            self.assertTrue(
                any(str(r.get("mapping_source", "")).strip() == "cashflow_phrase_map_v2" for r in matched)
            )

        self.assertGreaterEqual(int(stats.get("rows_emitted_unmapped_numeric", 0)), 1)
        self.assertGreaterEqual(int(stats.get("rows_mapped_to_capex", 0)), 1)
        self.assertGreaterEqual(int(stats.get("rows_mapped_to_capex_v2", 0)), 4)
        self.assertGreaterEqual(int(stats.get("rows_mapped_to_ocf", 0)), 1)

    def test_multicolumn_cashflow_row_uses_rightmost_numeric_token(self):
        rows_raw = [
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Purchases of property, plant and equipment",
                "line": "Purchases of property, plant and equipment (1,250) (900)",
                "raw_value": "",
                "value": None,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "",
                "table_header_text": "Current year Prior year",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
        ]
        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow", "page_start": 9, "block_id": "b1"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: list(rows_raw),
            split_rows_by_scope=lambda rows: {"canonical_rows": rows, "context_rows": [], "rejected_rows": []},
            dedupe=lambda rows: rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )
        rows, _stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={9: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={9},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda text: False,
        )
        self.assertEqual(len(rows), 1)
        rr = rows[0]
        self.assertEqual(str(rr.get("metric", "")).lower(), "capital_expenditure")
        self.assertEqual(str(rr.get("raw_value", "")).strip(), "(900)")
        self.assertEqual(float(rr.get("value", 0.0)), -900.0)

    def test_capex_label_value_next_row_stitching(self):
        rows_raw = [
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Purchases of property, plant and equipment",
                "line": "Purchases of property, plant and equipment",
                "raw_value": "",
                "value": None,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Investing activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/demo.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "",
                "line": "(1,234)",
                "raw_value": "(1,234)",
                "value": -1234.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Investing activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
        ]
        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow", "page_start": 9, "block_id": "b1"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: list(rows_raw),
            split_rows_by_scope=lambda rows: {"canonical_rows": rows, "context_rows": [], "rejected_rows": []},
            dedupe=lambda rows: rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )
        rows, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={9: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={9},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda _text: False,
        )
        self.assertEqual(int(stats.get("capex_rows_stitched", 0)), 1)
        self.assertEqual(len(rows), 1)
        rr = rows[0]
        self.assertEqual(str(rr.get("metric", "")).lower(), "capital_expenditure")
        self.assertEqual(str(rr.get("raw_value", "")).strip(), "(1,234)")
        self.assertEqual(float(rr.get("value", 0.0)), -1234.0)


if __name__ == "__main__":
    unittest.main()
