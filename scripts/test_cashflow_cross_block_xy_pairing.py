import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
CF_ADAPTER = load_module(str(ROOT / "cashflow_layout_adapter.py"), "cashflow_layout_adapter_xy_pair")


class TestCashflowCrossBlockXyPairing(unittest.TestCase):
    def _extract_mod(self, rows):
        return SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {
                    "title": "Consolidated Statement of Cash Flows",
                    "context_text": "",
                    "statement_family": "cash_flow",
                    "page_start": 12,
                    "block_id": "blk-main",
                }
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: list(rows),
            split_rows_by_scope=lambda rs: {"canonical_rows": rs, "context_rows": [], "rejected_rows": []},
            dedupe=lambda rs: rs,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )

    def test_pairs_capex_label_with_numeric_row_in_other_block(self):
        rows = [
            {
                "file": "/tmp/bhp-annual-report.pdf",
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
                "statement_period_end": "2024-06-30",
                "table_header_text": "Statement of cash flows",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "blk-label",
                "page_number": 12,
                "table_page": 12,
                "row_bbox": [40.0, 100.0, 280.0, 110.0],
            },
            {
                "file": "/tmp/bhp-annual-report.pdf",
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
                "statement_period_end": "2024-06-30",
                "table_header_text": "Statement of cash flows",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "blk-values",
                "page_number": 12,
                "table_page": 12,
                "row_bbox": [430.0, 101.0, 500.0, 111.0],
            },
        ]
        extract_mod = self._extract_mod(rows)
        out, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/bhp-annual-report.pdf"),
            source_kind="annual_report",
            prepared_pages={12: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={12},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda txt: "notes to the financial statements" in str(txt).lower(),
        )
        self.assertEqual(int(stats.get("capex_rows_xy_paired", 0)), 1)
        self.assertGreaterEqual(int(stats.get("capex_xy_pair_attempt_count", 0)), 1)
        self.assertEqual(len(out), 1)
        self.assertEqual(str(out[0].get("numeric_parse_reason", "")), "cross_block_xy_pairing")
        self.assertEqual(str(out[0].get("xy_pair_success", "")), "1")
        self.assertEqual(str(out[0].get("metric", "")), "capital_expenditure")
        self.assertEqual(float(out[0].get("value", 0.0)), -1234.0)

    def test_ignores_notes_or_far_rows(self):
        rows = [
            {
                "file": "/tmp/bhp-annual-report.pdf",
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
                "statement_period_end": "2024-06-30",
                "table_header_text": "Statement of cash flows",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "blk-label",
                "page_number": 12,
                "table_page": 12,
                "row_bbox": [40.0, 100.0, 280.0, 110.0],
            },
            {
                "file": "/tmp/bhp-annual-report.pdf",
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
                "statement_period_end": "2024-06-30",
                "table_header_text": "Notes",
                "statement_title": "Notes to the financial statements",
                "block_id": "blk-notes",
                "page_number": 12,
                "table_page": 12,
                "row_bbox": [430.0, 101.0, 500.0, 111.0],
            },
            {
                "file": "/tmp/bhp-annual-report.pdf",
                "metric": "",
                "metric_base": "",
                "row_label": "",
                "line": "(9,999)",
                "raw_value": "(9,999)",
                "value": -9999.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Statement of cash flows",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "blk-far",
                "page_number": 12,
                "table_page": 12,
                "row_bbox": [430.0, 140.0, 500.0, 150.0],
            },
        ]
        extract_mod = self._extract_mod(rows)
        out, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/bhp-annual-report.pdf"),
            source_kind="annual_report",
            prepared_pages={12: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={12},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda txt: "notes to the financial statements" in str(txt).lower(),
        )
        self.assertEqual(int(stats.get("capex_rows_xy_paired", 0)), 0)
        self.assertEqual(int(stats.get("capex_rows_reconstructed", 0)), 0)
        self.assertTrue(all(str(r.get("numeric_parse_reason", "")) != "cross_block_xy_pairing" for r in out))
        self.assertTrue(all(str(r.get("metric", "")).lower() != "capital_expenditure" for r in out))


if __name__ == "__main__":
    unittest.main()
