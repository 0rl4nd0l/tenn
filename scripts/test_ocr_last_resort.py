import importlib.util
import tempfile
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
MOD = load_module(str(ROOT / "scripts" / "ocr_last_resort.py"), "ocr_last_resort")


class TestOcrLastResort(unittest.TestCase):
    def test_should_trigger_ocr_on_near_empty_text(self):
        trigger, reasons = MOD.should_trigger_ocr("", line_count=2, table_extraction_failed=False)
        self.assertTrue(trigger)
        self.assertIn("near_empty_text", reasons)

    def test_should_trigger_ocr_on_table_failure_with_low_density(self):
        trigger, reasons = MOD.should_trigger_ocr("short text", line_count=10, table_extraction_failed=True)
        self.assertTrue(trigger)
        self.assertIn("table_extraction_failed", reasons)

    def test_collect_ocr_candidates_fail_closed_when_dependency_missing(self):
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "a.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")

            orig_tess = MOD.is_tesseract_available
            orig_ppm = MOD.is_pdftoppm_available
            try:
                MOD.is_tesseract_available = lambda: False
                MOD.is_pdftoppm_available = lambda: False
                rows, stats = MOD.collect_ocr_candidates_for_pdf(
                    pdf,
                    pages=[1],
                    prepared_pages={1: [{"text": ""}]},
                    source_kind="annual_report",
                    table_failed_pages=[1],
                )
            finally:
                MOD.is_tesseract_available = orig_tess
                MOD.is_pdftoppm_available = orig_ppm

        self.assertEqual(rows, [])
        self.assertGreaterEqual(int(stats.get("dependency_missing", 0)), 1)


if __name__ == "__main__":
    unittest.main()
