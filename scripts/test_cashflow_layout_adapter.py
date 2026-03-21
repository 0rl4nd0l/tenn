import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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
ADAPTER_PATH = SCRIPT_DIR / "cashflow_layout_adapter.py"
SECTION_PATH = SCRIPT_DIR / "section_capture_layer.py"
if not ADAPTER_PATH.exists() or not SECTION_PATH.exists():
    pytest.skip(
        "INCOMPLETE MIGRATION — cashflow_layout_adapter.py and section_capture_layer.py "
        "exist on main (commits 710fe968, af7f8e57) but were not merged into "
        "cloud/session-20260319. Merge main or cherry-pick those commits to restore "
        "full layout adapter integration tests. "
        "See backend/tests/test_extraction_capability_guards.py for the tracking xfail.",
        allow_module_level=True,
    )
CF_ADAPTER = load_module(str(ADAPTER_PATH), "cashflow_layout_adapter")
SECTION = load_module(str(SECTION_PATH), "section_capture_layer")


class TestCashflowLayoutAdapter(unittest.TestCase):
    def test_subtotal_preserved_reconciliation_filtered_and_dedupe_applied(self):
        def dedupe_rows(rows):
            seen = set()
            out = []
            for r in rows:
                k = (
                    str(r.get("file", "")),
                    str(r.get("metric", "")),
                    str(r.get("statement_period_end", "")),
                    str(r.get("raw_value", "")),
                )
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            return out

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [
                {
                    "file": str(pdf),
                    "metric": "cash_and_equivalents",
                    "metric_base": "cash_and_equivalents",
                    "row_label": "Net cash from operating activities",
                    "line": "100",
                    "raw_value": "100",
                    "value": 100.0,
                    "statement_scope": "other",
                    "statement_type": "other",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2024",
                    "period": "Year ended 30 June 2024",
                    "statement_period_end": "",
                    "table_header_text": "Statement of cash flows",
                    "statement_title": "Consolidated Statement of Cash Flows",
                    "page_number": 10,
                    "table_page": 10,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
                {
                    "file": str(pdf),
                    "metric": "cash_and_equivalents",
                    "metric_base": "cash_and_equivalents",
                    "row_label": "Net cash from operating activities",
                    "line": "100",
                    "raw_value": "100",
                    "value": 100.0,
                    "statement_scope": "other",
                    "statement_type": "other",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2024",
                    "period": "Year ended 30 June 2024",
                    "statement_period_end": "",
                    "table_header_text": "Statement of cash flows",
                    "statement_title": "Consolidated Statement of Cash Flows",
                    "page_number": 10,
                    "table_page": 10,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
                {
                    "file": str(pdf),
                    "metric": "operating_cash_flow",
                    "metric_base": "operating_cash_flow",
                    "row_label": "Reconciliation of net debt",
                    "line": "50",
                    "raw_value": "50",
                    "value": 50.0,
                    "statement_scope": "other",
                    "statement_type": "other",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2024",
                    "period": "Year ended 30 June 2024",
                    "statement_period_end": "",
                    "table_header_text": "Reconciliation",
                    "statement_title": "Consolidated Statement of Cash Flows",
                    "page_number": 10,
                    "table_page": 10,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
            ],
            split_rows_by_scope=lambda rows: {"canonical_rows": rows, "context_rows": [], "rejected_rows": []},
            dedupe=dedupe_rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )

        rows, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={10: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={10},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda text: "reconciliation" in str(text).lower(),
        )

        self.assertEqual(stats["rows_raw"], 3)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(str(row.get("metric")), "operating_cash_flow")
        self.assertEqual(str(row.get("statement_scope")), "consolidated_statement")
        self.assertEqual(str(row.get("statement_period_end")), "2024-06-30")

    def test_activation_only_when_cashflow_core_missing_and_not_for_balance_only(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            pdf_dir = td_path / "pdfs"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = pdf_dir / "demo.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")

            canonical_missing_cf = td_path / "canonical_missing_cf.csv"
            pd.DataFrame(
                [
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "revenue", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "ebit", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "net_income", "value": 1.0},
                ]
            ).to_csv(canonical_missing_cf, index=False)

            canonical_balance_only = td_path / "canonical_balance_only.csv"
            pd.DataFrame(
                [
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-12-31", "metric": "revenue", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-12-31", "metric": "ebit", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-12-31", "metric": "net_income", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-12-31", "metric": "operating_cash_flow", "value": 1.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-12-31", "metric": "capital_expenditure", "value": 1.0},
                ]
            ).to_csv(canonical_balance_only, index=False)

            call_counter = {"count": 0}

            def fake_adapter(**kwargs):
                call_counter["count"] += 1
                return [], {}

            original = {
                "_prepare_bbox_pages": SECTION.EXTRACT._prepare_bbox_pages,
                "classify_pdf_source_kind": SECTION.EXTRACT.classify_pdf_source_kind,
                "segment_statement_blocks": SECTION.EXTRACT.segment_statement_blocks,
                "extract_metrics_from_blocks": SECTION.EXTRACT.extract_metrics_from_blocks,
                "split_rows_by_scope": SECTION.EXTRACT.split_rows_by_scope,
                "resolve_canonical_conflicts": SECTION.EXTRACT.resolve_canonical_conflicts,
                "apply_balance_sheet_identity_guard": SECTION.EXTRACT.apply_balance_sheet_identity_guard,
                "dedupe": SECTION.EXTRACT.dedupe,
                "adapter": SECTION.CASHFLOW_ADAPTER.extract_cashflow_candidates,
            }
            try:
                SECTION.EXTRACT._prepare_bbox_pages = lambda _pdf: {
                    1: [{"text": "Consolidated Statement of Financial Position", "numeric_words": []}],
                    2: [{"text": "Consolidated Statement of Cash Flows", "numeric_words": []}],
                }
                SECTION.EXTRACT.classify_pdf_source_kind = lambda _pdf: "consolidated"
                SECTION.EXTRACT.segment_statement_blocks = lambda _pdf, source_kind="", prepared_pages=None: []
                SECTION.EXTRACT.extract_metrics_from_blocks = (
                    lambda _pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: []
                )
                SECTION.EXTRACT.split_rows_by_scope = lambda rows: {"canonical_rows": [], "context_rows": [], "rejected_rows": []}
                SECTION.EXTRACT.resolve_canonical_conflicts = lambda rows: (rows, [])
                SECTION.EXTRACT.apply_balance_sheet_identity_guard = lambda rows: (rows, [])
                SECTION.EXTRACT.dedupe = lambda rows: rows
                SECTION.CASHFLOW_ADAPTER.extract_cashflow_candidates = fake_adapter

                SECTION.run_section_capture_layer(
                    pdf_dir=pdf_dir,
                    canonical_path=canonical_missing_cf,
                    out_dir=td_path / "run_missing_cf",
                    force_section_pass=True,
                )
                self.assertEqual(call_counter["count"], 1)

                call_counter["count"] = 0
                SECTION.run_section_capture_layer(
                    pdf_dir=pdf_dir,
                    canonical_path=canonical_balance_only,
                    out_dir=td_path / "run_balance_only",
                    force_section_pass=True,
                )
                self.assertEqual(call_counter["count"], 0)
            finally:
                SECTION.EXTRACT._prepare_bbox_pages = original["_prepare_bbox_pages"]
                SECTION.EXTRACT.classify_pdf_source_kind = original["classify_pdf_source_kind"]
                SECTION.EXTRACT.segment_statement_blocks = original["segment_statement_blocks"]
                SECTION.EXTRACT.extract_metrics_from_blocks = original["extract_metrics_from_blocks"]
                SECTION.EXTRACT.split_rows_by_scope = original["split_rows_by_scope"]
                SECTION.EXTRACT.resolve_canonical_conflicts = original["resolve_canonical_conflicts"]
                SECTION.EXTRACT.apply_balance_sheet_identity_guard = original["apply_balance_sheet_identity_guard"]
                SECTION.EXTRACT.dedupe = original["dedupe"]
                SECTION.CASHFLOW_ADAPTER.extract_cashflow_candidates = original["adapter"]

    def test_validation_improves_when_adapter_adds_cashflow_rows(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            pdf_dir = td_path / "pdfs"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = pdf_dir / "demo.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\n")

            canonical_path = td_path / "canonical.csv"
            pd.DataFrame(
                [
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "revenue", "value": 100.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "ebit", "value": 10.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "net_income", "value": 8.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "total_assets", "value": 200.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "total_liabilities", "value": 120.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "total_equity", "value": 80.0},
                    {"file": str(pdf_path.resolve()), "statement_period_end": "2024-06-30", "metric": "cash_and_equivalents", "value": 30.0},
                ]
            ).to_csv(canonical_path, index=False)

            def fake_adapter(**kwargs):
                return (
                    [
                        {
                            "file": str(pdf_path.resolve()),
                            "statement_period_end": "2024-06-30",
                            "metric": "free_cash_flow",
                            "metric_base": "free_cash_flow",
                            "value": 12.0,
                            "raw_value": "12",
                            "currency": "AUD",
                            "statement_scope": "consolidated_statement",
                            "statement_type": "consolidated_statement",
                            "statement_family": "cash_flow",
                            "statement_title": "Consolidated statement of cash flows",
                            "period": "Year ended 30 June 2024",
                            "statement_period": "Year ended 30 June 2024",
                            "table_header_text": "Statement of cash flows",
                            "inside_table": True,
                            "page_number": 2,
                            "canonical_confidence_score": 3,
                        }
                    ],
                    {},
                )

            original = {
                "_prepare_bbox_pages": SECTION.EXTRACT._prepare_bbox_pages,
                "classify_pdf_source_kind": SECTION.EXTRACT.classify_pdf_source_kind,
                "segment_statement_blocks": SECTION.EXTRACT.segment_statement_blocks,
                "extract_metrics_from_blocks": SECTION.EXTRACT.extract_metrics_from_blocks,
                "split_rows_by_scope": SECTION.EXTRACT.split_rows_by_scope,
                "resolve_canonical_conflicts": SECTION.EXTRACT.resolve_canonical_conflicts,
                "apply_balance_sheet_identity_guard": SECTION.EXTRACT.apply_balance_sheet_identity_guard,
                "dedupe": SECTION.EXTRACT.dedupe,
                "adapter": SECTION.CASHFLOW_ADAPTER.extract_cashflow_candidates,
            }
            try:
                SECTION.EXTRACT._prepare_bbox_pages = lambda _pdf: {
                    1: [{"text": "Consolidated Statement of Financial Position", "numeric_words": []}],
                    2: [{"text": "Consolidated Statement of Cash Flows", "numeric_words": []}],
                }
                SECTION.EXTRACT.classify_pdf_source_kind = lambda _pdf: "consolidated"
                SECTION.EXTRACT.segment_statement_blocks = lambda _pdf, source_kind="", prepared_pages=None: []
                SECTION.EXTRACT.extract_metrics_from_blocks = (
                    lambda _pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: []
                )
                SECTION.EXTRACT.split_rows_by_scope = lambda rows: {"canonical_rows": [], "context_rows": [], "rejected_rows": []}
                SECTION.EXTRACT.resolve_canonical_conflicts = lambda rows: (rows, [])
                SECTION.EXTRACT.apply_balance_sheet_identity_guard = lambda rows: (rows, [])
                SECTION.EXTRACT.dedupe = lambda rows: rows
                SECTION.CASHFLOW_ADAPTER.extract_cashflow_candidates = fake_adapter

                result = SECTION.run_section_capture_layer(
                    pdf_dir=pdf_dir,
                    canonical_path=canonical_path,
                    out_dir=td_path / "run",
                    force_section_pass=True,
                )
            finally:
                SECTION.EXTRACT._prepare_bbox_pages = original["_prepare_bbox_pages"]
                SECTION.EXTRACT.classify_pdf_source_kind = original["classify_pdf_source_kind"]
                SECTION.EXTRACT.segment_statement_blocks = original["segment_statement_blocks"]
                SECTION.EXTRACT.extract_metrics_from_blocks = original["extract_metrics_from_blocks"]
                SECTION.EXTRACT.split_rows_by_scope = original["split_rows_by_scope"]
                SECTION.EXTRACT.resolve_canonical_conflicts = original["resolve_canonical_conflicts"]
                SECTION.EXTRACT.apply_balance_sheet_identity_guard = original["apply_balance_sheet_identity_guard"]
                SECTION.EXTRACT.dedupe = original["dedupe"]
                SECTION.CASHFLOW_ADAPTER.extract_cashflow_candidates = original["adapter"]

            summary_path = Path(result["cashflow_adapter_summary_path"])
            self.assertTrue(summary_path.exists())
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertGreater(float(summary["delta"]["fcf_completeness_mean"]), 0.0)
            self.assertEqual(int(summary["rows_added_from_cashflow_adapter"]), 1)

    def test_cashflow_scope_override_promotes_numeric_context_rows(self):
        def dedupe_rows(rows):
            seen = set()
            out = []
            for r in rows:
                k = (
                    str(r.get("file", "")),
                    str(r.get("metric", "")),
                    str(r.get("statement_period_end", "")),
                    str(r.get("raw_value", "")),
                )
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            return out

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [
                {
                    "file": str(pdf),
                    "metric": "capex",
                    "metric_base": "capex",
                    "row_label": "Payments for property, plant and equipment",
                    "line": "(1,250)",
                    "raw_value": "(1,250)",
                    "value": -1250.0,
                    "value_type": "amount",
                    "statement_scope": "other",
                    "statement_type": "other",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2024",
                    "period": "Year ended 30 June 2024",
                    "statement_period_end": "",
                    "table_header_text": "Investing activities",
                    "statement_title": "Consolidated Statement of Cash Flows",
                    "page_number": 12,
                    "table_page": 12,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
                {
                    "file": str(pdf),
                    "metric": "operating_cash_flow",
                    "metric_base": "operating_cash_flow",
                    "row_label": "Reconciliation of net debt",
                    "line": "99",
                    "raw_value": "99",
                    "value": 99.0,
                    "value_type": "amount",
                    "statement_scope": "other",
                    "statement_type": "other",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2024",
                    "period": "Year ended 30 June 2024",
                    "statement_period_end": "",
                    "table_header_text": "Reconciliation",
                    "statement_title": "Consolidated Statement of Cash Flows",
                    "page_number": 12,
                    "table_page": 12,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
            ],
            split_rows_by_scope=lambda rows: {
                "canonical_rows": [],
                "context_rows": [
                    dict(rows[0], context_reason="component_adjustment_row"),
                    dict(rows[1], context_reason="reconciliation_context"),
                ],
                "rejected_rows": [],
            },
            dedupe=dedupe_rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )

        rows, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={12: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={12},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda text: "notes to the financial statements" in str(text).lower(),
        )

        self.assertEqual(stats["rows_after_split_context"], 2)
        self.assertEqual(stats["rows_recovered_scope_override"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0].get("metric")), "capex")
        self.assertEqual(str(rows[0].get("statement_scope")), "consolidated_statement")
        self.assertEqual(str(rows[0].get("statement_period_end")), "2024-06-30")

    def test_scope_override_excludes_unmapped_and_low_confidence_rows(self):
        def dedupe_rows(rows):
            seen = set()
            out = []
            for r in rows:
                k = (
                    str(r.get("file", "")),
                    str(r.get("metric", "")),
                    str(r.get("statement_period_end", "")),
                    str(r.get("raw_value", "")),
                )
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            return out

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [
                {
                    "file": str(Path("/tmp/demo.pdf")),
                    "metric": "cash_and_equivalents",
                    "metric_base": "cash_and_equivalents",
                    "raw_value": "120",
                    "value": 120.0,
                    "value_type": "amount",
                    "row_label": "Cash and cash equivalents at end of period",
                    "line": "120",
                    "statement_scope": "consolidated_statement",
                    "statement_type": "consolidated_statement",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2024",
                    "period": "Year ended 30 June 2024",
                    "statement_period_end": "2024-06-30",
                    "inside_table": True,
                    "table_header_text": "Consolidated statement of cash flows",
                    "statement_title": "Consolidated statement of cash flows",
                    "page_number": 12,
                    "canonical_confidence_score": 3,
                }
            ],
            split_rows_by_scope=lambda rows: {
                "canonical_rows": [
                    {
                        "file": str(Path("/tmp/demo.pdf")),
                        "metric": "cashflow_unmapped",
                        "metric_base": "cashflow_unmapped",
                        "raw_value": "48",
                        "value": 48.0,
                        "value_type": "amount",
                        "row_label": "Unmapped row",
                        "line": "48",
                        "statement_scope": "consolidated_statement",
                        "statement_type": "consolidated_statement",
                        "statement_family": "cash_flow",
                        "statement_period_end": "2024-06-30",
                        "inside_table": True,
                        "page_number": 12,
                        "canonical_confidence_score": 3,
                    }
                ],
                "context_rows": [
                    {
                        "file": str(Path("/tmp/demo.pdf")),
                        "metric": "operating_cash_flow",
                        "metric_base": "operating_cash_flow",
                        "raw_value": "60",
                        "value": 60.0,
                        "value_type": "amount",
                        "row_label": "Net cash from operating activities",
                        "line": "60",
                        "statement_scope": "consolidated_statement",
                        "statement_type": "consolidated_statement",
                        "statement_family": "cash_flow",
                        "statement_period": "Year ended 30 June 2024",
                        "period": "Year ended 30 June 2024",
                        "statement_period_end": "",
                        "inside_table": True,
                        "table_header_text": "Consolidated statement of cash flows",
                        "statement_title": "Consolidated statement of cash flows",
                        "page_number": 12,
                        "context_reason": "component_adjustment_row",
                        "canonical_confidence_score": 1,
                    },
                    {
                        "file": str(Path("/tmp/demo.pdf")),
                        "metric": "operating_cash_flow",
                        "metric_base": "operating_cash_flow",
                        "raw_value": "75",
                        "value": 75.0,
                        "value_type": "amount",
                        "row_label": "Net cash from operating activities",
                        "line": "75",
                        "statement_scope": "consolidated_statement",
                        "statement_type": "consolidated_statement",
                        "statement_family": "cash_flow",
                        "statement_period": "Year ended 30 June 2024",
                        "period": "Year ended 30 June 2024",
                        "statement_period_end": "2024-06-30",
                        "inside_table": True,
                        "table_header_text": "Consolidated statement of cash flows",
                        "statement_title": "Consolidated statement of cash flows",
                        "page_number": 12,
                        "context_reason": "component_adjustment_row",
                        "canonical_confidence_score": 3,
                    },
                ],
                "rejected_rows": [],
            },
            dedupe=dedupe_rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )

        rows, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={12: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={12},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda _text: False,
        )

        self.assertEqual(stats["rows_after_split_canonical"], 1)
        self.assertEqual(stats["rows_after_split_context"], 2)
        self.assertEqual(stats["rows_recovered_scope_override"], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0].get("metric")), "operating_cash_flow")
        self.assertEqual(str(rows[0].get("statement_period_end")), "2024-06-30")

    def test_forward_label_numeric_mapping_recovers_operating_cash_flow(self):
        def dedupe_rows(rows):
            seen = set()
            out = []
            for r in rows:
                k = (
                    str(r.get("file", "")),
                    str(r.get("metric", "")),
                    str(r.get("statement_period_end", "")),
                    str(r.get("raw_value", "")),
                )
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            return out

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {
                    "title": "Consolidated Statement of Cash Flows",
                    "context_text": "\n".join(
                        [
                            "55",
                            "59",
                            "149",
                            "Cash generated from operations",
                            "Net operating cash flows",
                        ]
                    ),
                    "statement_family": "cash_flow",
                    "page_start": 34,
                    "line_start": 1,
                    "block_id": "p34:b1",
                }
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [],
            split_rows_by_scope=lambda rows: {"canonical_rows": rows, "context_rows": [], "rejected_rows": []},
            dedupe=dedupe_rows,
            infer_doc_date_from_path=lambda _path: "2025-02-18",
            normalize_period_for_db=lambda label, doc_date=None: ("", ""),
        )

        rows, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={34: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={34},
            missing_periods={"2024-12-31", "2024-06-30", "2023-12-31"},
            exclusion_fn=lambda _text: False,
        )

        self.assertGreaterEqual(stats["rows_context_line_candidates"], 1)
        ocf_rows = [r for r in rows if str(r.get("metric_base", r.get("metric", ""))) == "operating_cash_flow"]
        self.assertEqual(len(ocf_rows), 1)
        self.assertEqual(str(ocf_rows[0].get("raw_value", "")), "149")
        self.assertEqual(str(ocf_rows[0].get("statement_period_end", "")), "2024-12-31")

    def test_duplicate_operating_cash_flow_periods_rebalanced_by_missing_periods(self):
        def dedupe_rows(rows):
            # Preserve rows for this test; period rebalance runs after dedupe.
            return list(rows)

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [
                {
                    "file": str(pdf),
                    "metric": "operating_cash_flow",
                    "metric_base": "operating_cash_flow",
                    "row_label": "Net operating cash flow",
                    "line": "Net operating cash flow 6,263",
                    "raw_value": "6,263",
                    "value": 6263.0,
                    "value_type": "amount",
                    "statement_scope": "other",
                    "statement_type": "other",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2025",
                    "period": "Year ended 30 June 2025",
                    "statement_period_end": "2025-06-30",
                    "table_header_text": "Consolidated statement of cash flows",
                    "statement_title": "Consolidated statement of cash flows",
                    "page_number": 157,
                    "table_page": 157,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
                {
                    "file": str(pdf),
                    "metric": "operating_cash_flow",
                    "metric_base": "operating_cash_flow",
                    "row_label": "Net operating cash flow",
                    "line": "Net operating cash flow 4,180",
                    "raw_value": "4,180",
                    "value": 4180.0,
                    "value_type": "amount",
                    "statement_scope": "other",
                    "statement_type": "other",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2025",
                    "period": "Year ended 30 June 2025",
                    "statement_period_end": "2025-06-30",
                    "table_header_text": "Consolidated statement of cash flows",
                    "statement_title": "Consolidated statement of cash flows",
                    "page_number": 157,
                    "table_page": 157,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
            ],
            split_rows_by_scope=lambda rows: {"canonical_rows": rows, "context_rows": [], "rejected_rows": []},
            dedupe=dedupe_rows,
            infer_doc_date_from_path=lambda _path: "2025-08-19",
            normalize_period_for_db=lambda label, doc_date=None: ("", ""),
        )

        rows, _stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={157: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={157},
            missing_periods={"2025-06-30", "2024-06-30", "2024-12-31"},
            exclusion_fn=lambda _text: False,
        )

        ocf_periods = sorted(
            {
                str(r.get("statement_period_end", ""))
                for r in rows
                if str(r.get("metric_base", r.get("metric", ""))) == "operating_cash_flow"
            }
        )
        self.assertEqual(ocf_periods, ["2024-06-30", "2025-06-30"])

    def test_context_line_phrase_label_without_inline_numeric_not_promoted_as_capex(self):
        """Risk 1: label-only phrase lines must not grab adjacent note refs as canonical values.

        A context block where the CAPEX phrase line has no inline numeric and an adjacent
        line contains a bare note reference number ("5") must not produce a canonical
        capital_expenditure row.  The phrase match should require an inline numeric on the
        same line; the note reference may only produce a cashflow_unmapped row, which is
        excluded from canonical output.
        """

        def dedupe_rows(rows):
            seen = set()
            out = []
            for r in rows:
                k = (str(r.get("file", "")), str(r.get("metric", "")), str(r.get("statement_period_end", "")), str(r.get("raw_value", "")))
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            return out

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {
                    "title": "Consolidated Statement of Cash Flows",
                    # Label line has no inline numeric; adjacent "5" is a note reference.
                    "context_text": "Purchases of property, plant and equipment\n5\nFinancing activities",
                    "statement_family": "cash_flow",
                    "page_start": 7,
                    "line_start": 1,
                    "block_id": "p7:b1",
                }
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [],
            split_rows_by_scope=lambda rows: {"canonical_rows": rows, "context_rows": [], "rejected_rows": []},
            dedupe=dedupe_rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("", ""),
        )

        rows, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={7: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={7},
            missing_periods={"2024-06-30"},
            exclusion_fn=lambda _text: False,
        )

        capex_rows = [r for r in rows if str(r.get("metric_base", r.get("metric", ""))) in {"capital_expenditure", "capex"}]
        self.assertEqual(len(capex_rows), 0, "Note reference '5' adjacent to label-only CAPEX phrase must not become canonical capex")

    def test_period_rebalance_does_not_assign_period_to_empty_period_rows(self):
        """Risk 2: _rebalance_duplicate_cashflow_periods must not assign speculative periods
        to rows that have no statement_period_end.  Empty-period rows should pass through
        unchanged so that _repair_statement_period_end can handle them later.
        """

        def dedupe_rows(rows):
            return list(rows)

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [
                {
                    "file": str(Path("/tmp/demo.pdf")),
                    "metric": "operating_cash_flow",
                    "metric_base": "operating_cash_flow",
                    "row_label": "Net cash from operating activities",
                    "line": "500",
                    "raw_value": "500",
                    "value": 500.0,
                    "value_type": "amount",
                    "statement_scope": "consolidated_statement",
                    "statement_type": "consolidated_statement",
                    "statement_family": "cash_flow",
                    "statement_period": "",
                    "period": "",
                    # Empty period — must not get a speculative assignment via rebalance.
                    "statement_period_end": "",
                    "table_header_text": "Consolidated statement of cash flows",
                    "statement_title": "Consolidated statement of cash flows",
                    "page_number": 5,
                    "table_page": 5,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
            ],
            split_rows_by_scope=lambda rows: {"canonical_rows": rows, "context_rows": [], "rejected_rows": []},
            dedupe=dedupe_rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            # normalize_period_for_db returns empty so _repair also can't help here.
            normalize_period_for_db=lambda label, doc_date=None: ("", ""),
        )

        rows, _stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={5: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={5},
            missing_periods={"2024-06-30", "2023-06-30"},
            exclusion_fn=lambda _text: False,
        )

        # Row had no period end and normalize_period_for_db can't help →
        # must be dropped from canonical output (missing_period_filtered), not assigned a speculative period.
        ocf_rows = [r for r in rows if str(r.get("metric_base", r.get("metric", ""))) == "operating_cash_flow"]
        self.assertEqual(len(ocf_rows), 0, "Empty-period row must not receive a speculative period from rebalance and must not appear in canonical output")

    def test_scope_override_blocked_when_statement_title_is_notes(self):
        """Risk 3: hard statement-family conflict via statement_title must block scope override promotion.

        A row labelled as a cash-flow metric but whose statement_title includes 'Notes to
        the financial statements' must be blocked by the exclusion_fn when the fn covers
        statement_title.  With the fix, exclusion text includes statement_title.
        """

        def dedupe_rows(rows):
            seen = set()
            out = []
            for r in rows:
                k = (str(r.get("file", "")), str(r.get("metric", "")), str(r.get("statement_period_end", "")), str(r.get("raw_value", "")))
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            return out

        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow"}
            ],
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [
                {
                    "file": str(Path("/tmp/demo.pdf")),
                    "metric": "operating_cash_flow",
                    "metric_base": "operating_cash_flow",
                    "row_label": "Net cash from operating activities",
                    "line": "300",
                    "raw_value": "300",
                    "value": 300.0,
                    "value_type": "amount",
                    "statement_scope": "other",
                    "statement_type": "other",
                    "statement_family": "cash_flow",
                    "statement_period": "Year ended 30 June 2024",
                    "period": "Year ended 30 June 2024",
                    "statement_period_end": "2024-06-30",
                    # statement_title signals this is from the notes section.
                    "statement_title": "Notes to the financial statements",
                    "table_header_text": "Consolidated Statement of Cash Flows",
                    "page_number": 20,
                    "table_page": 20,
                    "inside_table": True,
                    "canonical_confidence_score": 3,
                },
            ],
            split_rows_by_scope=lambda rows: {
                "canonical_rows": [],
                "context_rows": [dict(rows[0], context_reason="component_adjustment_row")],
                "rejected_rows": [],
            },
            dedupe=dedupe_rows,
            infer_doc_date_from_path=lambda _path: "2024-08-27",
            normalize_period_for_db=lambda label, doc_date=None: ("2024-06-30", "2024-06-30"),
        )

        rows, stats = CF_ADAPTER.extract_cashflow_candidates(
            extract_mod=extract_mod,
            pdf=Path("/tmp/demo.pdf"),
            source_kind="annual_report",
            prepared_pages={20: [{"text": "Consolidated Statement of Cash Flows"}]},
            selected_cashflow_pages={20},
            missing_periods={"2024-06-30"},
            # exclusion_fn that catches notes in any text field.
            exclusion_fn=lambda text: "notes to the financial statements" in str(text).lower(),
        )

        self.assertEqual(stats["rows_recovered_scope_override"], 0, "Row with notes statement_title must be blocked by exclusion_fn via statement_title inclusion in override check")
        self.assertEqual(len(rows), 0)

    def test_audit_collector_records_dropped_rows_with_reason(self):
        """Risk 4: audit artifacts must capture dropped rows with drop reasons.

        A canonical_rows list containing a cashflow_unmapped row must produce a
        post_scope/dropped audit entry with context_reason='cashflow_unmapped_excluded'.
        """

        def dedupe_rows(rows):
            return list(rows)

        audit_collector = {
            "run_id": "test-run",
            "file_stem": "demo",
            "pdf_path": "/tmp/demo.pdf",
            "target_periods": ["2024-06-30"],
            "target_pages": [9],
        }

        _unmapped_row = {
            "file": str(Path("/tmp/demo.pdf")),
            "metric": "cashflow_unmapped",
            "metric_base": "cashflow_unmapped",
            "row_label": "Some unlabelled line",
            "line": "77",
            "raw_value": "77",
            "value": 77.0,
            "value_type": "amount",
            "statement_scope": "consolidated_statement",
            "statement_type": "consolidated_statement",
            "statement_family": "cash_flow",
            "statement_period_end": "2024-06-30",
            "inside_table": True,
            "page_number": 9,
            "table_page": 9,
            "canonical_confidence_score": 3,
        }
        extract_mod = SimpleNamespace(
            segment_statement_blocks=lambda pdf, source_kind="", prepared_pages=None: [
                {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow"}
            ],
            # Row comes from extraction so scoped_rows is non-empty; split passes it to canonical.
            extract_metrics_from_blocks=lambda pdf, blocks, strict_metric_rows_only=False, prepared_pages=None: [dict(_unmapped_row)],
            split_rows_by_scope=lambda rows: {"canonical_rows": list(rows), "context_rows": [], "rejected_rows": []},
            dedupe=dedupe_rows,
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
            exclusion_fn=lambda _text: False,
            audit_collector=audit_collector,
        )

        self.assertEqual(len(rows), 0, "cashflow_unmapped row must be excluded from canonical output")
        post_rows = audit_collector.get("post_scope_rows", [])
        dropped = [r for r in post_rows if str(r.get("scope", "")).lower() == "dropped"]
        self.assertGreater(len(dropped), 0, "Dropped cashflow_unmapped row must appear in post_scope audit with scope='dropped'")
        reasons = {str(r.get("context_reason", "")) for r in dropped}
        self.assertIn("cashflow_unmapped_excluded", reasons)


if __name__ == "__main__":
    unittest.main()
