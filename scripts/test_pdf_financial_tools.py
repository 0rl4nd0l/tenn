import importlib.util
import json
import subprocess
import sqlite3
import tempfile
import unittest
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
RAG = load_module(str(ROOT / "scripts" / "pdf_rag.py"), "pdf_rag")


class TestExtractFinancialMetrics(unittest.TestCase):
    def test_load_document_quarantine_rules(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "rules.json"
            p.write_text(
                json.dumps(
                    {
                        "rules": [
                            {
                                "ticker": "29M",
                                "reason": "quarantine",
                                "match_substrings": ["golden-grove"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            rules = EXTRACT.load_document_quarantine_rules(p)
            self.assertEqual(len(rules), 1)
            self.assertEqual(rules[0]["ticker"], "29M")
            self.assertEqual(rules[0]["reason"], "quarantine")
            self.assertIn("golden-grove", rules[0]["match_substrings"])

    def test_match_document_quarantine_reason(self):
        rules = [
            {
                "ticker": "29M",
                "reason": "quarantined_subsidiary_emr_golden_grove",
                "match_substrings": ["emr-capital", "golden-grove"],
            }
        ]
        pdf = Path("/home/l4nd0/tenn/financial-engine_v2/data/asx/docs/29M/other/2026-01-19_high-grade-at-golden-grove.pdf")
        reason = EXTRACT.match_document_quarantine_reason(pdf, rules)
        self.assertEqual(reason, "quarantined_subsidiary_emr_golden_grove")

    def test_match_document_quarantine_reason_requires_ticker_when_rule_scoped(self):
        rules = [
            {
                "ticker": "29M",
                "reason": "quarantined_subsidiary_emr_golden_grove",
                "match_substrings": ["golden-grove"],
            }
        ]
        pdf = Path("/tmp/2026-01-19_high-grade-at-golden-grove.pdf")
        reason = EXTRACT.match_document_quarantine_reason(pdf, rules)
        self.assertEqual(reason, "")

    def test_extract_pdf_text_timeout_raises_pdf_parse_timeout_error(self):
        with mock.patch.object(
            EXTRACT.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd=["pdftotext"], timeout=1),
        ):
            with self.assertRaises(EXTRACT.PDFParseTimeoutError):
                EXTRACT.extract_pdf_text(Path("dummy.pdf"), timeout_sec=1)

    def test_parse_bbox_layout_lines_timeout_raises_pdf_parse_timeout_error(self):
        with mock.patch.object(
            EXTRACT.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd=["pdftotext"], timeout=1),
        ):
            with self.assertRaises(EXTRACT.PDFParseTimeoutError):
                EXTRACT.parse_bbox_layout_lines(Path("dummy.pdf"), timeout_sec=1)

    def test_main_docling_strict_skips_pdftotext_line_pass(self):
        with tempfile.TemporaryDirectory() as td:
            pdf_dir = Path(td)
            (pdf_dir / "dummy.pdf").write_text("%PDF-1.4\n", encoding="utf-8")
            argv = [
                "extract_financial_metrics.py",
                "--pdf-dir",
                str(pdf_dir),
                "--extractor",
                "docling",
                "--no-sqlite",
            ]
            empty_split = {"canonical_rows": [], "context_rows": [], "rejected_rows": []}
            with mock.patch.object(EXTRACT, "_get_docling_converter", return_value=(object(), None)):
                with mock.patch.object(EXTRACT, "extract_table_metrics_docling", return_value=([], [], empty_split)):
                    with mock.patch.object(
                        EXTRACT,
                        "extract_pdf_text",
                        side_effect=AssertionError("extract_pdf_text should not run in strict docling mode"),
                    ):
                        with mock.patch.object(EXTRACT.sys, "argv", argv):
                            rc = EXTRACT.main()
        self.assertEqual(rc, 0)

    def test_resolve_docling_runtime_settings_auto_cpu_prefers_fast_threads(self):
        mode, threads = EXTRACT.resolve_docling_runtime_settings(
            requested_table_mode="auto",
            requested_num_threads=0,
            cuda_available=False,
        )
        self.assertEqual(mode, "fast")
        self.assertEqual(threads, 4)

    def test_resolve_docling_runtime_settings_auto_cuda_prefers_fast_threads(self):
        mode, threads = EXTRACT.resolve_docling_runtime_settings(
            requested_table_mode="auto",
            requested_num_threads=0,
            cuda_available=True,
        )
        self.assertEqual(mode, "fast")
        self.assertEqual(threads, 4)

    def test_resolve_docling_runtime_settings_honors_explicit_overrides(self):
        mode, threads = EXTRACT.resolve_docling_runtime_settings(
            requested_table_mode="accurate",
            requested_num_threads=8,
            cuda_available=False,
        )
        self.assertEqual(mode, "accurate")
        self.assertEqual(threads, 8)

    def test_docling_cuda_available_honors_explicit_disable_env(self):
        with mock.patch.dict(EXTRACT.os.environ, {"CUDA_VISIBLE_DEVICES": ""}, clear=True):
            self.assertFalse(EXTRACT._docling_cuda_available())

    def test_docling_cuda_available_uses_torch_when_env_not_forced_off(self):
        fake_torch = mock.Mock()
        fake_torch.cuda.is_available.return_value = True
        with mock.patch.dict(EXTRACT.os.environ, {}, clear=True):
            with mock.patch.dict(EXTRACT.sys.modules, {"torch": fake_torch}):
                self.assertTrue(EXTRACT._docling_cuda_available())

    def test_prefers_money_amount_over_date_number(self):
        line = (
            "For the half year ended 31 December 2025, revenue for the Group from "
            "ordinary activities of $73.671 million was up by 28%"
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        revenue_rows = [r for r in rows if r["metric"] == "revenue" and r["value_type"] == "amount"]
        self.assertTrue(revenue_rows)
        self.assertEqual(revenue_rows[0]["raw_value"], "$73.671 million")

    def test_ignores_ordinal_in_date_for_cash_metric(self):
        line = (
            "On the 6th of January 2026, SEG completed the sale, resulting in $12m "
            "of cash being received."
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        cash_rows = [r for r in rows if r["metric"] == "cash_and_equivalents" and r["value_type"] == "amount"]
        self.assertTrue(cash_rows)
        self.assertEqual(cash_rows[0]["raw_value"], "$12m")
        self.assertEqual(cash_rows[0]["value"], 12000000.0)

    def test_growth_metric_without_qualifier_is_ignored(self):
        line = "5-Year Growth Pathway to +500koz including FY26 Guidance"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        growth_rows = [r for r in rows if r["metric"] == "growth_pct"]
        self.assertEqual(growth_rows, [])

    def test_growth_metric_detects_yoy_percent(self):
        line = "Revenue YoY 12% in FY25."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        growth_rows = [r for r in rows if r["metric"] == "growth_pct" and r["value_type"] == "percent"]
        self.assertTrue(growth_rows)
        self.assertEqual(growth_rows[0]["value"], 12.0)

    def test_cash_flow_does_not_map_to_cash_and_equivalents(self):
        line = "Free cash flow outlook remains strong."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        metrics = {r["metric"] for r in rows}
        self.assertIn("free_cash_flow", metrics)
        self.assertNotIn("cash_and_equivalents", metrics)

    def test_guidance_without_unit_stays_text(self):
        line = "See ASX release including FY26 Guidance, 28 October 2025."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        guidance_rows = [r for r in rows if r["metric"] == "guidance"]
        self.assertTrue(guidance_rows)
        self.assertEqual(guidance_rows[0]["value_type"], "text")

    def test_confidence_scores_money_higher_than_text(self):
        amount_row = {
            "metric": "revenue",
            "value_type": "amount",
            "raw_value": "$73.6m",
            "currency": "$",
            "period": "FY26",
        }
        text_row = {
            "metric": "guidance",
            "value_type": "text",
            "raw_value": "",
            "currency": "",
            "period": "",
        }
        self.assertGreater(EXTRACT.score_confidence(amount_row), EXTRACT.score_confidence(text_row))

    def test_infer_statement_family_comprehensive_income_is_income_statement(self):
        family = EXTRACT.infer_statement_family("Consolidated statement of comprehensive income")
        self.assertEqual(family, "income_statement")

    def test_extract_explicit_date_labels_supports_compact_day_month_year(self):
        labels = EXTRACT._extract_explicit_date_labels("As at 31 Dec 25 and 30 Jun 24")
        self.assertIn("31 December 2025", labels)
        self.assertIn("30 June 2024", labels)

    def test_normalize_period_compact_date_does_not_leak_doc_year(self):
        period_end, sort_date = EXTRACT.normalize_period_for_db(
            "As at 31 Dec 25",
            doc_date="2026-02-03",
            allow_doc_date_fallback=False,
        )
        self.assertEqual(period_end, "2025-12-31")
        self.assertEqual(sort_date, "2025-12-31")

    def test_extended_metric_coverage(self):
        line = (
            "Segment revenue grew 12%, EBITDA was $44m, NPAT reached $18m, free cash flow $9m, "
            "ROIC 14%, net debt reduced to $30m, total borrowings were $42m, shares outstanding 280,874,770, and guidance was maintained."
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        metrics = {r["metric"] for r in rows}
        self.assertIn("segment_revenue", metrics)
        self.assertIn("ebitda", metrics)
        self.assertIn("npat", metrics)
        self.assertIn("free_cash_flow", metrics)
        self.assertIn("roic_pct", metrics)
        self.assertIn("net_debt", metrics)
        self.assertIn("total_debt", metrics)
        self.assertIn("shares_outstanding", metrics)
        self.assertIn("guidance", metrics)

    def test_total_debt_does_not_match_debt_facility_phrase(self):
        line = "Debt facility remained available at $50m."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        debt_rows = [r for r in rows if r["metric"] == "total_debt"]
        self.assertEqual(debt_rows, [])

    def test_total_debt_detects_total_interest_bearing_liabilities(self):
        line = "Total interest bearing liabilities 15,935 12,007"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=True)
        debt_rows = [r for r in rows if r["metric"] == "total_debt" and r["value_type"] == "amount"]
        self.assertTrue(debt_rows)
        self.assertEqual(debt_rows[0]["raw_value"], "15,935")

    def test_net_income_detects_attributable_to_owners_label(self):
        line = "Profit attributable to owners of the parent 2,140 1,820"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=True)
        ni_rows = [r for r in rows if r["metric"] == "net_income" and r["value_type"] == "amount"]
        self.assertTrue(ni_rows)
        self.assertEqual(ni_rows[0]["raw_value"], "2,140")

    def test_net_income_detects_after_taxation_attributable_label(self):
        line = "Profit after taxation attributable to BHP shareholders 9,019 7,897"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=True)
        ni_rows = [r for r in rows if r["metric"] == "net_income" and r["value_type"] == "amount"]
        self.assertTrue(ni_rows)
        self.assertEqual(ni_rows[0]["raw_value"], "9,019")

    def test_metric_variant_detects_statutory_ebit(self):
        line = "Statutory EBIT 48,039 52,331"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        ebit_rows = [r for r in rows if r["metric"] == "ebit" and r["value_type"] == "amount"]
        self.assertTrue(ebit_rows)
        self.assertEqual(ebit_rows[0].get("metric_variant"), "statutory")

    def test_net_debt_metric_detected_separately(self):
        line = "Net debt 30,500 42,000"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=True)
        metrics = {r["metric"] for r in rows if r["value_type"] == "amount"}
        self.assertIn("net_debt", metrics)
        self.assertNotIn("total_debt", metrics)

    def test_extracts_balance_sheet_total_assets_row(self):
        line = "Total assets 1,246,957 1,101,332"
        rows = EXTRACT.parse_line(
            Path("dummy.pdf"),
            1,
            line,
            strict_table_only=True,
            active_section="statement of financial position",
            statement_type="consolidated_statement",
            statement_scope_header="Consolidated statement of financial position",
        )
        metric_rows = [r for r in rows if r["metric"] == "total_assets" and r["value_type"] == "amount"]
        self.assertTrue(metric_rows)
        self.assertEqual(metric_rows[0].get("statement_family"), "balance_sheet")

    def test_strict_mode_rejects_asset_sale_cash_commentary(self):
        line = "$12m cash received for the final tranche of the Perth Wildcats sale received on 6 th January 2026"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 17, line, strict_table_only=True)
        self.assertEqual(rows, [])

    def test_strict_mode_accepts_compact_table_row_without_currency(self):
        line = "Cash and cash equivalents 171,962 197,472"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 10, line, strict_table_only=True)
        cash_rows = [r for r in rows if r["metric"] == "cash_and_equivalents" and r["value_type"] == "amount"]
        self.assertTrue(cash_rows)
        self.assertEqual(cash_rows[0]["raw_value"], "171,962")

    def test_strict_mode_rejects_narrative_multi_amount_sentence(self):
        line = "Revenue improved to $721 million (2021: $601 million), with higher production."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 12, line, strict_table_only=True)
        self.assertEqual(rows, [])

    def test_strict_mode_ignores_row_item_code_value(self):
        line = "4.6 Cash and cash equivalents at end of period 4,585 4,585"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 125, line, strict_table_only=True)
        cash_rows = [r for r in rows if r["metric"] == "cash_and_equivalents" and r["value_type"] == "amount"]
        self.assertTrue(cash_rows)
        self.assertEqual(cash_rows[0]["raw_value"], "4,585")

    def test_prefers_primary_period_value_over_change_column(self):
        line = (
            "2.3 Net Profit/ (Loss) for the period attributable to members "
            "(1,327,795) (1,516,286) (12%) 188,491"
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 28, line, strict_table_only=True)
        ni_rows = [r for r in rows if r["metric"] == "net_income" and r["value_type"] == "amount"]
        self.assertTrue(ni_rows)
        self.assertEqual(ni_rows[0]["raw_value"], "(1,327,795)")

    def test_ignores_aasb_code_number_for_ebitda(self):
        line = "2.3 Pre AASB-16 EBITDA (underlying) Up 94% to 9,715 5,011"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 69, line, strict_table_only=True)
        ebitda_rows = [r for r in rows if r["metric"] == "ebitda" and r["value_type"] == "amount"]
        self.assertTrue(ebitda_rows)
        self.assertEqual(ebitda_rows[0]["raw_value"], "9,715")

    def test_strict_mode_rejects_revenue_growth_sentence(self):
        line = (
            "Revenues have grown from $1,292k in FY2019 to $4,031k in FY2021 due wholesale client expansion."
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 6157, line, strict_table_only=True)
        self.assertEqual(rows, [])

    def test_strict_mode_rejects_bullet_commentary_with_revenue_word(self):
        line = (
            "Distribution (32.4) (26.9) 20.6% • Distribution costs marginally higher as a % of net sales revenue due to"
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 464, line, strict_table_only=True)
        self.assertEqual(rows, [])

    def test_extract_metrics_from_blocks_expanded_scope_includes_guidance_and_growth(self):
        pdf = Path("dummy.pdf")
        blocks = [
            {
                "block_id": "b1",
                "title": "Consolidated statement of profit or loss",
                "statement_scope": "consolidated_statement",
                "statement_family": "income_statement",
                "scope_reason": "test",
                "context_text": "Consolidated statement of profit or loss for the year ended 30 June 2025",
                "parent_entity_context": False,
                "note_number": "",
                "table_regions": [
                    {
                        "table_id": "b1:t1",
                        "page": 1,
                        "start_idx": 0,
                        "end_idx": 1,
                        "bbox": [0.0, 0.0, 400.0, 40.0],
                        "columns": [
                            {"x_center": 220.0, "period": "30 June 2025", "is_variance": False},
                        ],
                        "header_text": "Consolidated statement of profit or loss year ended 30 June 2025 US$M",
                        "unit_multiplier": 1.0,
                        "currency_hint": "US$",
                        "period_hint": "30 June 2025",
                    }
                ],
            }
        ]
        prepared_pages = {
            1: [
                {
                    "line_no": 1,
                    "text": "Guidance 30 June 2025 US$10m",
                    "words": [{"text": "Guidance", "x0": 0.0, "x1": 80.0}],
                    "numeric_words": [
                        {
                            "x_center": 220.0,
                            "value": 10_000_000.0,
                            "raw_value": "US$10m",
                            "currency": "US$",
                            "value_type": "amount",
                        }
                    ],
                    "section_kind": "financial",
                    "bbox": [0.0, 0.0, 400.0, 20.0],
                },
                {
                    "line_no": 2,
                    "text": "Revenue YoY 30 June 2025 12%",
                    "words": [
                        {"text": "Revenue", "x0": 0.0, "x1": 70.0},
                        {"text": "YoY", "x0": 72.0, "x1": 120.0},
                    ],
                    "numeric_words": [
                        {
                            "x_center": 220.0,
                            "value": 12.0,
                            "raw_value": "12%",
                            "currency": "",
                            "value_type": "percent",
                        }
                    ],
                    "section_kind": "financial",
                    "bbox": [0.0, 20.0, 400.0, 40.0],
                },
            ]
        }

        rows_default = EXTRACT.extract_metrics_from_blocks(
            pdf,
            blocks,
            strict_metric_rows_only=True,
            prepared_pages=prepared_pages,
        )
        metrics_default = {str(r.get("metric", "")) for r in rows_default}
        self.assertNotIn("guidance", metrics_default)
        self.assertNotIn("growth_pct", metrics_default)

        rows_expanded = EXTRACT.extract_metrics_from_blocks(
            pdf,
            blocks,
            strict_metric_rows_only=True,
            expanded_metric_scope=True,
            prepared_pages=prepared_pages,
        )
        metrics_expanded = {str(r.get("metric", "")) for r in rows_expanded}
        self.assertIn("guidance", metrics_expanded)
        self.assertIn("growth_pct", metrics_expanded)

    def test_extract_expanded_narrative_context_rows_tags_context_labels(self):
        text = "\n".join(
            [
                "FY26 guidance remains US$10m.",
                "Revenue YoY 12% in FY25.",
            ]
        )
        with mock.patch.object(EXTRACT, "extract_pdf_text", return_value=text):
            rows = EXTRACT.extract_expanded_narrative_context_rows(Path("dummy.pdf"))

        metrics = {str(r.get("metric", "")) for r in rows}
        self.assertIn("guidance", metrics)
        self.assertIn("growth_pct", metrics)
        self.assertTrue(rows)
        self.assertTrue(all(str(r.get("context_reason", "")) == "expanded_narrative_scope" for r in rows))
        self.assertTrue(all(not bool(r.get("inside_table")) for r in rows))
        self.assertTrue(all(str(r.get("source_mode", "")) == "expanded_narrative" for r in rows))

    def test_apply_unit_multiplier_for_thousands(self):
        row = {
            "metric": "cash_and_equivalents",
            "value_type": "amount",
            "raw_value": "4,585",
            "value": 4585.0,
        }
        out = EXTRACT.apply_unit_multiplier(row, 1000.0)
        self.assertEqual(out["value"], 4585000.0)

    def test_extracts_multiple_period_values_from_single_metric_line(self):
        line = (
            "Cash and cash equivalents amounted to $11,441,605 as at 31 December 2021 "
            "(30 June 2021: $22,015,560)."
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 192, line, strict_table_only=False)
        cash_rows = [r for r in rows if r["metric"] == "cash_and_equivalents" and r["value_type"] == "amount"]
        self.assertGreaterEqual(len(cash_rows), 2)
        by_period = {str(r["period"]): float(r["value"]) for r in cash_rows}
        self.assertEqual(by_period.get("31 December 2021"), 11441605.0)
        self.assertEqual(by_period.get("30 June 2021"), 22015560.0)

    def test_extract_period_labels_captures_months_ended_phrase(self):
        labels = EXTRACT.extract_period_labels("For the 3 months ended 31 December 2025")
        self.assertTrue(any("3 months ended 31 december 2025" in txt.lower() for _, txt in labels))

    def test_infer_region_period_hint_prefers_specific_label_over_bare_year(self):
        page_lines = [{"text": ""} for _ in range(14)]
        page_lines[1]["text"] = "2025"
        page_lines[2]["text"] = "Q4 2025"
        page_lines[3]["text"] = "31 December 2025"
        hint = EXTRACT.infer_region_period_hint(page_lines, start_idx=10, end_idx=11)
        self.assertIn("31 December 2025", hint)

    def test_column_period_fallback_sets_current_and_previous_quarter(self):
        current = EXTRACT._resolve_table_period_for_column(
            base_period="Q4 2025",
            row_label="Cash and cash equivalents at end of quarter",
            line_text="4,015",
            block_context="Current quarter Previous quarter",
            col_idx=0,
            ordered_col_indices=[0, 1],
        )
        previous = EXTRACT._resolve_table_period_for_column(
            base_period="Q4 2025",
            row_label="Cash and cash equivalents at end of quarter",
            line_text="6,278",
            block_context="Current quarter Previous quarter",
            col_idx=1,
            ordered_col_indices=[0, 1],
        )
        self.assertEqual(current, "Current quarter - Q4 2025")
        self.assertEqual(previous, "Previous quarter - 30 September 2025")

    def test_column_period_fallback_does_not_duplicate_relative_period(self):
        current = EXTRACT._resolve_table_period_for_column(
            base_period="Current quarter",
            row_label="Cash and cash equivalents at end of quarter",
            line_text="3,818",
            block_context="Current quarter",
            col_idx=0,
            ordered_col_indices=[0, 1],
        )
        self.assertEqual(current, "Current quarter")

    def test_column_period_fallback_uses_document_hint_for_current_quarter(self):
        current = EXTRACT._resolve_table_period_for_column(
            base_period="Current quarter",
            row_label="Cash and cash equivalents at end of quarter",
            line_text="3,818",
            block_context="Current quarter",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="31 December 2021",
        )
        self.assertEqual(current, "Current quarter - 31 December 2021")

    def test_column_period_fallback_handles_truncated_cash_row_label(self):
        current = EXTRACT._resolve_table_period_for_column(
            base_period="Current quarter",
            row_label="Cash and cash equivalents at end of",
            line_text="7,692",
            block_context="Current quarter Previous quarter",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="31 March 2024",
            statement_scope="appendix_statement",
        )
        previous = EXTRACT._resolve_table_period_for_column(
            base_period="Current quarter",
            row_label="Cash and cash equivalents at end of",
            line_text="8,952",
            block_context="Current quarter Previous quarter",
            col_idx=1,
            ordered_col_indices=[0, 1],
            document_period_hint="31 March 2024",
            statement_scope="appendix_statement",
        )
        self.assertEqual(current, "Current quarter - 31 March 2024")
        self.assertEqual(previous, "Previous quarter - 31 December 2023")

    def test_column_period_fallback_handles_previous_hint_in_first_column(self):
        current = EXTRACT._resolve_table_period_for_column(
            base_period="Previous quarter",
            row_label="Cash and cash equivalents at end of period",
            line_text="1,442",
            block_context="Current quarter Previous quarter",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="31 December 2023",
            statement_scope="appendix_statement",
        )
        previous = EXTRACT._resolve_table_period_for_column(
            base_period="Previous quarter",
            row_label="Cash and cash equivalents at end of period",
            line_text="1,442",
            block_context="Current quarter Previous quarter",
            col_idx=1,
            ordered_col_indices=[0, 1],
            document_period_hint="31 December 2023",
            statement_scope="appendix_statement",
        )
        self.assertEqual(current, "Current quarter - 31 December 2023")
        self.assertEqual(previous, "Previous quarter - 30 September 2023")

    def test_column_period_fallback_infers_previous_quarter_date(self):
        previous = EXTRACT._resolve_table_period_for_column(
            base_period="Current quarter",
            row_label="Cash and cash equivalents at end of quarter",
            line_text="4,179",
            block_context="Current quarter",
            col_idx=1,
            ordered_col_indices=[0, 1],
            document_period_hint="31 December 2021",
        )
        self.assertEqual(previous, "Previous quarter - 30 September 2021")

    def test_column_period_row_anchor_uses_column_year(self):
        p1 = EXTRACT._resolve_table_period_for_column(
            base_period="31 December 2021",
            row_label="Cash and cash equivalents at 1 July",
            line_text="22,015,560",
            block_context="Consolidated Statement of Cash Flows",
            col_idx=0,
            ordered_col_indices=[0, 1, 2],
        )
        p2 = EXTRACT._resolve_table_period_for_column(
            base_period="31 December 2020",
            row_label="Cash and cash equivalents at 1 July",
            line_text="2,364,440",
            block_context="Consolidated Statement of Cash Flows",
            col_idx=1,
            ordered_col_indices=[0, 1, 2],
        )
        self.assertEqual(p1, "1 July 2021")
        self.assertEqual(p2, "1 July 2020")

    def test_column_period_row_anchor_uses_doc_hint_year(self):
        p = EXTRACT._resolve_table_period_for_column(
            base_period="Current quarter",
            row_label="Cash and cash equivalents at 31 December",
            line_text="11,441,605",
            block_context="Current quarter",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="31 December 2021",
        )
        self.assertEqual(p, "31 December 2021")

    def test_column_period_upgrades_bare_year_using_doc_hint(self):
        p = EXTRACT._resolve_table_period_for_column(
            base_period="2022",
            row_label="Cash and cash equivalents at end of financial half-year",
            line_text="1,246,957",
            block_context="Statement of cash flows For the half-year ended 31 December 2022",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="31 December 2022",
        )
        self.assertEqual(p, "31 December 2022")

    def test_column_period_upgrades_bare_year_using_block_context_date(self):
        p = EXTRACT._resolve_table_period_for_column(
            base_period="2022",
            row_label="Cash and cash equivalents at end of financial half-year",
            line_text="1,246,957",
            block_context="Statement of cash flows For the half-year ended 31 December 2022 Consolidated 31 December 2022 2021",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="For the half-year ended 31 December 2021",
        )
        self.assertEqual(p, "31 December 2022")

    def test_column_period_maps_header_dates_with_ocr_split_month(self):
        p0 = EXTRACT._resolve_table_period_for_column(
            base_period="31 Dec 2021",
            row_label="Total Assets",
            line_text="48,945,121",
            block_context="Consolidated Statement of Financial Position as at 31 December 2021",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="31 December 2021",
            statement_scope="consolidated_statement",
            table_header_text="For Note 31 Dec 2021 30 J un 2021 (Restated) $ $",
        )
        p1 = EXTRACT._resolve_table_period_for_column(
            base_period="2021",
            row_label="Total Assets",
            line_text="50,750,599",
            block_context="Consolidated Statement of Financial Position as at 31 December 2021",
            col_idx=1,
            ordered_col_indices=[0, 1],
            document_period_hint="31 December 2021",
            statement_scope="consolidated_statement",
            table_header_text="For Note 31 Dec 2021 30 J un 2021 (Restated) $ $",
        )
        self.assertEqual(p0, "31 Dec 2021")
        self.assertEqual(p1, "30 June 2021")

    def test_column_period_maps_header_dates_with_extra_leading_numeric_column(self):
        p_current = EXTRACT._resolve_table_period_for_column(
            base_period="2025",
            row_label="Cash and cash equivalents at end of period",
            line_text="4,015",
            block_context="Consolidated statement of cash flows",
            col_idx=1,
            ordered_col_indices=[0, 1, 2],
            document_period_hint="31 March 2025",
            statement_scope="appendix_statement",
            table_header_text="As at 31 March 2025 31 December 2024",
        )
        p_previous = EXTRACT._resolve_table_period_for_column(
            base_period="2024",
            row_label="Cash and cash equivalents at end of period",
            line_text="6,278",
            block_context="Consolidated statement of cash flows",
            col_idx=2,
            ordered_col_indices=[0, 1, 2],
            document_period_hint="31 March 2025",
            statement_scope="appendix_statement",
            table_header_text="As at 31 March 2025 31 December 2024",
        )
        self.assertEqual(p_current, "31 March 2025")
        self.assertEqual(p_previous, "31 December 2024")

    def test_map_docling_header_date_to_value_column_handles_extra_leading_numeric_column(self):
        mapped_current = EXTRACT._map_docling_header_date_to_value_column(
            value_col_indices=[1, 2, 3],
            value_col_idx=2,
            header_dates=["31 March 2025", "31 December 2024"],
        )
        mapped_previous = EXTRACT._map_docling_header_date_to_value_column(
            value_col_indices=[1, 2, 3],
            value_col_idx=3,
            header_dates=["31 March 2025", "31 December 2024"],
        )
        self.assertEqual(mapped_current, "31 March 2025")
        self.assertEqual(mapped_previous, "31 December 2024")

    def test_extract_table_metrics_docling_emits_multiple_period_rows_for_multi_period_table(self):
        class _FakeRow:
            def __init__(self, values):
                self._values = list(values)

            def __len__(self):
                return len(self._values)

            @property
            def iloc(self):
                return self

            def __getitem__(self, idx):
                return self._values[idx]

        class _FakeDataFrame:
            def __init__(self, columns, rows):
                self.columns = list(columns)
                self.values = [list(r) for r in rows]
                self.empty = len(self.values) == 0

            def iterrows(self):
                for idx, row in enumerate(self.values):
                    yield idx, _FakeRow(row)

        class _FakeTable:
            def __init__(self, df):
                self._df = df

            def export_to_dataframe(self, doc=None):
                return self._df

        class _FakeDoc:
            def __init__(self, tables):
                self.tables = tables

        class _FakeConvertResult:
            def __init__(self, document):
                self.document = document

        class _FakeConverter:
            def __init__(self, tables):
                self._tables = tables

            def convert(self, _path):
                return _FakeConvertResult(_FakeDoc(self._tables))

        df = _FakeDataFrame(
            columns=["Item", "30 June 2025 $", "30 June 2024 $"],
            rows=[["Total assets", "9,982", "8,501"]],
        )
        converter = _FakeConverter([_FakeTable(df)])
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "dummy.pdf"
            pdf.write_text("%PDF-1.4\n", encoding="utf-8")
            rows, _, _ = EXTRACT.extract_table_metrics_docling(
                pdf,
                strict_metric_rows_only=True,
                source_kind="canonical_report",
                review_scope="all",
                include_blocks=False,
                converter=converter,
            )

        asset_rows = [r for r in rows if str(r.get("metric", "")).strip().lower() == "total_assets"]
        periods = {str(r.get("statement_period_end", "")).strip() for r in asset_rows}
        self.assertEqual(periods, {"2025-06-30", "2024-06-30"})
        self.assertEqual(len(asset_rows), 2)

    def test_extract_table_metrics_docling_attaches_table_statement_classification_and_diagnostics(self):
        class _FakeRow:
            def __init__(self, values):
                self._values = list(values)

            def __len__(self):
                return len(self._values)

            @property
            def iloc(self):
                return self

            def __getitem__(self, idx):
                return self._values[idx]

        class _FakeDataFrame:
            def __init__(self, columns, rows):
                self.columns = list(columns)
                self.values = [list(r) for r in rows]
                self.empty = len(self.values) == 0

            def iterrows(self):
                for idx, row in enumerate(self.values):
                    yield idx, _FakeRow(row)

        class _FakeTable:
            def __init__(self, df):
                self._df = df

            def export_to_dataframe(self, doc=None):
                return self._df

        class _FakeDoc:
            def __init__(self, tables):
                self.tables = tables

        class _FakeConvertResult:
            def __init__(self, document):
                self.document = document

        class _FakeConverter:
            def __init__(self, tables):
                self._tables = tables

            def convert(self, _path):
                return _FakeConvertResult(_FakeDoc(self._tables))

        df = _FakeDataFrame(
            columns=["Item", "30 June 2025 $"],
            rows=[
                ["Revenue", "120"],
                ["Gross profit", "60"],
                ["Net profit", "18"],
            ],
        )
        converter = _FakeConverter([_FakeTable(df)])
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "dummy.pdf"
            pdf.write_text("%PDF-1.4\n", encoding="utf-8")
            rows, blocks, split = EXTRACT.extract_table_metrics_docling(
                pdf,
                strict_metric_rows_only=True,
                source_kind="canonical_report",
                review_scope="all",
                include_blocks=True,
                converter=converter,
            )

        self.assertTrue(rows)
        self.assertTrue(all(r.get("table_statement_type") == "income_statement" for r in rows))
        self.assertTrue(all(float(r.get("table_statement_confidence", 0.0)) > 0.0 for r in rows))
        self.assertEqual(blocks[0].get("table_statement_type"), "income_statement")
        self.assertEqual(split["diagnostics"].get("table_statement_type_counts"), {"income_statement": 1})
        self.assertFalse(split["diagnostics"].get("identity_resolution_applied"))
        self.assertEqual(split["diagnostics"].get("identity_resolution_conflicts"), 0)

    def test_extract_table_metrics_docling_resolves_duplicate_ebit_with_identity(self):
        class _FakeRow:
            def __init__(self, values):
                self._values = list(values)

            def __len__(self):
                return len(self._values)

            @property
            def iloc(self):
                return self

            def __getitem__(self, idx):
                return self._values[idx]

        class _FakeDataFrame:
            def __init__(self, columns, rows):
                self.columns = list(columns)
                self.values = [list(r) for r in rows]
                self.empty = len(self.values) == 0

            def iterrows(self):
                for idx, row in enumerate(self.values):
                    yield idx, _FakeRow(row)

        class _FakeTable:
            def __init__(self, df):
                self._df = df

            def export_to_dataframe(self, doc=None):
                return self._df

        class _FakeDoc:
            def __init__(self, tables):
                self.tables = tables

        class _FakeConvertResult:
            def __init__(self, document):
                self.document = document

        class _FakeConverter:
            def __init__(self, tables):
                self._tables = tables

            def convert(self, _path):
                return _FakeConvertResult(_FakeDoc(self._tables))

        df = _FakeDataFrame(
            columns=["Item", "30 June 2025 $"],
            rows=[
                ["EBITDA", "100"],
                ["Depreciation and amortisation", "20"],
                ["Operating profit", "80"],
                ["Operating profit", "90"],
            ],
        )
        converter = _FakeConverter([_FakeTable(df)])
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "dummy.pdf"
            pdf.write_text("%PDF-1.4\n", encoding="utf-8")
            rows, _, split = EXTRACT.extract_table_metrics_docling(
                pdf,
                strict_metric_rows_only=True,
                source_kind="canonical_report",
                review_scope="all",
                include_blocks=True,
                converter=converter,
            )

        ebit_rows = [r for r in rows if str(r.get("metric", "")).strip().lower() == "ebit"]
        self.assertEqual(len(ebit_rows), 1)
        self.assertEqual(ebit_rows[0].get("value"), 80.0)
        identity_demoted = [
            r for r in split["context_rows"] if r.get("context_reason") == "identity_resolved_same_period"
        ]
        self.assertEqual(len(identity_demoted), 1)
        self.assertEqual(identity_demoted[0].get("value"), 90.0)
        self.assertTrue(split["diagnostics"].get("identity_resolution_applied"))
        self.assertEqual(split["diagnostics"].get("identity_resolution_conflicts"), 1)

    def test_split_rows_by_scope_demotes_metric_when_table_statement_type_conflicts(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "operating_cash_flow",
                "raw_value": "42",
                "value": 42.0,
                "value_type": "amount",
                "currency": "$",
                "period": "31 December 2025",
                "statement_period": "31 December 2025",
                "statement_period_end": "2025-12-31",
                "line": "42",
                "row_label": "Operating cash flow",
                "table_header_text": "Revenue Gross profit Net profit",
                "inside_table": True,
                "source_mode": "docling_table",
                "statement_scope": "consolidated_statement",
                "statement_title": "Statement of profit or loss",
                "statement_family": "income_statement",
                "table_statement_type": "income_statement",
                "table_statement_confidence": 0.8,
            }
        ]

        split = EXTRACT.split_rows_by_scope(rows)

        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "statement_type_metric_conflict")

    def test_column_period_prefers_explicit_base_date_over_out_of_order_header_dates(self):
        p_left = EXTRACT._resolve_table_period_for_column(
            base_period="30 June 2023",
            row_label="Total current assets",
            line_text="517,463",
            block_context="Consolidated statement of financial position",
            col_idx=0,
            ordered_col_indices=[0, 1],
            statement_scope="appendix_statement",
            table_header_text="Adjusted 30 June 2022 Notes 30 June 2023",
        )
        p_right = EXTRACT._resolve_table_period_for_column(
            base_period="30 June 2022",
            row_label="Total current assets",
            line_text="1,010,121",
            block_context="Consolidated statement of financial position",
            col_idx=1,
            ordered_col_indices=[0, 1],
            statement_scope="appendix_statement",
            table_header_text="Adjusted 30 June 2022 Notes 30 June 2023",
        )
        self.assertEqual(p_left, "30 June 2023")
        self.assertEqual(p_right, "30 June 2022")

    def test_column_period_appendix_fallback_uses_doc_hint_when_header_missing(self):
        current = EXTRACT._resolve_table_period_for_column(
            base_period="",
            row_label="Cash and cash equivalents at beginning of period",
            line_text="9,214",
            block_context="Net increase / (decrease) in cash and cash equivalents for the period",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="30 September 2025",
            statement_scope="appendix_statement",
        )
        previous = EXTRACT._resolve_table_period_for_column(
            base_period="",
            row_label="Cash and cash equivalents at beginning of period",
            line_text="15,727",
            block_context="Net increase / (decrease) in cash and cash equivalents for the period",
            col_idx=1,
            ordered_col_indices=[0, 1],
            document_period_hint="30 September 2025",
            statement_scope="appendix_statement",
        )
        self.assertEqual(current, "Current quarter - 30 September 2025")
        self.assertEqual(previous, "Previous quarter - 30 June 2025")

    def test_column_period_quarter_mapping_uses_rightmost_two_columns(self):
        current = EXTRACT._resolve_table_period_for_column(
            base_period="Current quarter",
            row_label="Cash and cash equivalents at end of quarter",
            line_text="7,692",
            block_context="Current quarter Previous quarter",
            col_idx=1,
            ordered_col_indices=[0, 1, 2],
            document_period_hint="31 March 2024",
            statement_scope="appendix_statement",
        )
        previous = EXTRACT._resolve_table_period_for_column(
            base_period="Current quarter",
            row_label="Cash and cash equivalents at end of quarter",
            line_text="8,952",
            block_context="Current quarter Previous quarter",
            col_idx=2,
            ordered_col_indices=[0, 1, 2],
            document_period_hint="31 March 2024",
            statement_scope="appendix_statement",
        )
        self.assertEqual(current, "Current quarter - 31 March 2024")
        self.assertEqual(previous, "Previous quarter - 31 December 2023")

    def test_column_period_bare_year_uses_doc_hint_day_month_anchor(self):
        p = EXTRACT._resolve_table_period_for_column(
            base_period="2021",
            row_label="Cash and cash equivalents at end of period",
            line_text="22,015,560",
            block_context="Consolidated statement of financial position",
            col_idx=1,
            ordered_col_indices=[0, 1],
            document_period_hint="As at 30 June 2022",
            statement_scope="consolidated_statement",
        )
        self.assertEqual(p, "30 June 2021")

    def test_parse_line_accepts_cash_metric_with_at_the_end_phrase(self):
        line = "Cash and cash equivalents at the end of the financial half-year 1,246,957 3,817,956"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 555, line, strict_table_only=False)
        cash_rows = [r for r in rows if r.get("metric") == "cash_and_equivalents"]
        self.assertGreaterEqual(len(cash_rows), 1)

    def test_extract_statement_scope_header_skips_page_footer(self):
        lines = [
            "Consolidated statement of cash flows",
            "Page 2 of 5",
        ]
        header = EXTRACT.extract_statement_scope_header(lines)
        self.assertEqual(header, "Consolidated statement of cash flows")

    def test_extract_statement_scope_header_prefers_statement_over_notes_to_the(self):
        """When both a statement title and 'Notes to the financial statements' appear, prefer the statement."""
        lines = [
            "Consolidated statement of comprehensive income",
            "Revenue 100 90",
            "Cost of sales (40) (35)",
            "Some other content",
            "Notes to the financial statements",
        ]
        header = EXTRACT.extract_statement_scope_header(lines)
        self.assertEqual(
            header,
            "Consolidated statement of comprehensive income",
            "should prefer statement title over generic 'notes to the' section heading",
        )

    def test_extract_statement_scope_header_returns_notes_to_the_when_no_statement(self):
        """When only 'Notes to the financial statements' exists in context, return it."""
        lines = [
            "Directors' report",
            "Notes to the financial statements",
        ]
        header = EXTRACT.extract_statement_scope_header(lines)
        self.assertIn("Notes to the", header)

    def test_previous_quarter_label_from_q_year_hint(self):
        self.assertEqual(EXTRACT._previous_quarter_label_from_hint("Q4 2025"), "30 September 2025")

    def test_infer_document_period_hint_uses_split_period_ending_date(self):
        by_page = {
            1: [
                {"text": "27 January 2022"},
                {"text": "activity report and Appendix 4C for the period ending 31 December"},
                {"text": "2021."},
            ]
        }
        hint = EXTRACT.infer_document_period_hint(by_page)
        self.assertEqual(hint, "31 December 2021")

    def test_extract_explicit_date_labels_handles_split_month_tokens(self):
        labels = EXTRACT._extract_explicit_date_labels("31 Dec 2021 30 J un 2021")
        self.assertIn("31 Dec 2021", labels)
        self.assertIn("30 June 2021", labels)

    def test_extract_explicit_date_labels_handles_split_day_month_year_sequences(self):
        labels = EXTRACT._extract_explicit_date_labels("As at 31 March 31 December 2025 2024")
        self.assertIn("31 March 2025", labels)
        self.assertIn("31 December 2024", labels)

    def test_extract_explicit_date_labels_as_at_dd_mon_yy_prospectus(self):
        """Prospectus balance sheet headers: AS AT 30-JUN-25, 30-JUN-24."""
        text = "PEAK VIEW EXPLORATION PTY LTD AS AT 30-JUN-25 UNAUDITED $ AS AT 30-JUN-24 UNAUDITED $"
        labels = EXTRACT._extract_explicit_date_labels(text)
        self.assertIn("30 June 2025", labels)
        self.assertIn("30 June 2024", labels)
        # Without "AS AT" prefix
        labels2 = EXTRACT._extract_explicit_date_labels("30-JUN-25 and 31-DEC-24")
        self.assertIn("30 June 2025", labels2)
        self.assertIn("31 December 2024", labels2)

    def test_extract_explicit_date_labels_2digit_year_boundaries(self):
        """2-digit year boundaries: 00→2000, 50→2050, 51→1951, 99→1999."""
        self.assertIn("1 January 2000", EXTRACT._extract_explicit_date_labels("AS AT 01-JAN-00"))
        self.assertIn("30 June 2050", EXTRACT._extract_explicit_date_labels("AS AT 30-JUN-50"))
        self.assertIn("31 December 1951", EXTRACT._extract_explicit_date_labels("31-DEC-51"))
        self.assertIn("1 July 1999", EXTRACT._extract_explicit_date_labels("01-JUL-99"))

    def test_extract_explicit_date_labels_four_digit_year(self):
        """4-digit year: AS AT 30-JUN-2025 → 30 June 2025."""
        labels = EXTRACT._extract_explicit_date_labels("AS AT 30-JUN-2025")
        self.assertIn("30 June 2025", labels)

    def test_extract_explicit_date_labels_invalid_month_skipped(self):
        """Invalid month 30-XYZ-25 must not appear; 30-JUN-25 in same string must still appear."""
        labels = EXTRACT._extract_explicit_date_labels("30-XYZ-25 30-JUN-25")
        self.assertNotIn("30 XYZ 2025", labels)
        self.assertIn("30 June 2025", labels)

    def test_extract_explicit_date_labels_invalid_day_skipped(self):
        """Invalid day 31-FEB-25 must not appear in output (result empty for that string)."""
        labels = EXTRACT._extract_explicit_date_labels("31-FEB-25")
        self.assertEqual(labels, [])

    def test_resolve_table_period_for_column_maps_header_dates_left_to_right(self):
        """Column mapping: header 'AS AT 30-JUN-25 AS AT 30-JUN-24' maps col 0→30 June 2025, col 1→30 June 2024."""
        table_header_text = "AS AT 30-JUN-25 AS AT 30-JUN-24"
        p0 = EXTRACT._resolve_table_period_for_column(
            base_period="",
            row_label="",
            line_text="",
            block_context="",
            col_idx=0,
            ordered_col_indices=[0, 1],
            document_period_hint="",
            table_header_text=table_header_text,
            statement_scope="consolidated_statement",
        )
        p1 = EXTRACT._resolve_table_period_for_column(
            base_period="",
            row_label="",
            line_text="",
            block_context="",
            col_idx=1,
            ordered_col_indices=[0, 1],
            document_period_hint="",
            table_header_text=table_header_text,
            statement_scope="consolidated_statement",
        )
        self.assertEqual(p0, "30 June 2025")
        self.assertEqual(p1, "30 June 2024")

    def test_normalize_period_for_db_handles_quarter_dates(self):
        end1, sort1 = EXTRACT.normalize_period_for_db("Current quarter - 31 December 2021", doc_date="2022-01-27")
        end2, sort2 = EXTRACT.normalize_period_for_db("Previous quarter - 30 September 2021", doc_date="2022-01-27")
        self.assertEqual(end1, "2021-12-31")
        self.assertEqual(sort1, "2021-12-31")
        self.assertEqual(end2, "2021-09-30")
        self.assertEqual(sort2, "2021-09-30")

    def test_normalize_period_for_db_falls_back_to_doc_date(self):
        end, sort = EXTRACT.normalize_period_for_db("Previous quarter", doc_date="2022-01-27")
        self.assertEqual(end, "")
        self.assertEqual(sort, "2022-01-27")

    def test_normalize_period_for_db_can_disable_doc_date_fallback(self):
        end, sort = EXTRACT.normalize_period_for_db(
            "Previous quarter",
            doc_date="2022-01-27",
            allow_doc_date_fallback=False,
        )
        self.assertEqual(end, "")
        self.assertEqual(sort, "")

    def test_normalize_period_for_db_current_quarter_snaps_to_quarter_end(self):
        end, sort = EXTRACT.normalize_period_for_db("Current quarter - 28 January 2022", doc_date="2022-01-28")
        self.assertEqual(end, "2021-12-31")
        self.assertEqual(sort, "2021-12-31")

    def test_normalize_period_for_db_previous_quarter_snaps_using_anchor(self):
        end, sort = EXTRACT.normalize_period_for_db("Previous quarter - 31 July 2023", doc_date="2023-07-31")
        self.assertEqual(end, "2023-03-31")
        self.assertEqual(sort, "2023-03-31")

    def test_store_metrics_sqlite_orders_by_period_sort_key(self):
        rows = [
            {
                "file": "/tmp/docs/AAA/financial_performance/2022-01-27_report.pdf",
                "line_no": 412,
                "metric": "cash_and_equivalents",
                "value_type": "amount",
                "raw_value": "3,818",
                "value": 3818.0,
                "currency": "A$",
                "period": "Current quarter - 31 December 2021",
                "statement_scope": "appendix_statement",
                "inside_table": True,
                "table_id": "t1",
                "block_id": "b1",
                "page_number": 7,
            },
            {
                "file": "/tmp/docs/AAA/financial_performance/2022-01-27_report.pdf",
                "line_no": 413,
                "metric": "cash_and_equivalents",
                "value_type": "amount",
                "raw_value": "4,179",
                "value": 4179.0,
                "currency": "A$",
                "period": "Previous quarter - 30 September 2021",
                "statement_scope": "appendix_statement",
                "inside_table": True,
                "table_id": "t1",
                "block_id": "b1",
                "page_number": 7,
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "financial_metrics.sqlite"
            written = EXTRACT.store_metrics_sqlite(rows, db_path)
            self.assertEqual(written, 2)
            conn = sqlite3.connect(str(db_path))
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT period_sort_date FROM financial_metrics ORDER BY period_sort_key ASC, line_no ASC"
                )
                got = [r[0] for r in cur.fetchall()]
                self.assertEqual(got, ["2021-09-30", "2021-12-31"])
            finally:
                conn.close()

    def test_strict_mode_rejects_liquidity_risk_narrative_cash_line(self):
        line = (
            "As at 31 March 2025, the Company had available a cash and cash equivalents balance of "
            "$13,068,842 (31 December 2024 - $15,726,784) to settle current liabilities of "
            "$4,357,947 (31 December 2024 - $4,085,000)."
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1066, line, strict_table_only=True, active_section="liquidity risk")
        self.assertEqual(rows, [])

    def test_strict_mode_rejects_presentational_cash_narrative(self):
        line = "robust cash balance of approximately C$8.3 million (A$9.0 million) setting us up for an active"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 139, line, strict_table_only=True, active_section="chairman's letter")
        self.assertEqual(rows, [])

    def test_strict_mode_extracts_loss_after_tax_statement_row(self):
        line = (
            "Loss after income tax expense for the period attributable to the owners of Matador Mining Ltd    "
            "(1,889,766)   (5,054,251)"
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 220, line, strict_table_only=True, active_section="statement of profit or loss")
        ni_rows = [r for r in rows if r["metric"] == "net_income" and r["value_type"] == "amount"]
        self.assertTrue(ni_rows)
        self.assertEqual(ni_rows[0]["raw_value"], "(1,889,766)")

    def test_strict_mode_rejects_statutory_revenue_highlight_sentence(self):
        line = "Revenue on a statutory basis of $600.7 million, $166.3 million higher than the prior period;"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 8124, line, strict_table_only=True, active_section="strong financial performance and low gearing")
        self.assertEqual(rows, [])

    def test_strict_mode_rejects_metric_heading_with_footnote_refs(self):
        line = "EBITDA 1, 2"
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 9859, line, strict_table_only=True, active_section="strong financial performance and low gearing")
        self.assertEqual(rows, [])

    def test_strict_mode_rejects_customer_concentration_narrative(self):
        line = (
            "Revenue from one customer represented approximately $346,837 thousand and "
            "$154,146 thousand of Golden Grove and Capricorn Copper total revenue"
        )
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 9001, line, strict_table_only=True, active_section="notes to the financial statements")
        self.assertEqual(rows, [])

    def test_classify_financial_statement_parent(self):
        section_text = (
            "Note 29 Parent entity information\n"
            "Statement of profit or loss\n"
            "Parent\n"
            "Loss after income tax"
        )
        self.assertEqual(EXTRACT.classify_financial_statement(section_text), "parent_statement")

    def test_classify_financial_statement_consolidated(self):
        section_text = (
            "Consolidated statement of profit or loss and other comprehensive income\n"
            "For the year ended 30 June 2022"
        )
        self.assertEqual(EXTRACT.classify_financial_statement(section_text), "consolidated_statement")

    def test_classify_statement_scope_appendix_marker_only_is_non_canonical(self):
        scope, reason = EXTRACT.classify_statement_scope(
            block_text="Quarterly cash flow report, Appendix 4C",
            header_text="Appendix 4C",
            source_kind="canonical_report",
        )
        self.assertEqual(scope, "other")
        self.assertEqual(reason, "appendix_marker_without_layout")

    def test_classify_statement_scope_appendix_report_form_layout(self):
        scope, reason = EXTRACT.classify_statement_scope(
            block_text="Item 5.5 Cash and cash equivalents at end of quarter",
            header_text="Appendix 5B Quarterly cash flow report",
            source_kind="appendix_report",
        )
        self.assertEqual(scope, "appendix_statement")
        self.assertEqual(reason, "appendix_source_kind")

    def test_classify_statement_scope_appendix_report_prefers_appendix_scope(self):
        scope, reason = EXTRACT.classify_statement_scope(
            block_text="Consolidated statement of cash flows Item 5.5 Cash and cash equivalents at end of quarter",
            header_text="Appendix 5B Quarterly cash flow report",
            source_kind="appendix_report",
        )
        self.assertEqual(scope, "appendix_statement")
        self.assertEqual(reason, "appendix_source_kind")

    def test_classify_statement_scope_appendix_marker_metric_table(self):
        scope, reason = EXTRACT.classify_statement_scope(
            block_text="NPAT to EBITDA reconciliation Revenue EBITDA NPAT 2021 2020",
            header_text="APPENDIX 4E AND ANNUAL FINANCIAL REPORT",
            source_kind="canonical_report",
        )
        self.assertEqual(scope, "appendix_statement")
        self.assertEqual(reason, "appendix_metric_table")

    def test_classify_statement_scope_notes_to_section_is_note_disclosure(self):
        scope, reason = EXTRACT.classify_statement_scope(
            block_text="NOTES TO THE CONSOLIDATED STATEMENT OF CASH FLOWS\nNote 12: ...",
            header_text="for the year ended 31 December 2021",
            source_kind="canonical_report",
        )
        self.assertEqual(scope, "note_disclosure")
        self.assertEqual(reason, "note_marker")

    def test_classify_statement_scope_canonical_report_generic_notes_to_the_is_consolidated(self):
        """Generic 'notes to the financial statements' without Note N: primary statement stays consolidated."""
        scope, reason = EXTRACT.classify_statement_scope(
            block_text="Consolidated statement of comprehensive income Revenue 100 Cost of sales (40)",
            header_text="Notes to the financial statements For the year ended 30 June 2025",
            source_kind="canonical_report",
        )
        self.assertEqual(scope, "consolidated_statement", f"expected consolidated_statement, got {scope!r} ({reason!r})")
        self.assertIn(reason, ("canonical_layout_source_kind", "consolidated_layout"))

    def test_classify_statement_scope_for_note_year_header_is_not_note(self):
        scope, reason = EXTRACT.classify_statement_scope(
            block_text="Consolidated statement of comprehensive income Revenue Cost of sales",
            header_text="For Note 2020 $'000 2019 $'000",
            source_kind="canonical_report",
        )
        self.assertEqual(scope, "consolidated_statement")
        self.assertEqual(reason, "consolidated_layout")

    def test_classify_statement_scope_parent_entity_financial_information(self):
        scope, reason = EXTRACT.classify_statement_scope(
            block_text="Balance sheet Assets Current assets Non-current assets Total assets",
            header_text="31 Parent entity financial information",
            source_kind="appendix_report",
        )
        self.assertEqual(scope, "parent_statement")
        self.assertEqual(reason, "parent_marker")

    def test_infer_statement_family_from_titles(self):
        self.assertEqual(
            EXTRACT.infer_statement_family("Consolidated statement of financial position", "consolidated_statement"),
            "balance_sheet",
        )
        self.assertEqual(
            EXTRACT.infer_statement_family("Consolidated statement of cash flows", "appendix_statement"),
            "cash_flow",
        )
        self.assertEqual(
            EXTRACT.infer_statement_family("Consolidated statement of comprehensive income", "consolidated_statement"),
            "income_statement",
        )
        self.assertEqual(
            EXTRACT.infer_statement_family(
                "APPENDIX 4E AND ANNUAL FINANCIAL REPORT",
                "appendix_statement",
                context_text="NPAT TO EBITDA reconciliation Revenue EBITDA",
            ),
            "income_statement",
        )
        self.assertEqual(
            EXTRACT.infer_statement_family(
                "APPENDIX 4E AND ANNUAL FINANCIAL REPORT",
                "appendix_statement",
                context_text="Assets Current assets Total liabilities Net assets",
            ),
            "balance_sheet",
        )

    def test_infer_statement_family_detects_equity_rollforward_context(self):
        fam = EXTRACT.infer_statement_family(
            "Consolidated statement of changes in equity",
            "consolidated_statement",
            "Retained earnings opening balance and dividends paid",
        )
        self.assertEqual(fam, "equity_statement")

    def test_infer_metric_alias_for_total_equity_net_assets(self):
        alias = EXTRACT.infer_metric_alias("total_equity", row_label="Net assets", line_text="42,287,136")
        self.assertEqual(alias, "net_assets")

    def test_canonical_confidence_score_rewards_strong_row(self):
        row = {
            "metric": "revenue",
            "statement_scope": "consolidated_statement",
            "statement_family": "income_statement",
            "period": "31 December 2025",
            "table_header_text": "For the year ended 31 December 2025 2024",
            "statement_title": "Consolidated statement of comprehensive income",
            "row_label": "Revenue",
            "line": "600,762",
        }
        score = EXTRACT.canonical_confidence_score(row, {"income_statement"})
        self.assertGreaterEqual(score, 3)

    def test_resolve_canonical_conflicts_keeps_higher_confidence_row(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_equity",
                "metric_variant": "",
                "statement_period_end": "2025-12-31",
                "balance_position": "",
                "value": 100.0,
                "raw_value": "100",
                "currency": "$",
                "line_no": 10,
                "row_label": "Net assets",
                "statement_title": "Consolidated statement of financial position",
                "table_header_text": "As at 31 December 2025 2024",
                "canonical_confidence_score": 4,
            },
            {
                "file": "a.pdf",
                "metric": "total_equity",
                "metric_variant": "",
                "statement_period_end": "2025-12-31",
                "balance_position": "",
                "value": 90.0,
                "raw_value": "90",
                "currency": "$",
                "line_no": 11,
                "row_label": "Net assets",
                "statement_title": "Page 2 of 5",
                "table_header_text": "Impact on consolidated statement of financial position previously disclosed",
                "canonical_confidence_score": 1,
            },
        ]
        kept, demoted = EXTRACT.resolve_canonical_conflicts(rows)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(demoted), 1)
        self.assertEqual(kept[0]["raw_value"], "100")
        self.assertEqual(demoted[0].get("context_reason"), "canonical_conflict_same_period")

    def test_resolve_canonical_conflicts_dedupes_identical_values(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "net_debt",
                "metric_variant": "",
                "statement_period_end": "2024-06-30",
                "balance_position": "",
                "value": 9120.0,
                "raw_value": "9,120",
                "currency": "$",
                "line_no": 100,
                "row_label": "Net debt",
                "statement_title": "Consolidated statement of financial position",
                "table_header_text": "As at 30 June 2024",
                "canonical_confidence_score": 4,
            },
            {
                "file": "a.pdf",
                "metric": "net_debt",
                "metric_variant": "",
                "statement_period_end": "2024-06-30",
                "balance_position": "",
                "value": 9120.0,
                "raw_value": "9,120",
                "currency": "$",
                "line_no": 120,
                "row_label": "Net debt",
                "statement_title": "Consolidated statement of financial position",
                "table_header_text": "As at 30 June 2024",
                "canonical_confidence_score": 3,
            },
        ]
        kept, demoted = EXTRACT.resolve_canonical_conflicts(rows)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(demoted), 1)
        self.assertEqual(demoted[0].get("context_reason"), "canonical_duplicate_same_period")

    def test_resolve_canonical_conflicts_dedupes_across_files_for_same_entity(self):
        rows = [
            {
                "file": "/tmp/docs/BHP/financial_performance/a.pdf",
                "metric": "revenue",
                "metric_variant": "",
                "statement_period_end": "2021-06-30",
                "balance_position": "",
                "value": 60817.0,
                "raw_value": "60,817",
                "currency": "US$",
                "line_no": 20,
                "row_label": "Revenue",
                "statement_title": "Consolidated statement of comprehensive income",
                "table_header_text": "for the year ended 30 June 2021",
                "canonical_confidence_score": 4,
            },
            {
                "file": "/tmp/docs/BHP/financial_performance/b.pdf",
                "metric": "revenue",
                "metric_variant": "",
                "statement_period_end": "2021-06-30",
                "balance_position": "",
                "value": 60900.0,
                "raw_value": "60,900",
                "currency": "US$",
                "line_no": 25,
                "row_label": "Revenue",
                "statement_title": "Consolidated statement of comprehensive income",
                "table_header_text": "for the year ended 30 June 2021",
                "canonical_confidence_score": 2,
            },
        ]
        kept, demoted = EXTRACT.resolve_canonical_conflicts(rows)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(demoted), 1)
        self.assertEqual(kept[0]["raw_value"], "60,817")
        self.assertEqual(demoted[0].get("context_reason"), "canonical_conflict_same_period")
        self.assertEqual(demoted[0].get("canonical_conflict_winner_file"), kept[0]["file"])

    def test_mark_primary_metric_rows_selects_single_variant_per_metric_period(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "revenue",
                "metric_variant": "reported",
                "statement_period_end": "2025-12-31",
                "balance_position": "",
                "value_type": "amount",
                "value": 100.0,
                "raw_value": "100",
                "currency": "US$",
                "line_no": 10,
                "row_label": "Revenue",
                "statement_title": "Consolidated statement of comprehensive income",
                "table_header_text": "for the year ended 31 December 2025",
                "canonical_confidence_score": 4,
                "source_mode": "table_bbox",
            },
            {
                "file": "a.pdf",
                "metric": "revenue",
                "metric_variant": "underlying",
                "statement_period_end": "2025-12-31",
                "balance_position": "",
                "value_type": "amount",
                "value": 120.0,
                "raw_value": "120",
                "currency": "US$",
                "line_no": 11,
                "row_label": "Underlying revenue",
                "statement_title": "Consolidated statement of comprehensive income",
                "table_header_text": "for the year ended 31 December 2025",
                "canonical_confidence_score": 3,
                "source_mode": "table_bbox",
            },
        ]
        EXTRACT.mark_primary_metric_rows(rows)
        primary = [r for r in rows if bool(r.get("primary_metric_value"))]
        self.assertEqual(len(primary), 1)
        self.assertEqual(primary[0]["metric_variant"], "reported")
        loser = [r for r in rows if not bool(r.get("primary_metric_value"))][0]
        self.assertEqual(loser.get("primary_conflict_winner_file"), "a.pdf")
        self.assertEqual(loser.get("primary_conflict_winner_line_no"), 10)

    def test_classify_pdf_source_kind_detects_appendix_filename_with_prefix(self):
        pdf = Path("x__2022-01-27_appendix-4c-quarterly-activity-report.pdf")
        self.assertEqual(EXTRACT.classify_pdf_source_kind(pdf), "appendix_report")

    def test_classify_pdf_source_kind_detects_appendix_filename_with_underscore_suffix(self):
        pdf = Path("x__2022-10-31_september-quarterly-report-appendix-4c_abc123.pdf")
        self.assertEqual(EXTRACT.classify_pdf_source_kind(pdf), "appendix_report")

    def test_row_label_aligned_lines_finds_same_y_label(self):
        page_lines = [
            {
                "text": "18,080",
                "bbox": [400.0, 507.4, 435.3, 517.6],
                "numeric_words": [{"minor_for_table": False}],
            },
            {
                "text": "Net foreign exchange rate difference",
                "bbox": [79.3, 507.4, 243.9, 517.6],
                "numeric_words": [],
            },
        ]
        label = EXTRACT._row_label_text_from_aligned_lines(
            page_lines=page_lines,
            start_idx=0,
            end_idx=1,
            target_idx=0,
            first_col_x=380.0,
        )
        self.assertEqual(label, "Net foreign exchange rate difference")

    def test_row_label_aligned_lines_maps_stacked_numeric_rows(self):
        def mk_line(text: str, y: float, has_numeric: bool = False):
            return {
                "text": text,
                "bbox": [40.0 if not has_numeric else 400.0, y, 260.0 if not has_numeric else 470.0, y + 8.0],
                "numeric_words": [{"minor_for_table": False}] if has_numeric else [],
            }

        page_lines = [
            mk_line("Current assets", 0.0),
            mk_line("Cash and cash equivalents", 12.0),
            mk_line("Trade and other receivables", 24.0),
            mk_line("Inventories", 36.0),
            mk_line("Current tax receivables", 48.0),
            mk_line("Total current assets", 60.0),
            mk_line("11", 72.0),
            mk_line("14", 84.0),
            mk_line("16", 96.0),
            mk_line("372,592", 108.0, has_numeric=True),
            mk_line("149,040", 120.0, has_numeric=True),
            mk_line("202,157", 132.0, has_numeric=True),
            mk_line("-", 144.0),
            mk_line("723,789", 156.0, has_numeric=True),
            mk_line("335,164", 168.0, has_numeric=True),
            mk_line("86,207", 180.0, has_numeric=True),
            mk_line("259,909", 192.0, has_numeric=True),
            mk_line("1,467", 204.0, has_numeric=True),
            mk_line("682,747", 216.0, has_numeric=True),
            mk_line("Non-current assets", 228.0),
        ]

        current_period_total = EXTRACT._row_label_text_from_aligned_lines(
            page_lines=page_lines,
            start_idx=0,
            end_idx=len(page_lines) - 1,
            target_idx=13,
            first_col_x=380.0,
        )
        prior_period_total = EXTRACT._row_label_text_from_aligned_lines(
            page_lines=page_lines,
            start_idx=0,
            end_idx=len(page_lines) - 1,
            target_idx=18,
            first_col_x=380.0,
        )
        prior_period_cash = EXTRACT._row_label_text_from_aligned_lines(
            page_lines=page_lines,
            start_idx=0,
            end_idx=len(page_lines) - 1,
            target_idx=14,
            first_col_x=380.0,
        )
        self.assertEqual(current_period_total, "Total current assets")
        self.assertEqual(prior_period_total, "Total current assets")
        self.assertEqual(prior_period_cash, "Cash and cash equivalents")

    def test_row_label_aligned_lines_stacked_mapping_requires_well_formed_band(self):
        def mk_line(text: str, y: float, has_numeric: bool = False):
            return {
                "text": text,
                "bbox": [40.0 if not has_numeric else 400.0, y, 260.0 if not has_numeric else 470.0, y + 8.0],
                "numeric_words": [{"minor_for_table": False}] if has_numeric else [],
            }

        # 3 labels but only 5 value rows -> misaligned band (not a clean multiple).
        page_lines = [
            mk_line("Cash and cash equivalents", 0.0),
            mk_line("Trade and other receivables", 12.0),
            mk_line("Total current assets", 24.0),
            mk_line("11", 36.0),
            mk_line("372,592", 48.0, has_numeric=True),
            mk_line("149,040", 60.0, has_numeric=True),
            mk_line("723,789", 72.0, has_numeric=True),
            mk_line("335,164", 84.0, has_numeric=True),
            mk_line("86,207", 96.0, has_numeric=True),
            mk_line("Non-current assets", 108.0),
        ]
        label = EXTRACT._row_label_text_from_aligned_lines(
            page_lines=page_lines,
            start_idx=0,
            end_idx=len(page_lines) - 1,
            target_idx=8,
            first_col_x=380.0,
        )
        self.assertEqual(label, "")

    def test_row_label_aligned_lines_ignores_footer_text_candidates(self):
        page_lines = [
            {
                "text": "349,398",
                "bbox": [400.0, 10.0, 470.0, 18.0],
                "numeric_words": [{"minor_for_table": False}],
            },
            {
                "text": "For personal use only",
                "bbox": [40.0, 10.0, 210.0, 18.0],
                "numeric_words": [],
            },
        ]
        label = EXTRACT._row_label_text_from_aligned_lines(
            page_lines=page_lines,
            start_idx=0,
            end_idx=1,
            target_idx=0,
            first_col_x=380.0,
        )
        self.assertEqual(label, "")

    def test_parse_line_accepts_total_current_assets_row(self):
        line = "Total current assets 723,789 682,747"
        rows = EXTRACT.parse_line(
            Path("dummy.pdf"),
            1,
            line,
            strict_table_only=True,
            active_section="statement of financial position",
            statement_type="consolidated_statement",
            statement_scope_header="Consolidated statement of financial position",
        )
        cur_assets = [r for r in rows if r.get("metric") == "current_assets" and r.get("value_type") == "amount"]
        self.assertTrue(cur_assets)
        self.assertEqual(cur_assets[0].get("raw_value"), "723,789")

    def test_segment_statement_blocks_appendix_preserves_balance_sheet_title(self):
        page_lines = [
            {"text": "APPENDIX 4E", "bbox": [0.0, 0.0, 200.0, 8.0], "line_no": 1, "line_no_on_page": 1},
            {
                "text": "Consolidated statement of financial position",
                "bbox": [0.0, 10.0, 300.0, 18.0],
                "line_no": 2,
                "line_no_on_page": 2,
            },
            {"text": "Current assets", "bbox": [0.0, 20.0, 200.0, 28.0], "line_no": 3, "line_no_on_page": 3},
            {"text": "372,592", "bbox": [400.0, 30.0, 470.0, 38.0], "line_no": 4, "line_no_on_page": 4},
            {"text": "723,789", "bbox": [400.0, 40.0, 470.0, 48.0], "line_no": 5, "line_no_on_page": 5},
            {"text": "3,674,652", "bbox": [400.0, 50.0, 470.0, 58.0], "line_no": 6, "line_no_on_page": 6},
        ]
        for ln in page_lines:
            ln["numeric_words"] = []

        fake_region = {
            "start_idx": 3,
            "end_idx": 5,
            "bbox": [0.0, 30.0, 470.0, 58.0],
            "columns": [{"x_center": 420.0, "is_variance": False}, {"x_center": 520.0, "is_variance": False}],
            "header_text": "Consolidated statement of financial position",
            "unit_multiplier": 1.0,
            "currency_hint": "$",
            "period_hint": "30 June 2020",
        }
        with mock.patch.object(EXTRACT, "detect_table_regions", return_value=[fake_region]):
            blocks = EXTRACT.segment_statement_blocks(
                Path("dummy.pdf"),
                source_kind="appendix_report",
                prepared_pages={1: page_lines},
            )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].get("statement_scope"), "appendix_statement")
        self.assertEqual(blocks[0].get("title"), "Consolidated statement of financial position")
        self.assertEqual(blocks[0].get("statement_family"), "balance_sheet")

    def test_is_canonical_statement_type_accepts_appendix(self):
        self.assertTrue(EXTRACT.is_canonical_statement_type("appendix_statement"))

    def test_detect_currency_hint_for_cad_header(self):
        self.assertEqual(EXTRACT.detect_currency_hint("All values in $CAD'000"), "C$")

    def test_parent_statement_rows_rejected_in_strict_mode(self):
        line = "Loss after income tax (1,191,647) (5,599,792)"
        rows = EXTRACT.parse_line(
            Path("dummy.pdf"),
            5316,
            line,
            strict_table_only=True,
            active_section="statement of profit or loss",
            statement_type="parent_statement",
            statement_scope_header="Note 29 Parent entity information",
            page_number=92,
            note_number="29",
        )
        self.assertEqual(rows, [])

    def test_consolidated_statement_rows_accepted_in_strict_mode(self):
        line = "Loss after income tax (1,889,766) (5,054,251)"
        rows = EXTRACT.parse_line(
            Path("dummy.pdf"),
            4170,
            line,
            strict_table_only=True,
            active_section="statement of profit or loss",
            statement_type="consolidated_statement",
            statement_scope_header="Consolidated statement of profit or loss",
            page_number=88,
            note_number="",
        )
        ni_rows = [r for r in rows if r["metric"] == "net_income" and r["value_type"] == "amount"]
        self.assertTrue(ni_rows)
        self.assertEqual(ni_rows[0].get("statement_type"), "consolidated_statement")

    def test_same_metric_in_parent_and_consolidated_keeps_consolidated_only(self):
        parent_line = "Loss after income tax (1,191,647) (5,599,792)"
        cons_line = "Loss after income tax (1,889,766) (5,054,251)"
        parent_rows = EXTRACT.parse_line(
            Path("dummy.pdf"),
            5316,
            parent_line,
            strict_table_only=True,
            active_section="statement of profit or loss",
            statement_type="parent_statement",
            statement_scope_header="Note 29 Parent entity information",
            page_number=92,
            note_number="29",
        )
        cons_rows = EXTRACT.parse_line(
            Path("dummy.pdf"),
            4170,
            cons_line,
            strict_table_only=True,
            active_section="statement of profit or loss",
            statement_type="consolidated_statement",
            statement_scope_header="Consolidated statement of profit or loss",
            page_number=88,
            note_number="",
        )
        all_rows = EXTRACT.dedupe(parent_rows + cons_rows)
        self.assertEqual(len(parent_rows), 0)
        self.assertTrue(any(r.get("statement_type") == "consolidated_statement" for r in all_rows))

    def test_classify_statement_context_uses_lookahead_for_parent_scope(self):
        lines = [
            "Statement of profit or loss",
            "Loss after income tax (1,191,647) (5,599,792)",
            "Total comprehensive loss (1,191,647) (5,599,792)",
            "Parent",
            "31 December 2022",
        ]
        ctx = EXTRACT.classify_statement_context(lines, 2, active_section="statement of profit or loss")
        self.assertEqual(ctx.get("statement_type"), "parent_statement")

    def test_split_rows_by_scope_routes_canonical_context_and_rejected(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "revenue",
                "raw_value": "$1m",
                "period": "FY25",
                "statement_period_end": "2025-12-31",
                "line": "Revenue $1m",
                "row_label": "Revenue",
                "table_header_text": "For the year ended 31 December 2025 2024 $'000",
                "statement_title": "Consolidated statement of comprehensive income",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
            },
            {
                "file": "a.pdf",
                "metric": "cash_and_equivalents",
                "raw_value": "$2m",
                "period": "Current quarter - 31 December 2025",
                "statement_period_end": "2025-12-31",
                "line": "Cash $2m",
                "row_label": "Cash and cash equivalents at end of quarter",
                "table_header_text": "Current quarter Previous quarter 31 December 2025 30 September 2025",
                "statement_title": "Consolidated statement of cash flows",
                "inside_table": True,
                "statement_scope": "appendix_statement",
            },
            {
                "file": "a.pdf",
                "metric": "net_income",
                "raw_value": "$3m",
                "period": "FY25",
                "line": "NPAT $3m",
                "inside_table": True,
                "statement_scope": "parent_statement",
            },
            {
                "file": "a.pdf",
                "metric": "ebitda",
                "raw_value": "$4m",
                "period": "FY25",
                "line": "EBITDA $4m",
                "inside_table": False,
                "statement_scope": "consolidated_statement",
            },
            {
                "file": "a.pdf",
                "metric": "cash_and_equivalents_closing",
                "raw_value": "$5m",
                "period": "Current quarter - Previous quarter",
                "statement_period_end": "",
                "line": "Cash and cash equivalents at end of period $5m",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
            },
            {
                "file": "a.pdf",
                "metric": "net_income",
                "raw_value": "$6m",
                "period": "FY25",
                "statement_period_end": "2025-12-31",
                "line": "6",
                "row_label": "Loss after income tax",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
            },
            {
                "file": "a.pdf",
                "metric": "total_assets",
                "raw_value": "$7m",
                "period": "FY25",
                "statement_period_end": "2025-12-31",
                "line": "Total assets 7",
                "row_label": "Total assets",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of profit or loss",
            },
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 2)
        self.assertEqual(len(split["context_rows"]), 4)
        self.assertEqual(len(split["rejected_rows"]), 1)

    def test_split_rows_by_scope_routes_reconciliation_tables_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_equity",
                "raw_value": "42,287,136",
                "value": 42287136.0,
                "period": "30 June 2021",
                "statement_period_end": "2021-06-30",
                "line": "42,287,136",
                "row_label": "Net assets",
                "table_header_text": "Impact on consolidated statement of financial position previously disclosed",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_split_rows_by_scope_routes_parent_entity_context_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_assets",
                "raw_value": "4,737,793",
                "value": 4737793000.0,
                "period": "30 June 2023",
                "statement_period_end": "2023-06-30",
                "line": "4,737,793",
                "row_label": "Total assets",
                "table_header_text": "Balance sheet Assets Current assets Non-current assets Total assets",
                "block_context_text": "31 Parent entity financial information",
                "inside_table": True,
                "statement_scope": "appendix_statement",
                "statement_title": "Consolidated statement of financial position",
                "parent_entity_context": True,
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "parent_entity_context")

    def test_split_rows_by_scope_routes_financial_impacts_title_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "net_income",
                "raw_value": "(914)",
                "value": -914.0,
                "period": "30 June 2025",
                "statement_period_end": "2025-06-30",
                "line": "(914)",
                "row_label": "Loss after taxation",
                "table_header_text": "Income statement",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "The financial impacts of the Samarco dam failure on the Group’s income statement, balance sheet and cash flow statement",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_split_rows_by_scope_recovers_income_family_from_header_hints(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "ebit",
                "raw_value": "48,039",
                "value": 48039000.0,
                "period": "31 December 2021",
                "statement_period_end": "2021-12-31",
                "line": "48,039",
                "row_label": "Operating profit",
                "table_header_text": "Consolidated Income Statement (Financial Statements 1.1)",
                "inside_table": True,
                "statement_scope": "appendix_statement",
                "statement_family": "other",
                "statement_title": "Financial statements section 1.1",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertEqual(split["canonical_rows"][0].get("statement_family"), "income_statement")

    def test_split_rows_by_scope_routes_bulleted_narrative_row_labels_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "revenue",
                "raw_value": "2.6",
                "value": 2.6,
                "period": "31 December 2024",
                "statement_period_end": "2024-12-31",
                "line": "2.6",
                "row_label": "We generated free cash flow of \u2022 Payment of dividends to BHP",
                "table_header_text": "Conservatively geared balance sheet",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated Income Statement",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "narrative_row_label")

    def test_split_rows_by_scope_routes_party_to_deed_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "net_income",
                "raw_value": "11,935",
                "value": 11935000000.0,
                "period": "30 June 2023",
                "statement_period_end": "2023-06-30",
                "line": "11,935",
                "row_label": "Profit after taxation",
                "table_header_text": "wholly owned subsidiaries that are party to the Deed for the years ended 30 June 2023",
                "inside_table": True,
                "statement_scope": "appendix_statement",
                "statement_title": "Consolidated statement of cash flows",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_split_rows_by_scope_routes_net_assets_disposed_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_assets",
                "raw_value": "242",
                "value": 242000000.0,
                "period": "30 June 2022",
                "statement_period_end": "2022-06-30",
                "line": "242",
                "row_label": "Total assets",
                "table_header_text": "2022 US$M Net assets disposed",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_split_rows_by_scope_routes_news_release_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "free_cash_flow",
                "raw_value": "8.5",
                "value": 8.5,
                "period": "31 December 2020",
                "statement_period_end": "2020-12-31",
                "line": "8.5",
                "row_label": "Free cash flow (continuing operations) of",
                "table_header_text": "News release Cash flow and balance sheet",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Our balance sheet remains strong with net debt at US$6.1 billion",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_split_rows_by_scope_routes_ambiguous_multi_metric_row_labels_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_assets",
                "raw_value": "242",
                "value": 242000000.0,
                "period": "30 June 2022",
                "statement_period_end": "2022-06-30",
                "line": "242",
                "row_label": "Total assets Liabilities Trade and other payables",
                "row_label_metric_hit_count": 2,
                "table_header_text": "Consolidated statement of financial position",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "ambiguous_row_label")

    def test_split_rows_by_scope_routes_narrative_prefix_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "net_debt",
                "raw_value": "4.1",
                "value": 4.1,
                "period": "30 June 2020",
                "statement_period_end": "2020-06-30",
                "line": "4.1",
                "row_label": "This resulted in Net debt",
                "table_header_text": "was 6.9 per cent at 30 June 2021, compared",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "A strong balance sheet through the cycle",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "narrative_row_label")

    def test_split_rows_by_scope_routes_component_adjustment_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "net_debt",
                "raw_value": "(1,572)",
                "value": -1572.0,
                "period": "30 June 2021",
                "statement_period_end": "2021-06-30",
                "line": "(1,572)",
                "row_label": "Less: Net debt management related instruments 1",
                "table_header_text": "Consolidated statement of financial position",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_split_rows_by_scope_routes_combined_liabilities_equity_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_liabilities",
                "raw_value": "579,972",
                "value": 579972000.0,
                "period": "31 December 2020",
                "statement_period_end": "2020-12-31",
                "line": "579,972",
                "row_label": "Total liabilities and net assets attributable to partners in Golden Grove, LP",
                "table_header_text": "Consolidated statement of financial position",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "combined_liabilities_equity_row")

    def test_split_rows_by_scope_balance_sheet_identity_guard_demotes_equal_liabilities(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_assets",
                "raw_value": "579,972",
                "value": 579972000.0,
                "period": "31 December 2020",
                "statement_period_end": "2020-12-31",
                "line": "579,972",
                "row_label": "Total assets",
                "table_header_text": "Consolidated statement of financial position",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
                "statement_family": "balance_sheet",
            },
            {
                "file": "a.pdf",
                "metric": "total_liabilities",
                "raw_value": "579,972",
                "value": 579972000.0,
                "period": "31 December 2020",
                "statement_period_end": "2020-12-31",
                "line": "579,972",
                "row_label": "Total liabilities",
                "table_header_text": "Consolidated statement of financial position",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
                "statement_family": "balance_sheet",
            },
            {
                "file": "a.pdf",
                "metric": "total_equity",
                "raw_value": "168,599",
                "value": 168599000.0,
                "period": "31 December 2020",
                "statement_period_end": "2020-12-31",
                "line": "168,599",
                "row_label": "Net assets attributable to partners",
                "table_header_text": "Consolidated statement of financial position",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
                "statement_family": "balance_sheet",
            },
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 2)
        self.assertEqual(
            sorted(r.get("metric", "") for r in split["canonical_rows"]),
            ["total_assets", "total_equity"],
        )
        guarded = [r for r in split["context_rows"] if r.get("context_reason") == "balance_sheet_identity_guard"]
        self.assertEqual(len(guarded), 1)
        self.assertEqual(guarded[0].get("metric"), "total_liabilities")

    def test_split_rows_by_scope_normalizes_income_title_when_family_conflicts(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "net_income",
                "raw_value": "(4,835,687)",
                "value": -4835687.0,
                "period": "year ended 30 June 2021",
                "statement_period_end": "2021-06-30",
                "line": "(4,835,687)",
                "row_label": "Loss after income tax",
                "table_header_text": "2021 AUD$ 2020 AUD$ Loss after income tax Total comprehensive income",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
                "statement_family": "income_statement",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertIn(
            "comprehensive income",
            str(split["canonical_rows"][0].get("statement_title", "")).lower(),
        )

    def test_split_rows_by_scope_normalizes_income_title_from_cashflow_label(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "revenue",
                "raw_value": "600,762",
                "value": 600762000.0,
                "period": "31 December 2021",
                "statement_period_end": "2021-12-31",
                "line": "600,762",
                "row_label": "Revenue",
                "table_header_text": "NPAT TO EBITDA reconciliation Revenue EBITDA NPAT",
                "inside_table": True,
                "statement_scope": "appendix_statement",
                "statement_title": "Consolidated statement of cash flows",
                "statement_family": "income_statement",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertIn(
            "comprehensive income",
            str(split["canonical_rows"][0].get("statement_title", "")).lower(),
        )

    def test_split_rows_by_scope_normalizes_balance_title_from_cashflow_label(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_assets",
                "raw_value": "579,972",
                "value": 579972000.0,
                "period": "31 December 2021",
                "statement_period_end": "2021-12-31",
                "line": "579,972",
                "row_label": "Total assets",
                "table_header_text": "Assets Current assets Total assets Total liabilities Net assets",
                "inside_table": True,
                "statement_scope": "appendix_statement",
                "statement_title": "Consolidated statement of cash flows",
                "statement_family": "balance_sheet",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertIn(
            "financial position",
            str(split["canonical_rows"][0].get("statement_title", "")).lower(),
        )

    def test_split_rows_by_scope_routes_cash_reconciliation_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "cash_and_equivalents",
                "raw_value": "(13,426)",
                "value": -13426000000.0,
                "period": "30 June 2020",
                "statement_period_end": "2020-06-30",
                "line": "(13,426)",
                "row_label": "Cash and cash equivalents",
                "table_header_text": "Alternative Performance Measures continued Net debt waterfall Year ended 30 June",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "The following table reconciles Net operating assets for the Group to Net assets on the Consolidated Balance Sheet",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_split_rows_by_scope_routes_net_cash_movement_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "cash_and_equivalents",
                "raw_value": "(557)",
                "value": -557000000.0,
                "period": "2024",
                "statement_period_end": "2024-12-31",
                "line": "(557)",
                "row_label": "Net decrease in cash and cash equivalents",
                "table_header_text": "Statement of cash flows",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of cash flows",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "cash_non_balance_context")

    def test_split_rows_by_scope_routes_cash_acquired_or_disposed_rows_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "cash_and_equivalents",
                "raw_value": "(399)",
                "value": -399000000.0,
                "period": "30 June 2022",
                "statement_period_end": "2022-06-30",
                "line": "(399)",
                "row_label": "Cash and cash equivalents acquired",
                "table_header_text": "2022 US$M Net assets disposed",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of cash flows",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_split_rows_by_scope_routes_non_current_assets_row_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "current_assets",
                "metric_base": "current_assets",
                "raw_value": "3,833",
                "value": 3833000000.0,
                "period": "2 April 2024",
                "statement_period_end": "2024-04-02",
                "line": "3,833",
                "row_label": "Total impairment of non-current assets",
                "table_header_text": "Consolidated statement of financial position",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "non_current_row_label")

    def test_split_rows_by_scope_routes_cash_award_row_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "cash_and_equivalents",
                "metric_base": "cash_and_equivalents",
                "raw_value": "120",
                "value": 120.0,
                "period": "Previous quarter - 31 March 2024",
                "statement_period_end": "2024-03-31",
                "line": "Consists of fixed remuneration, maximum CDP (a cash award of 120 per cent of base",
                "row_label": "Consists of fixed remuneration, maximum CDP (a cash award of",
                "table_header_text": "Consolidated statement of cash flows",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of cash flows",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "cash_keyword_false_positive")

    def test_split_rows_by_scope_repairs_non_month_end_statement_period_using_header_date(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "cash_and_equivalents",
                "raw_value": "15,246",
                "value": 15246000000.0,
                "period": "2 September 2021",
                "statement_period": "2 September 2021",
                "statement_period_end": "2021-09-02",
                "line": "15,246",
                "row_label": "Cash and cash equivalents",
                "table_header_text": "Consolidated Balance Sheet as at 30 June 2021 Notes",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 1)
        row = split["canonical_rows"][0]
        self.assertEqual(row.get("statement_period_end"), "2021-06-30")
        self.assertEqual(row.get("period"), "30 June 2021")

    def test_split_rows_by_scope_recovers_balance_sheet_total_row_scope_and_period_from_file_hint(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_equity",
                "metric_base": "total_equity",
                "value_type": "amount",
                "raw_value": "52,218",
                "value": 52218000000.0,
                "currency": "US$",
                "period": "30 June 2025",
                "statement_period": "30 June 2025",
                "statement_period_end": "2025-06-30",
                "line": "52,218",
                "row_label": "Total equity",
                "table_header_text": "Consolidated statement of financial position 2025 2024",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
                "statement_family": "balance_sheet",
            },
            {
                "file": "a.pdf",
                "metric": "total_assets",
                "metric_base": "total_assets",
                "value_type": "amount",
                "raw_value": "108,790",
                "value": 108790000000.0,
                "currency": "US$",
                "period": "",
                "statement_period": "",
                "statement_period_end": "",
                "line": "Total assets 108,790 102,362",
                "row_label": "Total assets 108,790 102,362",
                "table_header_text": "Consolidated statement of financial position 2025 2024",
                "inside_table": False,
                "source_mode": "line",
                "statement_scope": "other",
                "statement_title": "Assets Current assets Total assets",
                "statement_family": "other",
            },
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 2)
        recovered = next(r for r in split["canonical_rows"] if r.get("metric") == "total_assets")
        self.assertEqual(recovered.get("statement_scope"), "consolidated_statement")
        self.assertEqual(recovered.get("statement_family"), "balance_sheet")
        self.assertEqual(recovered.get("statement_period_end"), "2025-06-30")
        self.assertEqual(recovered.get("statement_scope_reason"), "balance_sheet_total_row_recovery")

    def test_split_rows_by_scope_does_not_recover_parent_entity_balance_sheet_row(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "total_equity",
                "metric_base": "total_equity",
                "value_type": "amount",
                "raw_value": "52,218",
                "value": 52218000000.0,
                "currency": "US$",
                "period": "30 June 2025",
                "statement_period": "30 June 2025",
                "statement_period_end": "2025-06-30",
                "line": "52,218",
                "row_label": "Total equity",
                "table_header_text": "Consolidated statement of financial position 2025 2024",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of financial position",
                "statement_family": "balance_sheet",
            },
            {
                "file": "a.pdf",
                "metric": "total_assets",
                "metric_base": "total_assets",
                "value_type": "amount",
                "raw_value": "49,677",
                "value": 49677000000.0,
                "currency": "US$",
                "period": "",
                "statement_period": "",
                "statement_period_end": "",
                "line": "49,677",
                "row_label": "Total assets",
                "table_header_text": "Statement of financial position",
                "inside_table": True,
                "statement_scope": "other",
                "statement_scope_header": "Note 29 Parent entity financial information",
                "statement_title": "Statement of financial position",
                "statement_family": "other",
            },
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 1)
        self.assertEqual(split["canonical_rows"][0].get("metric"), "total_equity")
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "parent_entity_context")

    def test_split_rows_by_scope_routes_unresolved_non_month_end_period_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "ebitda",
                "metric_base": "ebitda",
                "value_type": "amount",
                "raw_value": "112",
                "value": 112000000.0,
                "currency": "US$",
                "period": "3 May 2022",
                "statement_period": "3 May 2022",
                "statement_period_end": "2022-05-03",
                "line": "112",
                "row_label": "Underlying EBITDA",
                "table_header_text": "Total Coal",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of comprehensive income",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "non_month_end_period_unresolved")

    def test_split_rows_by_scope_routes_eps_non_month_end_period_to_context(self):
        rows = [
            {
                "file": "a.pdf",
                "metric": "eps",
                "metric_base": "eps",
                "value_type": "amount",
                "raw_value": "1.23",
                "value": 1.23,
                "currency": "US$",
                "period": "2 September 2021",
                "statement_period": "2 September 2021",
                "statement_period_end": "2021-09-02",
                "line": "1.23",
                "row_label": "Earnings per share",
                "table_header_text": "Financial Statements",
                "inside_table": True,
                "statement_scope": "consolidated_statement",
                "statement_title": "Consolidated statement of comprehensive income",
            }
        ]
        split = EXTRACT.split_rows_by_scope(rows)
        self.assertEqual(len(split["canonical_rows"]), 0)
        self.assertEqual(len(split["context_rows"]), 1)
        self.assertEqual(split["context_rows"][0].get("context_reason"), "non_month_end_period_unresolved")


