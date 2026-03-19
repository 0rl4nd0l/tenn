import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
MOD = load_module(str(ROOT / "scripts" / "run_ticker_expansion_batch.py"), "run_ticker_expansion_batch")


class TestRunTickerExpansionBatch(unittest.TestCase):
    def test_extract_date_key_and_doc_id(self):
        name = "2026-02-17_half-yearly-report_76a78e2a-3a37-49a7-b00a-ae540bf5e678.pdf"
        self.assertEqual(MOD._extract_date_key(name), "2026-02-17")
        self.assertEqual(MOD._doc_id_from_pdf_name(name), "76a78e2a-3a37-49a7-b00a-ae540bf5e678")

    def test_select_latest_pdfs_prefers_date_prefix_desc(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            files = [
                d / "2024-01-01_old_a_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.pdf",
                d / "2026-01-01_new_b_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb.pdf",
                d / "2025-12-31_mid_c_cccccccc-cccc-cccc-cccc-cccccccccccc.pdf",
            ]
            for p in files:
                p.write_bytes(b"%PDF-1.4\n")
            picked = MOD._select_latest_pdfs(files, max_docs=2)
            self.assertEqual([p.name for p in picked], [files[1].name, files[2].name])

    def test_select_latest_pdfs_prefers_financial_relevance_over_agm_noise(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            agm = d / "2026-02-20_annual-general-meeting-voting-results_a.pdf"
            fin = d / "2025-11-07_half-year-financial-report-and-appendix-4d_b.pdf"
            media = d / "2026-02-21_media-release_c.pdf"
            for p in (agm, fin, media):
                p.write_bytes(b"%PDF-1.4\n")

            picked = MOD._select_latest_pdfs([agm, fin, media], max_docs=1)
            self.assertEqual(len(picked), 1)
            self.assertEqual(picked[0].name, fin.name)

    def test_select_latest_pdfs_includes_annual_and_half_when_available(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            files = [
                d / "2026-02-20_fy26-half-year-results-presentation_a.pdf",
                d / "2026-02-19_interim-financial-report-incorporating-appendix-4d_b.pdf",
                d / "2025-08-25_annual-report-incorporating-appendix-4e_c.pdf",
                d / "2026-02-21_media-release_d.pdf",
            ]
            for p in files:
                p.write_bytes(b"%PDF-1.4\n")

            picked = MOD._select_latest_pdfs(files, max_docs=3)
            picked_names = [p.name for p in picked]
            self.assertEqual(len(picked_names), 3)
            self.assertTrue(any("appendix-4e" in n for n in picked_names))
            self.assertTrue(any("appendix-4d" in n or "half-year" in n for n in picked_names))

    def test_ticker_from_file_path(self):
        p = Path("/home/l4nd0/tenn/financial-engine_v2/data/asx/docs/MIN/financial_performance/demo.pdf")
        self.assertEqual(MOD._ticker_from_file_path(p), "MIN")

    def test_select_annual_per_year_prefers_appendix_4e_winner_for_year(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            files = [
                d / "2024-10-17_annual-report-to-shareholders_a.pdf",
                d / "2024-08-14_appendix-4e-and-fy24-financial-report_b.pdf",
                d / "2023-10-18_annual-report-to-shareholders_c.pdf",
                d / "2023-08-17_appendix-4e-and-fy23-financial-report_d.pdf",
            ]
            for p in files:
                p.write_bytes(b"%PDF-1.4\n")

            picked = MOD._select_annual_per_year_pdfs(files, max_docs=2)
            picked_names = [p.name for p in picked]
            self.assertEqual(len(picked_names), 2)
            self.assertTrue(any("2024-08-14_appendix-4e" in n for n in picked_names))
            self.assertTrue(any("2023-08-17_appendix-4e" in n for n in picked_names))

    def test_select_annual_per_year_fills_with_half_when_limit_exceeds_annual_years(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            files = [
                d / "2024-08-14_appendix-4e-and-fy24-financial-report_a.pdf",
                d / "2023-08-17_appendix-4e-and-fy23-financial-report_b.pdf",
                d / "2025-02-12_appendix-4d-and-fy25-half-year-financial-report_c.pdf",
                d / "2024-02-14_appendix-4d-and-fy24-half-year-financial-report_d.pdf",
            ]
            for p in files:
                p.write_bytes(b"%PDF-1.4\n")

            picked = MOD._select_annual_per_year_pdfs(files, max_docs=3)
            picked_names = [p.name for p in picked]
            self.assertEqual(len(picked_names), 3)
            self.assertTrue(any("appendix-4e-and-fy24" in n for n in picked_names))
            self.assertTrue(any("appendix-4e-and-fy23" in n for n in picked_names))
            self.assertTrue(any("appendix-4d-and-fy25" in n for n in picked_names))

    def test_main_defaults_python_bin_from_runtime_resolver(self):
        captured = {}

        def fake_run_batch(cfg, tickers):
            captured["python_bin"] = str(cfg.python_bin)
            return {
                "run_id": "demo",
                "batch_dir": "/tmp/demo",
                "summary_json": "/tmp/demo/summary.json",
                "status_counts": {"ok": 1},
                "aggregate_curated_gold": {},
            }

        stdout = io.StringIO()
        def fake_print_runtime_info():
            print("[runtime] using python interpreter: /tmp/docling-python")
            return "/tmp/docling-python"

        with mock.patch.object(MOD, "print_runtime_info", side_effect=fake_print_runtime_info), mock.patch.object(
            MOD,
            "run_batch",
            side_effect=fake_run_batch,
        ), mock.patch.object(sys, "argv", ["run_ticker_expansion_batch.py", "--tickers", "ASB"]), redirect_stdout(stdout):
            rc = MOD.main()

        self.assertEqual(rc, 0)
        self.assertEqual(captured["python_bin"], "/tmp/docling-python")
        self.assertIn("[runtime] using python interpreter: /tmp/docling-python", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
