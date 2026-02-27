import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.extraction import build_extraction_text


class TestExtractionWindowSampling(unittest.TestCase):
    def test_short_text_passthrough(self):
        text = "hello world"
        self.assertEqual(build_extraction_text(text, max_chars=100), text)

    def test_window_sampling_includes_head_tail_and_keyword(self):
        head = "HEAD SECTION " + ("A" * 500)
        middle = "x" * 8000 + " accounting policies note contains data " + ("y" * 7000)
        tail = "TAIL SECTION " + ("Z" * 700)
        text = head + middle + tail

        out = build_extraction_text(text, max_chars=3000, head_chars=900, tail_chars=900, keyword_window_chars=600)
        self.assertIn("[HEAD]", out)
        self.assertIn("[TAIL]", out)
        self.assertIn("[KEYWORD:accounting policies]", out)
        self.assertIn("HEAD SECTION", out)
        self.assertIn("TAIL SECTION", out)
        self.assertLessEqual(len(out), 3000)


if __name__ == "__main__":
    unittest.main()
