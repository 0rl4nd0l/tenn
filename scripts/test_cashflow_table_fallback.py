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
ADAPTER_PATH = SCRIPT_DIR / "cashflow_layout_adapter.py"
TABLE_FB_PATH = SCRIPT_DIR / "cashflow_table_fallback.py"
if not ADAPTER_PATH.exists() or not TABLE_FB_PATH.exists():
    pytest.skip(
        "INCOMPLETE MIGRATION — cashflow_layout_adapter.py and cashflow_table_fallback.py "
        "exist on main (commits 710fe968, af7f8e57) but were not merged into "
        "cloud/session-20260319. Merge main or cherry-pick those commits to restore "
        "camelot-backed table fallback tests. "
        "See backend/tests/test_extraction_capability_guards.py for the tracking xfail.",
        allow_module_level=True,
    )
CF_ADAPTER = load_module(str(ADAPTER_PATH), "cashflow_layout_adapter_table_fallback")
TABLE_FB = load_module(str(TABLE_FB_PATH), "cashflow_table_fallback_mod")


class FakeRow:
    def __init__(self, values):
        self.values = values


class FakeDF:
    def __init__(self, rows):
        self._rows = rows

    def iterrows(self):
        for idx, values in enumerate(self._rows):
            yield idx, FakeRow(values)


class FakeTable:
    def __init__(self, rows):
        self.df = FakeDF(rows)


