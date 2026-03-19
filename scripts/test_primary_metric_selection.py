import importlib.util
import unittest
from pathlib import Path


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
EXTRACT = load_module(str(ROOT / "scripts" / "extract_financial_metrics.py"), "extract_financial_metrics")
QUERY = load_module(str(ROOT / "scripts" / "query_financial_metrics.py"), "query_financial_metrics")


class TestPrimaryMetricSelection(unittest.TestCase):
    def _base_scope_row(self, **overrides):
        row = {
            "file": "/tmp/docs/BHP/financial_performance/a.pdf",
            "line_no": 1,
            "metric": "revenue",
            "metric_alias": "",
            "value_type": "amount",
            "raw_value": "42,931",
            "value": 42_931_000_000.0,
            "currency": "US$",
            "period": "year ended 30 June 2020",
            "statement_period": "year ended 30 June 2020",
            "statement_period_end": "2020-06-30",
            "balance_position": "",
            "balance_date": "",
            "confidence": 0.9,
            "line": "42,931",
            "row_label": "Revenue",
            "row_label_metric_hit_count": 1,
            "source_mode": "table_bbox",
            "table_id": "t1",
            "table_header_text": "Consolidated Income Statement for the year ended 30 June 2020 2020 2019 US$M",
            "statement_type": "consolidated_statement",
            "statement_scope_header": "Consolidated Income Statement",
            "statement_scope": "consolidated_statement",
            "statement_title": "Consolidated Income Statement",
            "statement_family": "income_statement",
            "statement_scope_reason": "consolidated_layout",
            "block_id": "b1",
            "block_context_text": "",
            "parent_entity_context": False,
            "inside_table": True,
            "page_number": 1,
            "note_number": "",
            "pro_forma_context": False,
        }
        row.update(overrides)
        return row

    def test_mark_primary_prefers_blank_variant_over_underlying(self):
        rows = [
            {
                "file": "/tmp/docs/BHP/financial_performance/a.pdf",
                "metric": "ebit",
                "metric_variant": "",
                "statement_period_end": "2021-06-30",
                "value_type": "amount",
                "balance_position": "",
                "value": 25_906_000_000.0,
                "row_label": "Profit from operations",
                "canonical_confidence_score": 4,
                "source_mode": "table_bbox",
                "line_no": 100,
            },
            {
                "file": "/tmp/docs/BHP/financial_performance/a.pdf",
                "metric": "ebit",
                "metric_variant": "underlying",
                "statement_period_end": "2021-06-30",
                "value_type": "amount",
                "balance_position": "",
                "value": 30_291_000_000.0,
                "row_label": "Underlying EBIT",
                "canonical_confidence_score": 4,
                "source_mode": "table_bbox",
                "line_no": 110,
            },
        ]

        EXTRACT.mark_primary_metric_rows(rows)
        primary_rows = [r for r in rows if bool(r.get("primary_metric_value"))]

        self.assertEqual(len(primary_rows), 1)
        self.assertEqual(primary_rows[0]["metric_variant"], "")
        non_primary = [r for r in rows if not bool(r.get("primary_metric_value"))]
        self.assertEqual(non_primary[0]["primary_conflict_winner_line_no"], 100)

    def test_query_dedupe_prefers_primary_row(self):
        rows = [
            {
                "metric": "net_income",
                "metric_variant": "",
                "statement_period_end": "2020-12-31",
                "value_type": "amount",
                "value": 5_020_000_000.0,
                "primary_metric_value": True,
                "canonical_confidence_score": 3,
                "source_mode": "table_bbox",
                "line_no": 200,
            },
            {
                "metric": "net_income",
                "metric_variant": "underlying",
                "statement_period_end": "2020-12-31",
                "value_type": "amount",
                "value": 3_876_000_000.0,
                "primary_metric_value": False,
                "canonical_confidence_score": 4,
                "source_mode": "table_bbox",
                "line_no": 210,
            },
        ]

        selected, dropped = QUERY._dedupe_metric_period(rows, include_variants=False)
        self.assertEqual(len(selected), 1)
        self.assertEqual(len(dropped), 1)
        self.assertEqual(float(selected[0]["value"]), 5_020_000_000.0)
        self.assertTrue(bool(selected[0].get("primary_metric_value")))

    def test_opening_net_debt_row_is_demoted(self):
        row = self._base_scope_row(
            metric="net_debt",
            row_label="Net debt at the beginning of the period",
            statement_title="Consolidated Balance Sheet",
            statement_scope_header="Consolidated Balance Sheet",
            statement_family="balance_sheet",
            table_header_text="Consolidated Balance Sheet as at 30 June 2023 US$M",
            statement_period_end="2023-06-30",
            value=333_000_000.0,
        )
        scoped = EXTRACT.split_rows_by_scope([row])
        self.assertEqual(len(scoped["canonical_rows"]), 0)
        self.assertEqual(len(scoped["context_rows"]), 1)
        self.assertEqual(scoped["context_rows"][0].get("context_reason"), "opening_balance_context")

    def test_narrative_contaminated_row_label_is_demoted(self):
        row = self._base_scope_row(
            metric="free_cash_flow",
            row_label="Free cash flow and BHP's business is stronger now than",
            statement_title="Consolidated Cash Flow Statement",
            statement_scope_header="Consolidated Cash Flow Statement",
            statement_family="cash_flow",
            table_header_text="Consolidated Cash Flow Statement year ended 30 June 2024 US$M",
            statement_period_end="2024-12-31",
            value=2_600_000_000.0,
        )
        scoped = EXTRACT.split_rows_by_scope([row])
        self.assertEqual(len(scoped["canonical_rows"]), 0)
        self.assertEqual(len(scoped["context_rows"]), 1)
        self.assertEqual(scoped["context_rows"][0].get("context_reason"), "narrative_row_label")

    def test_eps_cents_currency_is_normalized(self):
        row = self._base_scope_row(
            metric="eps",
            row_label="Underlying basic earnings per share (US cents)",
            line="337.7",
            raw_value="337.7",
            value=337.7,
            currency="US$",
            statement_title="Consolidated Income Statement",
            statement_scope_header="Consolidated Income Statement",
            statement_family="income_statement",
            table_header_text="Underlying basic earnings per share (US cents) 2021 2020",
            statement_period_end="2021-06-30",
        )
        scoped = EXTRACT.split_rows_by_scope([row])
        self.assertEqual(len(scoped["canonical_rows"]), 1)
        self.assertEqual(scoped["canonical_rows"][0].get("currency"), "USc")

    def test_period_metadata_annual_flow(self):
        row = self._base_scope_row(
            metric="revenue",
            statement_family="income_statement",
            statement_period="Year ended 30 June 2021",
            period="Year ended 30 June 2021",
        )
        meta = EXTRACT.infer_period_metadata(row)
        self.assertEqual(meta.get("period_type"), "annual")
        self.assertEqual(meta.get("period_scope"), "flow")
        self.assertEqual(meta.get("period_length_months"), 12)
        self.assertEqual(meta.get("reporting_cadence"), "annual")
        self.assertEqual(meta.get("reporting_period_months"), 12)

    def test_period_metadata_quarterly_flow(self):
        row = self._base_scope_row(
            metric="revenue",
            statement_family="income_statement",
            statement_period="Quarter ended 31 December 2024",
            period="Quarter ended 31 December 2024",
        )
        meta = EXTRACT.infer_period_metadata(row)
        self.assertEqual(meta.get("period_type"), "quarterly")
        self.assertEqual(meta.get("period_scope"), "flow")
        self.assertEqual(meta.get("period_length_months"), 3)
        self.assertEqual(meta.get("reporting_cadence"), "quarterly")
        self.assertEqual(meta.get("reporting_period_months"), 3)

    def test_period_metadata_half_yearly_flow(self):
        row = self._base_scope_row(
            metric="revenue",
            statement_family="income_statement",
            statement_period="Half year ended 31 Dec 2024",
            period="Half year ended 31 Dec 2024",
        )
        meta = EXTRACT.infer_period_metadata(row)
        self.assertEqual(meta.get("period_type"), "half_yearly")
        self.assertEqual(meta.get("period_scope"), "flow")
        self.assertEqual(meta.get("period_length_months"), 6)
        self.assertEqual(meta.get("reporting_cadence"), "half_yearly")
        self.assertEqual(meta.get("reporting_period_months"), 6)

    def test_period_metadata_point_in_time_stock(self):
        row = self._base_scope_row(
            metric="total_assets",
            statement_family="balance_sheet",
            statement_period="as at 30 June 2021",
            period="as at 30 June 2021",
            table_header_text="Consolidated Balance Sheet as at 30 June 2021",
            statement_scope_header="Consolidated Balance Sheet",
            statement_title="Consolidated Balance Sheet",
        )
        meta = EXTRACT.infer_period_metadata(row)
        self.assertEqual(meta.get("period_type"), "point_in_time")
        self.assertEqual(meta.get("period_scope"), "stock")
        self.assertEqual(meta.get("period_length_months"), 0)
        self.assertEqual(meta.get("period_inference_source"), "statement_family_stock")
        self.assertEqual(meta.get("reporting_cadence"), "unknown")
        self.assertEqual(meta.get("reporting_period_months"), 0)

    def test_period_metadata_stock_keeps_point_in_time_with_cadence(self):
        row = self._base_scope_row(
            metric="current_liabilities",
            statement_family="balance_sheet",
            statement_period="Half year ended 31 Dec 2024",
            period="Half year ended 31 Dec 2024",
            statement_period_end="2024-12-31",
        )
        meta = EXTRACT.infer_period_metadata(row)
        self.assertEqual(meta.get("period_type"), "point_in_time")
        self.assertEqual(meta.get("period_scope"), "stock")
        self.assertEqual(meta.get("period_length_months"), 0)
        self.assertEqual(meta.get("period_inference_source"), "statement_family_stock")
        self.assertEqual(meta.get("reporting_cadence"), "half_yearly")
        self.assertEqual(meta.get("reporting_period_months"), 6)
        self.assertEqual(meta.get("reporting_cadence_inference_source"), "statement_period_label")

    def test_period_metadata_half_year_hint_from_slug_filename(self):
        row = self._base_scope_row(
            file="/tmp/docs/BHP/financial_performance/2025-02-18_half-year-2025-report-and-accounts_x.pdf",
            metric="net_debt",
            statement_family="balance_sheet",
            statement_period="31 Dec 2024",
            period="31 Dec 2024",
            statement_period_end="2024-12-31",
            table_header_text="Net debt and gearing ratio 31 Dec 2024",
            statement_scope_header="Non-IFRS financial information derived from Consolidated Balance Sheet",
            statement_title="Non-IFRS financial information derived from Consolidated Balance Sheet",
        )
        meta = EXTRACT.infer_period_metadata(row)
        self.assertEqual(meta.get("period_type"), "point_in_time")
        self.assertEqual(meta.get("period_scope"), "stock")
        self.assertEqual(meta.get("reporting_cadence"), "half_yearly")
        self.assertEqual(meta.get("reporting_period_months"), 6)
        self.assertEqual(meta.get("reporting_cadence_inference_source"), "document_name_hint")

    def test_period_metadata_prefers_document_hint_when_context_unresolved(self):
        row = self._base_scope_row(
            file="/tmp/docs/BHP/financial_performance/2025-02-18_half-year-2025-report-and-accounts_x.pdf",
            metric="total_debt",
            statement_family="balance_sheet",
            statement_period="31 Dec 2024",
            period="31 Dec 2024",
            statement_period_end="2024-12-31",
            table_header_text="Net debt and gearing ratio 31 Dec 2024 31 Dec 2023",
            statement_scope_header="Non-IFRS financial information",
            statement_title="Net debt and gearing ratio",
        )
        meta = EXTRACT.infer_period_metadata(row)
        self.assertEqual(meta.get("period_type"), "point_in_time")
        self.assertEqual(meta.get("period_scope"), "stock")
        self.assertEqual(meta.get("reporting_cadence"), "half_yearly")
        self.assertEqual(meta.get("reporting_period_months"), 6)
        self.assertEqual(meta.get("reporting_cadence_inference_source"), "document_name_hint")

    def test_period_metadata_prefers_explicit_context_over_annual_file_hint(self):
        row = self._base_scope_row(
            file="/tmp/docs/BHP/financial_performance/2025-09-14_annual-report-to-shareholders_x.pdf",
            metric="revenue",
            statement_family="income_statement",
            statement_period="",
            period="",
            statement_period_end="2024-12-31",
            table_header_text="Consolidated Income Statement for the six months ended 31 December 2024",
            statement_scope_header="Consolidated Income Statement",
            statement_title="Consolidated Income Statement",
        )
        meta = EXTRACT.infer_period_metadata(row)
        self.assertEqual(meta.get("period_type"), "half_yearly")
        self.assertEqual(meta.get("period_scope"), "flow")
        self.assertEqual(meta.get("reporting_cadence"), "half_yearly")
        self.assertEqual(meta.get("reporting_period_months"), 6)
        self.assertEqual(meta.get("reporting_cadence_inference_source"), "context_period_phrase")

    def test_mark_primary_metric_rows_separates_flow_by_duration(self):
        rows = [
            {
                "file": "/tmp/docs/BHP/financial_performance/a.pdf",
                "metric": "net_income",
                "metric_variant": "",
                "statement_period_end": "2022-12-31",
                "value_type": "amount",
                "balance_position": "",
                "value": 7_126_000_000.0,
                "row_label": "Profit after taxation",
                "canonical_confidence_score": 4,
                "source_mode": "table_bbox",
                "line_no": 100,
                "period_scope": "flow",
                "period_type": "half_yearly",
                "reporting_cadence": "half_yearly",
                "reporting_period_months": 6,
            },
            {
                "file": "/tmp/docs/BHP/financial_performance/b.pdf",
                "metric": "net_income",
                "metric_variant": "",
                "statement_period_end": "2022-12-31",
                "value_type": "amount",
                "balance_position": "",
                "value": 6_457_000_000.0,
                "row_label": "Underlying net income",
                "canonical_confidence_score": 4,
                "source_mode": "table_bbox",
                "line_no": 110,
                "period_scope": "flow",
                "period_type": "annual",
                "reporting_cadence": "annual",
                "reporting_period_months": 12,
            },
        ]
        EXTRACT.mark_primary_metric_rows(rows)
        self.assertEqual(sum(1 for r in rows if bool(r.get("primary_metric_value"))), 2)

    def test_query_dedupe_keeps_flow_rows_with_different_duration(self):
        rows = [
            {
                "metric": "net_income",
                "metric_variant": "",
                "statement_period_end": "2022-12-31",
                "value_type": "amount",
                "value": 7_126_000_000.0,
                "primary_metric_value": True,
                "canonical_confidence_score": 4,
                "source_mode": "table_bbox",
                "line_no": 100,
                "period_scope": "flow",
                "period_type": "half_yearly",
                "reporting_cadence": "half_yearly",
                "reporting_period_months": 6,
            },
            {
                "metric": "net_income",
                "metric_variant": "",
                "statement_period_end": "2022-12-31",
                "value_type": "amount",
                "value": 6_457_000_000.0,
                "primary_metric_value": True,
                "canonical_confidence_score": 4,
                "source_mode": "table_bbox",
                "line_no": 110,
                "period_scope": "flow",
                "period_type": "annual",
                "reporting_cadence": "annual",
                "reporting_period_months": 12,
            },
        ]
        selected, dropped = QUERY._dedupe_metric_period(rows, include_variants=False)
        self.assertEqual(len(selected), 2)
        self.assertEqual(len(dropped), 0)

    def test_resolve_canonical_conflicts_keeps_flow_rows_with_different_duration(self):
        rows = [
            self._base_scope_row(
                file="/tmp/docs/BHP/financial_performance/a.pdf",
                metric="net_income",
                value=7_126_000_000.0,
                raw_value="7,126",
                row_label="Profit after taxation",
                statement_period_end="2022-12-31",
                period_scope="flow",
                reporting_cadence="half_yearly",
                reporting_period_months=6,
                canonical_confidence_score=4,
                metric_variant="",
            ),
            self._base_scope_row(
                file="/tmp/docs/BHP/financial_performance/b.pdf",
                metric="net_income",
                value=6_457_000_000.0,
                raw_value="6,457",
                row_label="Profit after taxation",
                statement_period_end="2022-12-31",
                period_scope="flow",
                reporting_cadence="annual",
                reporting_period_months=12,
                canonical_confidence_score=4,
                metric_variant="",
            ),
        ]
        kept, demoted = EXTRACT.resolve_canonical_conflicts(rows)
        self.assertEqual(len(kept), 2)
        self.assertEqual(len(demoted), 0)

    def test_promote_table_context_rows_allows_different_duration_from_strict(self):
        canonical_rows = [
            self._base_scope_row(
                file="/tmp/docs/BHP/financial_performance/a.pdf",
                metric="free_cash_flow",
                value=3_800_000_000.0,
                raw_value="3,800",
                row_label="Free cash flow",
                statement_period_end="2024-12-31",
                period_scope="flow",
                reporting_cadence="annual",
                reporting_period_months=12,
                canonical_tier="strict",
                metric_variant="",
            )
        ]
        context_rows = [
            self._base_scope_row(
                file="/tmp/docs/BHP/financial_performance/b.pdf",
                metric="free_cash_flow",
                value=2_600_000_000.0,
                raw_value="2,600",
                row_label="Free cash flow",
                statement_period_end="2024-12-31",
                period_scope="flow",
                reporting_cadence="half_yearly",
                reporting_period_months=6,
                metric_variant="",
                context_reason="reconciliation_context",
                source_mode="table_bbox",
                inside_table=True,
                value_type="amount",
            )
        ]
        promoted_canon, promoted_context, promoted_count = EXTRACT.promote_table_context_rows(canonical_rows, context_rows)
        self.assertEqual(promoted_count, 1)
        self.assertEqual(len(promoted_canon), 2)
        self.assertEqual(sum(1 for r in promoted_canon if r.get("canonical_tier") == "table_promoted"), 1)
        self.assertTrue(bool(promoted_context[0].get("promoted_to_canonical_tier")))

    def test_non_canonical_scope_row_promotes_only_with_expanded_metric_scope(self):
        row = self._base_scope_row(
            metric="roic_pct",
            value_type="percent",
            raw_value="14%",
            value=14.0,
            currency="",
            row_label="ROIC",
            line="ROIC 14%",
            period="30 June 2025",
            statement_period="30 June 2025",
            statement_period_end="2025-06-30",
            statement_scope="other",
            statement_type="other",
            statement_title="Financial performance",
            statement_scope_header="Financial performance",
            table_header_text="Financial performance for the year ended 30 June 2025",
        )

        scoped_default = EXTRACT.split_rows_by_scope([row])
        self.assertEqual(len(scoped_default["canonical_rows"]), 0)
        self.assertEqual(len(scoped_default["context_rows"]), 1)
        self.assertEqual(scoped_default["context_rows"][0].get("context_reason"), "non_canonical_scope")
        self.assertFalse(bool(scoped_default["context_rows"][0].get("promoted_to_canonical_tier")))

        scoped_expanded = EXTRACT.split_rows_by_scope([row], expanded_metric_scope=True)
        self.assertEqual(len(scoped_expanded["canonical_rows"]), 1)
        canon = scoped_expanded["canonical_rows"][0]
        self.assertEqual(canon.get("metric"), "roic_pct")
        self.assertEqual(canon.get("canonical_tier"), "table_promoted")
        self.assertEqual(canon.get("canonical_promotion_reason"), "non_canonical_scope")
        self.assertEqual(len(scoped_expanded["context_rows"]), 1)
        self.assertTrue(bool(scoped_expanded["context_rows"][0].get("promoted_to_canonical_tier")))

    def test_reconciliation_table_row_is_promoted_with_table_tier(self):
        row = self._base_scope_row(
            metric="total_debt",
            row_label="Total interest bearing liabilities",
            line="20,983",
            raw_value="20,983",
            value=20_983_000_000.0,
            currency="US$",
            statement_period="30 June 2021",
            period="30 June 2021",
            statement_period_end="2021-06-30",
            statement_title="APMs derived from Consolidated Balance Sheet",
            statement_scope_header="APMs derived from Consolidated Balance Sheet",
            statement_family="balance_sheet",
            table_header_text="APMs derived from Consolidated Balance Sheet Net debt and gearing ratio 2021 2020 US$M",
        )
        scoped = EXTRACT.split_rows_by_scope([row])
        self.assertEqual(len(scoped["canonical_rows"]), 1)
        canon = scoped["canonical_rows"][0]
        self.assertEqual(canon.get("metric"), "total_debt")
        self.assertEqual(canon.get("canonical_tier"), "table_promoted")
        self.assertEqual(canon.get("canonical_promotion_reason"), "reconciliation_context")
        self.assertGreaterEqual(int(canon.get("canonical_confidence_score", 0) or 0), 1)
        self.assertEqual(len(scoped["context_rows"]), 1)
        self.assertTrue(bool(scoped["context_rows"][0].get("promoted_to_canonical_tier")))

    def test_reconciliation_component_row_is_not_promoted(self):
        row = self._base_scope_row(
            metric="net_debt",
            row_label="Less: Net debt management related instruments (1)",
            line="(557)",
            raw_value="(557)",
            value=-557_000_000.0,
            currency="US$",
            statement_period="30 June 2021",
            period="30 June 2021",
            statement_period_end="2021-06-30",
            statement_title="APMs derived from Consolidated Balance Sheet",
            statement_scope_header="APMs derived from Consolidated Balance Sheet",
            statement_family="balance_sheet",
            table_header_text="APMs derived from Consolidated Balance Sheet Net debt and gearing ratio 2021 2020 US$M",
        )
        scoped = EXTRACT.split_rows_by_scope([row])
        self.assertEqual(len(scoped["canonical_rows"]), 0)
        self.assertEqual(len(scoped["context_rows"]), 1)
        self.assertEqual(scoped["context_rows"][0].get("context_reason"), "reconciliation_context")

    def test_mark_primary_metric_rows_keeps_underlying_and_reported_scopes(self):
        rows = [
            self._base_scope_row(
                metric="ebit",
                metric_base="ebit",
                metric_variant="reported",
                definition_scope="reported",
                row_label="Reported EBIT",
                value=18_200_000_000.0,
                statement_period_end="2025-06-30",
                canonical_confidence_score=4,
                line_no=100,
            ),
            self._base_scope_row(
                metric="ebit",
                metric_base="ebit",
                metric_variant="underlying",
                definition_scope="underlying",
                row_label="Underlying EBIT",
                value=20_100_000_000.0,
                statement_period_end="2025-06-30",
                canonical_confidence_score=4,
                line_no=120,
            ),
        ]
        EXTRACT.mark_primary_metric_rows(rows)
        primary_rows = [r for r in rows if bool(r.get("primary_metric_value"))]
        self.assertEqual(len(primary_rows), 2)
        self.assertEqual({str(r.get("definition_scope", "")).lower() for r in primary_rows}, {"reported", "underlying"})

    def test_coverage_backfill_is_deterministic_and_sets_provenance(self):
        primary_rows = [
            self._base_scope_row(
                metric="net_income",
                metric_base="net_income",
                definition_scope="reported",
                statement_period_end="2025-12-31",
                value=9_100_000_000.0,
                confidence=0.98,
                source_mode="table_bbox",
            )
        ]
        non_primary_candidates = [
            self._base_scope_row(
                file="/tmp/docs/CBA/financial_performance/2026-02-03_half-year-results.pdf",
                metric="total_assets",
                metric_base="total_assets",
                definition_scope="reported",
                statement_family="balance_sheet",
                statement_period_end="2025-12-31",
                value=1_350_000_000_000.0,
                confidence=0.92,
                canonical_confidence_score=4,
                source_mode="table_bbox",
                primary_metric_value=False,
                line_no=40,
            ),
            self._base_scope_row(
                file="/tmp/docs/CBA/financial_performance/2026-02-03_investor-presentation.pdf",
                metric="total_assets",
                metric_base="total_assets",
                definition_scope="reported",
                statement_family="balance_sheet",
                statement_period_end="2025-12-31",
                value=1_350_000_000_000.0,
                confidence=0.91,
                canonical_confidence_score=3,
                source_mode="docling_table",
                primary_metric_value=False,
                line_no=60,
            ),
        ]
        enhanced_rows, audit_rows = EXTRACT.build_coverage_enhanced_rows(primary_rows, non_primary_candidates, [])
        backfilled = [
            r
            for r in enhanced_rows
            if str(r.get("metric_base", "")).lower() == "total_assets" and bool(r.get("is_backfilled"))
        ]
        self.assertEqual(len(backfilled), 1)
        self.assertEqual(backfilled[0].get("backfill_rule"), "deterministic_missing_primary_backfill")
        self.assertEqual(backfilled[0].get("file"), "/tmp/docs/CBA/financial_performance/2026-02-03_half-year-results.pdf")
        self.assertGreaterEqual(float(backfilled[0].get("source_confidence", 0.0)), 0.92)
        self.assertTrue(audit_rows)


if __name__ == "__main__":
    unittest.main()
