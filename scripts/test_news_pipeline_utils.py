import importlib.util
import sys
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
UTILS = load_module(ROOT / "scripts" / "news_pipeline" / "utils.py", "news_pipeline_utils")


class NewsPipelineUtilsTests(unittest.TestCase):
    def test_parse_datetime_utc_compact_formats(self):
        self.assertEqual(UTILS.parse_datetime_utc("20260224143000"), "2026-02-24T14:30:00Z")
        self.assertEqual(UTILS.parse_datetime_utc("20260224T143000Z"), "2026-02-24T14:30:00Z")

    def test_parse_datetime_utc_rfc_and_epoch(self):
        self.assertEqual(
            UTILS.parse_datetime_utc("Tue, 24 Feb 2026 14:30:00 GMT"),
            "2026-02-24T14:30:00Z",
        )
        # Epoch milliseconds for 2026-02-24 14:30:00 UTC.
        self.assertEqual(UTILS.parse_datetime_utc("1771943400000"), "2026-02-24T14:30:00Z")

    def test_parse_datetime_utc_invalid(self):
        self.assertIsNone(UTILS.parse_datetime_utc(""))
        self.assertIsNone(UTILS.parse_datetime_utc("not-a-date"))

    def test_canonicalize_url_strips_tracking_and_sorts_query(self):
        url = "HTTPS://WWW.Example.com/path/?utm_source=x&b=2&a=1&fbclid=z#frag"
        self.assertEqual(UTILS.canonicalize_url(url), "https://example.com/path?a=1&b=2")

    def test_hash_stability(self):
        exact_a = UTILS.compute_exact_hash(" BHP beats earnings ", "Revenue up 12% ")
        exact_b = UTILS.compute_exact_hash("bhp beats earnings", "revenue up 12%")
        self.assertEqual(exact_a, exact_b)

        near_a = UTILS.compute_near_hash("BHP beats earnings", "Revenue up 12%", "Cash flow improved.")
        near_b = UTILS.compute_near_hash("BHP beats earnings!", "Revenue up 12%", "Cash flow improved")
        self.assertEqual(near_a, near_b)


if __name__ == "__main__":
    unittest.main()