class TestMetricAccuracy(unittest.TestCase):
    """Tests for numeric and scaling accuracy of extracted metrics."""

    def test_detect_unit_multiplier_compact_usd_million_header(self):
        self.assertEqual(EXTRACT.detect_unit_multiplier("Consolidated income statement (US$M)"), 1e6)

    def test_detect_unit_multiplier_compact_aud_billion_header(self):
        self.assertEqual(EXTRACT.detect_unit_multiplier("Statement of financial position A$bn"), 1e9)

    def test_parse_scaled_number_bare_integer(self):
        self.assertEqual(EXTRACT.parse_scaled_number("100", None), 100.0)
        self.assertEqual(EXTRACT.parse_scaled_number("1,234", None), 1234.0)

    def test_parse_scaled_number_thousand_suffix(self):
        self.assertEqual(EXTRACT.parse_scaled_number("50", "k"), 50000.0)
        self.assertEqual(EXTRACT.parse_scaled_number("50", "thousand"), 50000.0)

    def test_parse_scaled_number_million_suffix(self):
        self.assertEqual(EXTRACT.parse_scaled_number("18.2", "m"), 18200000.0)
        self.assertEqual(EXTRACT.parse_scaled_number("73.671", "million"), 73671000.0)
        self.assertEqual(EXTRACT.parse_scaled_number("1", "mn"), 1000000.0)

    def test_parse_scaled_number_billion_suffix(self):
        self.assertEqual(EXTRACT.parse_scaled_number("2.5", "b"), 2500000000.0)
        self.assertEqual(EXTRACT.parse_scaled_number("1", "billion"), 1e9)

    def test_parse_scaled_number_negative_parentheses(self):
        self.assertEqual(EXTRACT.parse_scaled_number("(1,327)", None), -1327.0)
        self.assertEqual(EXTRACT.parse_scaled_number("(914)", None), -914.0)

    def test_parse_accounting_number_variants(self):
        self.assertEqual(EXTRACT.parse_accounting_number("(123)"), -123.0)
        self.assertEqual(EXTRACT.parse_accounting_number("123"), 123.0)
        self.assertEqual(EXTRACT.parse_accounting_number("-123"), -123.0)
        self.assertEqual(EXTRACT.parse_accounting_number("1,234"), 1234.0)
        self.assertEqual(EXTRACT.parse_accounting_number("(1,234)"), -1234.0)

    def test_normalize_metric_value_enforces_negative_expense_sign(self):
        metric = "depreciation_and_amortisation"
        self.assertEqual(EXTRACT.normalize_metric_value(metric, "(123)"), -123.0)
        self.assertEqual(EXTRACT.normalize_metric_value(metric, "123"), -123.0)
        self.assertEqual(EXTRACT.normalize_metric_value(metric, "-123"), -123.0)

    def test_parse_scaled_number_invalid_returns_none(self):
        self.assertIsNone(EXTRACT.parse_scaled_number("n/a", None))
        self.assertIsNone(EXTRACT.parse_scaled_number("", "m"))

    def test_apply_unit_multiplier_scales_money_metric(self):
        row = {
            "metric": "revenue",
            "value_type": "amount",
            "raw_value": "100",
            "value": 100.0,
        }
        out = EXTRACT.apply_unit_multiplier(row, 1e6)
        self.assertEqual(out["value"], 100_000_000.0)

    def test_apply_unit_multiplier_does_not_double_scale_when_raw_has_suffix(self):
        row = {
            "metric": "revenue",
            "value_type": "amount",
            "raw_value": "18.2m",
            "value": 18200000.0,
        }
        out = EXTRACT.apply_unit_multiplier(row, 1e6)
        self.assertEqual(out["value"], 18200000.0)

    def test_apply_unit_multiplier_ignores_percent_row(self):
        row = {"metric": "growth_pct", "value_type": "percent", "value": 12.0}
        out = EXTRACT.apply_unit_multiplier(row, 1e6)
        self.assertEqual(out["value"], 12.0)

    def test_parse_line_amount_value_accuracy_m_suffix(self):
        line = "Cash and equivalents $12m at period end."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        cash = [r for r in rows if r["metric"] == "cash_and_equivalents" and r["value_type"] == "amount"]
        self.assertTrue(cash, "expected cash amount row")
        self.assertEqual(cash[0]["value"], 12000000.0)
        self.assertEqual(cash[0]["raw_value"], "$12m")

    def test_parse_line_percent_value_accuracy(self):
        line = "Revenue YoY 12% in FY25."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        growth = [r for r in rows if r["metric"] == "growth_pct" and r["value_type"] == "percent"]
        self.assertTrue(growth)
        self.assertEqual(growth[0]["value"], 12.0)

    def test_parse_line_million_in_raw_value_scaled(self):
        line = "Revenue for the group was $73.671 million in FY25."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        rev = [r for r in rows if r["metric"] == "revenue" and r["value_type"] == "amount"]
        self.assertTrue(rev)
        self.assertEqual(rev[0]["raw_value"], "$73.671 million")
        self.assertEqual(rev[0]["value"], 73671000.0)

    def test_parse_line_multiple_amounts_same_line(self):
        """Multiple amount metrics on one line: each metric gets the amount that appears after its label."""
        line = "EBITDA $44m, NPAT $18m, free cash flow $9m."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        ebitda = [r for r in rows if r["metric"] == "ebitda" and r["value_type"] == "amount"]
        npat = [r for r in rows if r["metric"] == "npat" and r["value_type"] == "amount"]
        fcf = [r for r in rows if r["metric"] == "free_cash_flow" and r["value_type"] == "amount"]
        self.assertTrue(ebitda, "expected ebitda row")
        self.assertTrue(npat, "expected npat row")
        self.assertTrue(fcf, "expected free_cash_flow row")
        self.assertEqual(ebitda[0]["value"], 44000000.0)
        self.assertEqual(ebitda[0]["raw_value"], "$44m")
        self.assertEqual(npat[0]["value"], 18000000.0)
        self.assertEqual(npat[0]["raw_value"], "$18m")
        self.assertEqual(fcf[0]["value"], 9000000.0)
        self.assertEqual(fcf[0]["raw_value"], "$9m")

    def test_parse_line_single_npat_amount_accuracy(self):
        line = "NPAT reached $18m for the period."
        rows = EXTRACT.parse_line(Path("dummy.pdf"), 1, line, strict_table_only=False)
        npat = [r for r in rows if r["metric"] == "npat" and r["value_type"] == "amount"]
        self.assertTrue(npat)
        self.assertEqual(npat[0]["value"], 18000000.0)
        self.assertEqual(npat[0]["raw_value"], "$18m")


