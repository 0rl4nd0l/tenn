import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
