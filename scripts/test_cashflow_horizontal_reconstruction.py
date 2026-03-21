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
        "Merge main or cherry-pick those commits to restore horizontal reconstruction. "
        "See backend/tests/test_extraction_capability_guards.py for the tracking xfail.",
        allow_module_level=True,
    )
CF_ADAPTER = load_module(str(MODULE_PATH), "cashflow_layout_adapter_hrecon")


class TestCashflowHorizontalReconstruction(unittest.TestCase):
    def _extract_mod(self, rows):
        return SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {
                    "title": "Consolidated Statement of Cash Flows",
                    "context_text": "",
                    "statement_family": "cash_flow",
                    "page_start": 9,
                    "block_id": "b1",
                }
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: list(rows),
            split_rows_by_scope=lambda rs: {"canonical_rows": rs, "context_rows": [], "rejected_rows": []},
            dedupe=lambda rs: rs,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )

    def test_reconstructs_capex_label_followed_by_numeric_row(self):
        rows = [
            {
                "file": "/tmp/2024-annual-report.pdf",
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
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/2024-annual-report.pdf",
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
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
        ]
        extract_mod = self._extract_mod(rows)
        out, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/2024-annual-report.pdf"),
            source_kind="annual_report",
            prepared_pages={9: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={9},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda txt: "notes to the financial statements" in str(txt).lower(),
        )
        self.assertEqual(int(stats.get("capex_rows_reconstructed", 0)), 1)
        self.assertEqual(int(stats.get("capex_rows_consumed_following_lines", 0)), 1)
        self.assertEqual(len(out), 1)
        self.assertEqual(str(out[0].get("metric", "")).lower(), "capital_expenditure")
        self.assertEqual(str(out[0].get("numeric_parse_reason", "")), "horizontal_table_reconstruction")
        self.assertEqual(float(out[0].get("value", 0.0)), -1234.0)

    def test_does_not_reconstruct_when_following_row_is_notes_heading(self):
        rows = [
            {
                "file": "/tmp/2024-annual-report.pdf",
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
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/2024-annual-report.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Notes to the financial statements",
                "line": "Notes to the financial statements (1,234)",
                "raw_value": "(1,234)",
                "value": -1234.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Notes",
                "statement_title": "Notes to the financial statements",
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
        ]
        extract_mod = self._extract_mod(rows)
        out, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/2024-annual-report.pdf"),
            source_kind="annual_report",
            prepared_pages={9: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={9},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda txt: "notes to the financial statements" in str(txt).lower(),
        )
        self.assertEqual(int(stats.get("capex_rows_reconstructed", 0)), 0)
        self.assertTrue(all(str(r.get("numeric_parse_reason", "")) != "horizontal_table_reconstruction" for r in out))

    def test_multitoken_reconstruction_uses_period_selector_else_rightmost(self):
        rows = [
            {
                "file": "/tmp/2024-half-yearly-report-and-accounts.pdf",
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
                "statement_period": "Previous quarter",
                "period": "Previous quarter",
                "statement_period_end": "",
                "table_header_text": "Current quarter Previous quarter",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/2024-half-yearly-report-and-accounts.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "",
                "line": "(1,500)",
                "raw_value": "(1,500)",
                "value": -1500.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Previous quarter",
                "period": "Previous quarter",
                "statement_period_end": "",
                "table_header_text": "Current quarter Previous quarter",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/2024-half-yearly-report-and-accounts.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "",
                "line": "(900)",
                "raw_value": "(900)",
                "value": -900.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Previous quarter",
                "period": "Previous quarter",
                "statement_period_end": "",
                "table_header_text": "Current quarter Previous quarter",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
        ]
        extract_mod = self._extract_mod(rows)
        out, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/2024-half-yearly-report-and-accounts.pdf"),
            source_kind="half_year",
            prepared_pages={9: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={9},
            missing_periods=set(),
            exclusion_fn=lambda _txt: False,
        )
        self.assertEqual(int(stats.get("capex_rows_reconstructed", 0)), 1)
        self.assertEqual(int(stats.get("capex_rows_consumed_following_lines", 0)), 2)
        self.assertEqual(len(out), 1)
        # Previous quarter should pick second token in sequence.
        self.assertEqual(str(out[0].get("raw_value", "")).strip(), "(900)")

    def test_non_capex_row_does_not_reconstruct(self):
        rows = [
            {
                "file": "/tmp/2024-annual-report.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "Payments to suppliers and employees",
                "line": "Payments to suppliers and employees",
                "raw_value": "",
                "value": None,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Operating activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
            {
                "file": "/tmp/2024-annual-report.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "",
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
                "table_header_text": "Operating activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "b1",
                "page_number": 9,
                "table_page": 9,
                "inside_table": True,
            },
        ]
        extract_mod = self._extract_mod(rows)
        out, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/2024-annual-report.pdf"),
            source_kind="annual_report",
            prepared_pages={9: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={9},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda _txt: False,
        )
        self.assertEqual(int(stats.get("capex_rows_reconstructed", 0)), 0)
        self.assertTrue(all(str(r.get("numeric_parse_reason", "")) != "horizontal_table_reconstruction" for r in out))


if __name__ == "__main__":
    unittest.main()
