import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
SECTION = load_module(str(ROOT / "section_capture_layer.py"), "section_capture_layer_audit")


class TestCashflowPreScopeAudit(unittest.TestCase):
    def test_cashflow_pre_scope_audit_artifacts_capture_and_filter_rows(self):
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
                1: [
                    {"text": "Consolidated Statement of Cash Flows", "numeric_words": []},
                    {"text": "Operating activities", "numeric_words": []},
                ],
                2: [
                    {"text": "Investing activities", "numeric_words": []},
                    {"text": "Payments for property, plant and equipment", "numeric_words": []},
                ],
                3: [
                    {"text": "Notes to the financial statements", "numeric_words": []},
                    {"text": "Adjusted reconciliation", "numeric_words": []},
                ],
            }

            row_capex = {
                "file": str(pdf_path.resolve()),
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
                "statement_period_end": "2024-06-30",
                "table_header_text": "Investing activities",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 2,
                "table_page": 2,
                "inside_table": True,
            }
            row_recon = {
                "file": str(pdf_path.resolve()),
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
                "statement_period_end": "2024-06-30",
                "table_header_text": "Reconciliation",
                "statement_title": "Consolidated Statement of Cash Flows",
                "page_number": 2,
                "table_page": 2,
                "inside_table": True,
            }
            row_notes = {
                "file": str(pdf_path.resolve()),
                "metric": "capex",
                "metric_base": "capex",
                "row_label": "notes-only capex",
                "line": "777",
                "raw_value": "777",
                "value": 777.0,
                "value_type": "amount",
                "statement_scope": "other",
                "statement_type": "other",
                "statement_family": "cash_flow",
                "statement_period": "Year ended 30 June 2024",
                "period": "Year ended 30 June 2024",
                "statement_period_end": "2024-06-30",
                "table_header_text": "Notes",
                "statement_title": "Notes to the financial statements",
                "page_number": 3,
                "table_page": 3,
                "inside_table": True,
            }

            def fake_split(rows):
                context_rows = []
                for rr in rows:
                    reason = (
                        "reconciliation_context"
                        if "reconciliation" in str(rr.get("row_label", "")).lower()
                        else "component_adjustment_row"
                    )
                    context_rows.append(dict(rr, context_reason=reason))
                return {"canonical_rows": [], "context_rows": context_rows, "rejected_rows": []}

            original = {
                "_prepare_bbox_pages": SECTION.EXTRACT._prepare_bbox_pages,
                "classify_pdf_source_kind": SECTION.EXTRACT.classify_pdf_source_kind,
                "segment_statement_blocks": SECTION.EXTRACT.segment_statement_blocks,
                "extract_metrics_from_blocks": SECTION.EXTRACT.extract_metrics_from_blocks,
                "split_rows_by_scope": SECTION.EXTRACT.split_rows_by_scope,
                "resolve_canonical_conflicts": SECTION.EXTRACT.resolve_canonical_conflicts,
                "apply_balance_sheet_identity_guard": SECTION.EXTRACT.apply_balance_sheet_identity_guard,
                "dedupe": SECTION.EXTRACT.dedupe,
            }
            try:
                SECTION.EXTRACT._prepare_bbox_pages = lambda _pdf: prepared_pages
                SECTION.EXTRACT.classify_pdf_source_kind = lambda _pdf: "consolidated"
                SECTION.EXTRACT.segment_statement_blocks = (
                    lambda _pdf, source_kind=None, prepared_pages=None: [
                        {"title": "Consolidated Statement of Cash Flows", "context_text": "", "statement_family": "cash_flow"},
                        {"title": "Notes to the financial statements", "context_text": "", "statement_family": "other"},
                    ]
                )
                SECTION.EXTRACT.extract_metrics_from_blocks = (
                    lambda _pdf, _blocks, strict_metric_rows_only=False, prepared_pages=None: [
                        dict(row_capex),
                        dict(row_recon),
                        dict(row_notes),
                    ]
                )
                SECTION.EXTRACT.split_rows_by_scope = fake_split
                SECTION.EXTRACT.resolve_canonical_conflicts = lambda rows: (rows, [])
                SECTION.EXTRACT.apply_balance_sheet_identity_guard = lambda rows: (rows, [])
                SECTION.EXTRACT.dedupe = lambda rows: rows

                result = SECTION.run_section_capture_layer(
                    pdf_dir=pdf_dir,
                    canonical_path=canonical_path,
                    out_dir=td_path,
                    force_section_pass=True,
                    audit_cashflow_pre_scope=True,
                    audit_max_pages_per_pdf=2,
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

            self.assertTrue(result["audit_cashflow_pre_scope_enabled"])

            pre_path = td_path / "cashflow_pre_scope_rows.csv"
            post_path = td_path / "cashflow_post_scope_rows.csv"
            written_path = td_path / "cashflow_canonical_written_rows.csv"
            summary_path = td_path / "cashflow_audit_summary.json"

            self.assertTrue(pre_path.exists())
            self.assertTrue(post_path.exists())
            self.assertTrue(written_path.exists())
            self.assertTrue(summary_path.exists())

            pre_df = pd.read_csv(pre_path)
            post_df = pd.read_csv(post_path)
            written_df = pd.read_csv(written_path)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            pre_text = "\n".join(pre_df["raw_text"].fillna("").astype(str).tolist()).lower()
            self.assertIn("payments for property, plant and equipment", pre_text)
            self.assertNotIn("notes-only capex", pre_text)
            self.assertTrue((pre_df["numeric_parse_ok"].fillna(0).astype(int) == 1).any())

            self.assertTrue((post_df["scope"].fillna("").str.lower() == "context").any())
            self.assertNotIn("reconciliation_context", set(post_df["context_reason"].fillna("").astype(str).tolist()))

            written_text = "\n".join(written_df["raw_text"].fillna("").astype(str).tolist()).lower()
            self.assertIn("payments for property, plant and equipment", written_text)
            self.assertNotIn("reconciliation of net debt", written_text)

            self.assertGreater(int(summary["counts"]["rows_pre_scope"]), 0)
            self.assertGreater(int(summary["counts"]["rows_written_canonical"]), 0)
            self.assertGreaterEqual(int(summary["top_raw_text_contains_keywords"]["property"]), 1)
            self.assertGreaterEqual(int(summary["top_raw_text_contains_keywords"]["payments"]), 1)
            self.assertIn("capex_numeric_audit", summary)
            self.assertIn("capex_like_rows_pre_scope", summary["capex_numeric_audit"])
            self.assertIn("top_numeric_parse_fail_reasons", summary["capex_numeric_audit"])
            self.assertIn("capex_rows_reconstructed", summary["capex_numeric_audit"])
            self.assertIn("capex_rows_consumed_following_lines", summary["capex_numeric_audit"])


if __name__ == "__main__":
    unittest.main()
