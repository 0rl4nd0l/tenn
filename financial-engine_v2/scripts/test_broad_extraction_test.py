#!/usr/bin/env python3
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "broad_extraction_test.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("broad_extraction_test", str(SCRIPT_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {SCRIPT_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _touch_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n")
    return path


class BroadExtractionDocsRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_explicit_docs_root_is_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = Path(tmp) / "docs"
            pdf = _touch_pdf(
                docs_root
                / "BHP"
                / "financial_performance"
                / "2026-01-01_report_11111111-1111-4111-8111-111111111111.pdf"
            )

            with mock.patch.dict(os.environ, {"DOCS_ROOT": "/does/not/matter"}, clear=True):
                self.assertEqual(self.mod.resolve_docs_root(docs_root), docs_root)
                self.assertEqual(self.mod.discover_pdfs(docs_root), [pdf])

    def test_data_root_is_used_when_it_contains_financial_pdfs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp) / "runtime-data"
            docs_root = data_root / "asx" / "docs"
            pdf = _touch_pdf(
                docs_root
                / "MIN"
                / "financial_performance"
                / "2026-02-20_half-year_22222222-2222-4222-8222-222222222222.pdf"
            )

            with mock.patch.dict(os.environ, {"DATA_ROOT": str(data_root)}, clear=True):
                self.assertEqual(self.mod.resolve_docs_root(), docs_root)
                self.assertEqual(self.mod.discover_pdfs(), [pdf])

    def test_missing_explicit_docs_root_returns_empty_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing"

            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(self.mod.discover_pdfs(missing_root), [])

    def test_external_pdf_record_path_is_stable_logical_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = Path(tmp) / "data" / "asx" / "docs"
            pdf = _touch_pdf(
                docs_root
                / "A2M"
                / "financial_performance"
                / "2026-02-16_appendix-4d_33333333-3333-4333-8333-333333333333.pdf"
            )

            self.assertEqual(
                self.mod._source_path_for_record(pdf, docs_root),
                "data/asx/docs/A2M/financial_performance/"
                "2026-02-16_appendix-4d_33333333-3333-4333-8333-333333333333.pdf",
            )

    def test_empty_summary_has_stable_shape(self) -> None:
        summary = self.mod.compute_summary([])

        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["success_rate"], 0)
        self.assertEqual(
            sorted(summary["metric_coverage"]),
            sorted(self.mod.METRIC_FIELDS),
        )
        self.assertEqual(summary["sanity_checks"]["period_end_valid"]["total"], 0)

    def test_candidate_filter_excludes_meeting_results_and_financial_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = Path(tmp) / "data" / "asx" / "docs"
            agm_pdf = _touch_pdf(
                docs_root
                / "ARL"
                / "financial_performance"
                / "2022-10-28_results-of-meeting_aaaa.pdf"
            )
            agm_notice_pdf = _touch_pdf(
                docs_root
                / "AAM"
                / "financial_performance"
                / "2024-11-05_notice-of-annual-general-meeting-proxy-form_eeee.pdf"
            )
            update_pdf = _touch_pdf(
                docs_root
                / "HNG"
                / "financial_performance"
                / "2021-05-17_financial-update_bbbb.pdf"
            )
            operational_pdf = _touch_pdf(
                docs_root
                / "CCR"
                / "financial_performance"
                / "2021-04-12_ccr-signs-suncorp-as-first-insurance-client-grows-q3-revenue_dddd.pdf"
            )
            purchase_order_pdf = _touch_pdf(
                docs_root
                / "AUK"
                / "financial_performance"
                / "2024-10-02_purchase-order-from-china-southern-air-wine-sale-agreement_pppp.pdf"
            )
            buyback_pdf = _touch_pdf(
                docs_root
                / "NAB"
                / "financial_performance"
                / "2023-08-15_nab-to-buy-back-up-to-1-5-billion-of-ordinary-shares_qqqq.pdf"
            )
            share_purchase_plan_pdf = _touch_pdf(
                docs_root
                / "CQT"
                / "financial_performance"
                / "2022-09-29_results-of-share-purchase-plan_rrrr.pdf"
            )
            unit_purchase_plan_pdf = _touch_pdf(
                docs_root
                / "MXT"
                / "financial_performance"
                / "2024-01-31_unit-purchase-plan-results-of-final-issue_ssss.pdf"
            )
            company_agm_result_pdf = _touch_pdf(
                docs_root
                / "RIO"
                / "financial_performance"
                / "2022-04-11_results-of-rio-tinto-plc-agm_tttt.pdf"
            )
            agm_abbrev_pdf = _touch_pdf(
                docs_root
                / "LSR"
                / "financial_performance"
                / "2022-11-04_results-of-2022-agm_gggg.pdf"
            )
            drilling_pdf = _touch_pdf(
                docs_root
                / "LM8"
                / "financial_performance"
                / "2022-08-29_baker-rc-programme-results-complete_hhhh.pdf"
            )
            base_metals_pdf = _touch_pdf(
                docs_root
                / "CRS"
                / "financial_performance"
                / "2023-05-12_excellent-base-metals-results-extend-lady-sampson_uuuu.pdf"
            )
            monthly_report_pdf = _touch_pdf(
                docs_root
                / "LSF"
                / "financial_performance"
                / "2022-04-08_monthly-report-march-2022_iiii.pdf"
            )
            shareholder_summary_pdf = _touch_pdf(
                docs_root
                / "OLY"
                / "financial_performance"
                / "2024-07-31_annual-asx-shareholder-summary_jjjj.pdf"
            )
            agm_presentation_pdf = _touch_pdf(
                docs_root
                / "CMM"
                / "financial_performance"
                / "2023-11-29_annual-general-meeting-presentation_kkkk.pdf"
            )
            results_briefing_pdf = _touch_pdf(
                docs_root
                / "MFG"
                / "financial_performance"
                / "2023-08-07_full-year-results-briefing-18-august-2023-at-11-30-am_llll.pdf"
            )
            notable_items_pdf = _touch_pdf(
                docs_root
                / "WBC"
                / "financial_performance"
                / "2023-10-26_westpac-s-full-year-2023-notable-items_vvvv.pdf"
            )
            capital_raise_pdf = _touch_pdf(
                docs_root
                / "CMM"
                / "financial_performance"
                / "2024-11-01_capricorn-raises-200m-to-underpin-growth_mmmm.pdf"
            )
            service_launch_pdf = _touch_pdf(
                docs_root
                / "MFD"
                / "financial_performance"
                / "2026-01-29_launch-of-mayfield-360-allied-health-services_nnnn.pdf"
            )
            appendix_pdf = _touch_pdf(
                docs_root
                / "CAF"
                / "financial_performance"
                / "2021-08-25_appendix-4e-fy21_cccc.pdf"
            )
            appendix_4c_pdf = _touch_pdf(
                docs_root
                / "IMR"
                / "financial_performance"
                / "2022-04-28_appendix-4c-quarterly-report-and-business-update_ffff.pdf"
            )
            fy_results_buyback_pdf = _touch_pdf(
                docs_root
                / "AZJ"
                / "financial_performance"
                / "2024-08-12_fy2024-results-and-buyback-announcement_oooo.pdf"
            )

            candidates, excluded = self.mod.filter_candidate_pdfs(
                [
                    agm_pdf,
                    agm_notice_pdf,
                    update_pdf,
                    operational_pdf,
                    purchase_order_pdf,
                    buyback_pdf,
                    share_purchase_plan_pdf,
                    unit_purchase_plan_pdf,
                    company_agm_result_pdf,
                    agm_abbrev_pdf,
                    drilling_pdf,
                    base_metals_pdf,
                    monthly_report_pdf,
                    shareholder_summary_pdf,
                    agm_presentation_pdf,
                    results_briefing_pdf,
                    notable_items_pdf,
                    capital_raise_pdf,
                    service_launch_pdf,
                    appendix_pdf,
                    appendix_4c_pdf,
                    fy_results_buyback_pdf,
                ],
                docs_root,
            )

        self.assertEqual(candidates, [appendix_pdf, appendix_4c_pdf, fy_results_buyback_pdf])
        self.assertEqual(
            [row["exclusion_reason"] for row in excluded],
            [
                "meeting_results_notice",
                "meeting_notice",
                "unaudited_financial_update_without_formal_statements",
                "operational_update_without_formal_statements",
                "operational_update_without_formal_statements",
                "capital_management_update_without_formal_statements",
                "capital_management_update_without_formal_statements",
                "capital_management_update_without_formal_statements",
                "meeting_results_notice",
                "meeting_results_notice",
                "non_financial_update_without_formal_statements",
                "non_financial_update_without_formal_statements",
                "non_financial_update_without_formal_statements",
                "non_financial_update_without_formal_statements",
                "non_financial_update_without_formal_statements",
                "non_financial_update_without_formal_statements",
                "pre_results_update_without_formal_statements",
                "operational_update_without_formal_statements",
                "operational_update_without_formal_statements",
            ],
        )
        self.assertEqual(
            excluded[0]["source_path"],
            "data/asx/docs/ARL/financial_performance/"
            "2022-10-28_results-of-meeting_aaaa.pdf",
        )


if __name__ == "__main__":
    unittest.main()