class TestPdfRag(unittest.TestCase):
    def test_build_index_skips_unreadable_pdf(self):
        good = Path("good.pdf")
        bad = Path("bad.pdf")

        def fake_extract(pdf: Path) -> str:
            if pdf == bad:
                raise RuntimeError("pdftotext failed")
            return "Revenue increased and net income rose."

        with mock.patch.object(RAG, "find_pdfs", return_value=[bad, good]), mock.patch.object(
            RAG, "extract_pdf_text", side_effect=fake_extract
        ):
            chunks, idf = RAG.build_index(Path("."))
        self.assertTrue(chunks)
        self.assertTrue(idf)

    def test_validate_canonical_row_valid_passes(self):
        row = {
            "file": "/path/to/a.pdf",
            "metric": "revenue",
            "value_type": "amount",
            "value": 100.0,
            "confidence": 0.85,
        }
        self.assertEqual(EXTRACT.validate_canonical_row(row), [])

    def test_validate_canonical_row_missing_metric_fails(self):
        row = {"file": "/path/to/a.pdf", "metric": "", "value_type": "amount", "value": 1.0}
        errors = EXTRACT.validate_canonical_row(row)
        self.assertIn("missing metric", errors)

    def test_validate_canonical_row_invalid_value_type_fails(self):
        row = {"file": "/path/to/a.pdf", "metric": "revenue", "value_type": "unknown"}
        errors = EXTRACT.validate_canonical_row(row)
        self.assertTrue(any("value_type" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