class TestCashflowTableFallback(unittest.TestCase):
    def test_extract_rows_with_camelot_parses_numeric_tokens(self):
        original = TABLE_FB._read_tables_lattice
        try:
            TABLE_FB._read_tables_lattice = lambda _pdf, _page: (
                [FakeTable([["Purchases of property, plant and equipment", "(1,234)", "(1,001)"]])],
                {},
            )
            rows, stats = TABLE_FB.extract_cashflow_table_rows_with_camelot_with_stats("/tmp/a.pdf", 10)
        finally:
            TABLE_FB._read_tables_lattice = original

        self.assertEqual(int(stats.get("tables_found", 0)), 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["raw_label"], "Purchases of property, plant and equipment")
        self.assertEqual(rows[0]["numeric_tokens"], ["(1,234)", "(1,001)"])

    def test_extract_rows_no_tables(self):
        original = TABLE_FB._read_tables_lattice
        try:
            TABLE_FB._read_tables_lattice = lambda _pdf, _page: ([], {})
            rows, stats = TABLE_FB.extract_cashflow_table_rows_with_camelot_with_stats("/tmp/a.pdf", 10)
        finally:
            TABLE_FB._read_tables_lattice = original

        self.assertEqual(rows, [])
        self.assertEqual(int(stats.get("tables_found", 0)), 0)

    def _extract_mod(self, rows, *, context_text=""):
        return SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {
                    "title": "Consolidated Statement of Cash Flows",
                    "context_text": context_text,
                    "statement_family": "cash_flow",
                    "page_start": 8,
                    "block_id": "b1",
                }
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: list(rows),
            split_rows_by_scope=lambda rs: {"canonical_rows": rs, "context_rows": [], "rejected_rows": []},
            dedupe=lambda rs: rs,
            infer_doc_date_from_path=lambda _path: "2025-08-19",
            normalize_period_for_db=lambda label, doc_date=None: ("2025-06-30", "2025-06-30"),
        )

    def test_adapter_recovers_capex_from_table_fallback(self):
        rows = [
            {
                "file": "/tmp/2025-08-19_bhp-annual-report.pdf",
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
                "page_number": 8,
                "table_page": 8,
                "inside_table": True,
            }
        ]
        extract_mod = self._extract_mod(rows)
        original_fb = CF_ADAPTER.CASHFLOW_TABLE_FALLBACK
        try:
            CF_ADAPTER.CASHFLOW_TABLE_FALLBACK = SimpleNamespace(
                extract_cashflow_table_rows_with_camelot_with_stats=lambda _pdf, _page: (
                    [
                        {
                            "raw_label": "Purchases of property, plant and equipment",
                            "numeric_tokens": ["(1,500)", "(900)"],
                            "page_number": 8,
                            "source": "camelot_lattice",
                        }
                    ],
                    {"pages_scanned": 1, "tables_found": 1},
                )
            )
            out, stats = CF_ADAPTER.extract_cashflow_candidates(
                extract_mod=extract_mod,
                pdf=Path("/tmp/2025-08-19_bhp-annual-report.pdf"),
                source_kind="annual_report",
                prepared_pages={8: [{"text": "Consolidated Statement of Cash Flows"}]},
                selected_cashflow_pages={8},
                missing_periods=set(),
                exclusion_fn=lambda _txt: False,
            )
        finally:
            CF_ADAPTER.CASHFLOW_TABLE_FALLBACK = original_fb

        self.assertEqual(int(stats.get("camelot_pages_scanned", 0)), 1)
        self.assertEqual(int(stats.get("camelot_tables_found", 0)), 1)
        self.assertEqual(int(stats.get("capex_rows_recovered_via_table_fallback", 0)), 1)
        self.assertEqual(len(out), 1)
        self.assertEqual(str(out[0].get("metric", "")), "capital_expenditure")
        self.assertEqual(str(out[0].get("numeric_parse_reason", "")), "camelot_lattice_recovery")
        # Previous quarter chooses second token.
        self.assertEqual(str(out[0].get("raw_value", "")), "(900)")

    def test_adapter_does_not_trigger_fallback_for_non_statutory_docs(self):
        rows = [
            {
                "file": "/tmp/2025-10-29_quarterly-activities-appendix-5b.pdf",
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
                "statement_period_end": "",
                "table_header_text": "Current quarter Previous quarter",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "b1",
                "page_number": 8,
                "table_page": 8,
                "inside_table": True,
            }
        ]
        extract_mod = self._extract_mod(rows)
        original_fb = CF_ADAPTER.CASHFLOW_TABLE_FALLBACK
        try:
            CF_ADAPTER.CASHFLOW_TABLE_FALLBACK = SimpleNamespace(
                extract_cashflow_table_rows_with_camelot_with_stats=lambda _pdf, _page: (
                    [
                        {
                            "raw_label": "Purchases of property, plant and equipment",
                            "numeric_tokens": ["(1,111)"],
                            "page_number": 8,
                            "source": "camelot_lattice",
                        }
                    ],
                    {"pages_scanned": 1, "tables_found": 1},
                )
            )
            out, stats = CF_ADAPTER.extract_cashflow_candidates(
                extract_mod=extract_mod,
                pdf=Path("/tmp/2025-10-29_quarterly-activities-appendix-5b.pdf"),
                source_kind="appendix_report",
                prepared_pages={8: [{"text": "Consolidated Statement of Cash Flows"}]},
                selected_cashflow_pages={8},
                missing_periods=set(),
                exclusion_fn=lambda _txt: False,
            )
        finally:
            CF_ADAPTER.CASHFLOW_TABLE_FALLBACK = original_fb

        self.assertEqual(int(stats.get("camelot_pages_scanned", 0)), 0)
        self.assertEqual(int(stats.get("capex_rows_recovered_via_table_fallback", 0)), 0)
        self.assertEqual(len(out), 0)

    def test_page_level_eligibility_scans_when_rows_have_no_capex_phrase(self):
        rows = [
            {
                "file": "/tmp/2025-08-19_bhp-annual-report.pdf",
                "metric": "cashflow_unmapped",
                "metric_base": "cashflow_unmapped",
                "row_label": "Net cash from operating activities",
                "line": "Net cash from operating activities",
                "raw_value": "1,000",
                "value": 1000.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Current quarter",
                "period": "Current quarter",
                "statement_period_end": "",
                "table_header_text": "Current quarter Previous quarter",
                "statement_title": "Consolidated Statement of Cash Flows",
                "block_id": "b1",
                "page_number": 8,
                "table_page": 8,
                "inside_table": True,
            }
        ]
        context_text = "\n".join(
            [
                "Investing activities",
                "Purchases of property, plant and equipment",
            ]
        )
        extract_mod = self._extract_mod(rows, context_text=context_text)
        original_fb = CF_ADAPTER.CASHFLOW_TABLE_FALLBACK
        try:
            CF_ADAPTER.CASHFLOW_TABLE_FALLBACK = SimpleNamespace(
                extract_cashflow_table_rows_with_camelot_with_stats=lambda _pdf, _page: (
                    [
                        {
                            "raw_label": "Purchases of property, plant and equipment",
                            "numeric_tokens": ["(2,345)"],
                            "page_number": 8,
                            "source": "camelot_lattice",
                        }
                    ],
                    {"pages_scanned": 1, "tables_found": 1},
                )
            )
            out, stats = CF_ADAPTER.extract_cashflow_candidates(
                extract_mod=extract_mod,
                pdf=Path("/tmp/2025-08-19_bhp-annual-report.pdf"),
                source_kind="annual_report",
                prepared_pages={8: [{"text": "Consolidated Statement of Cash Flows"}]},
                selected_cashflow_pages={8},
                missing_periods=set(),
                exclusion_fn=lambda _txt: False,
            )
        finally:
            CF_ADAPTER.CASHFLOW_TABLE_FALLBACK = original_fb

        self.assertGreaterEqual(int(stats.get("capex_rows_phrase_match", 0)), 1)
        self.assertGreaterEqual(int(stats.get("capex_rows_numeric_failed", 0)), 1)
        self.assertGreaterEqual(int(stats.get("capex_rows_fallback_eligible", 0)), 1)
        self.assertEqual(int(stats.get("camelot_pages_scanned", 0)), 1)
        self.assertEqual(int(stats.get("camelot_fallback_invocation_attempted", 0)), 1)
        self.assertEqual(int(stats.get("capex_rows_recovered_via_table_fallback", 0)), 1)
        self.assertTrue(any(str(r.get("mapping_source", "")) == "camelot_lattice_capex" for r in out))


if __name__ == "__main__":
    unittest.main()
