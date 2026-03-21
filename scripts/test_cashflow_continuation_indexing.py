import importlib.util
import unittest
from pathlib import Path

import pytest


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPT_DIR = Path(__file__).resolve().parent
MODULE_PATH = SCRIPT_DIR / "section_capture_layer.py"
if not MODULE_PATH.exists():
    pytest.skip(
        "INCOMPLETE MIGRATION — section_capture_layer.py exists on main "
        "(commits 710fe968, af7f8e57) but was not merged into cloud/session-20260319. "
        "Merge main or cherry-pick those commits to restore continuation indexing. "
        "See backend/tests/test_extraction_capability_guards.py for the tracking xfail.",
        allow_module_level=True,
    )
MOD = load_module(str(MODULE_PATH), "section_capture_layer_continuation")


class TestCashflowContinuationIndexing(unittest.TestCase):
    def test_includes_continuation_page_then_stops_on_next_statement_heading(self):
        prepared_pages = {
            1: [
                {"text": "Consolidated Statement of Cash Flows", "numeric_words": []},
                {"text": "Operating activities", "numeric_words": []},
            ],
            2: [
                {"text": "Investing activities", "numeric_words": []},
                {"text": "Net cash used in investing activities", "numeric_words": []},
            ],
            3: [
                {"text": "Consolidated Statement of Financial Position", "numeric_words": []},
                {"text": "Total assets", "numeric_words": []},
            ],
        }

        out = MOD.build_section_index_for_pdf(Path("/tmp/demo.pdf"), prepared_pages)
        self.assertEqual(out["sections"]["cash_flow"]["pages"], [1, 2])
        self.assertEqual(out["debug"]["cashflow_continuation_pages_added"], [2])
        self.assertIn("next_statement_heading", out["debug"]["cashflow_stop_reasons"])

    def test_stops_at_max_continuation_window(self):
        prepared_pages = {
            1: [
                {"text": "Consolidated Statement of Cash Flows", "numeric_words": []},
            ],
            2: [
                {"text": "Operating activities", "numeric_words": []},
                {"text": "Net cash from operating activities", "numeric_words": []},
            ],
            3: [
                {"text": "Investing activities", "numeric_words": []},
                {"text": "Net cash used in investing activities", "numeric_words": []},
            ],
            4: [
                {"text": "Financing activities", "numeric_words": []},
                {"text": "Net cash from financing activities", "numeric_words": []},
            ],
        }

        out = MOD.build_section_index_for_pdf(Path("/tmp/demo.pdf"), prepared_pages)
        # max continuation pages is 2, so only pages 2 and 3 are added after page 1.
        self.assertEqual(out["sections"]["cash_flow"]["pages"], [1, 2, 3])
        self.assertNotIn(4, out["sections"]["cash_flow"]["pages"])
        self.assertIn("max_pages", out["debug"]["cashflow_stop_reasons"])

    def test_excludes_notes_page_from_continuation(self):
        prepared_pages = {
            1: [
                {"text": "Consolidated Statement of Cash Flows", "numeric_words": []},
            ],
            2: [
                {"text": "Operating activities", "numeric_words": []},
                {"text": "Cash generated from operations", "numeric_words": []},
            ],
            3: [
                {"text": "Notes to the financial statements", "numeric_words": []},
                {"text": "Cash and cash equivalents", "numeric_words": []},
            ],
        }

        out = MOD.build_section_index_for_pdf(Path("/tmp/demo.pdf"), prepared_pages)
        self.assertEqual(out["sections"]["cash_flow"]["pages"], [1, 2])
        self.assertNotIn(3, out["sections"]["cash_flow"]["pages"])
        self.assertIn("notes", out["debug"]["cashflow_stop_reasons"])


if __name__ == "__main__":
    unittest.main()
