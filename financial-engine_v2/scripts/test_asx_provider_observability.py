import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.providers.asx_provider import ASXDiscoveryError, ASXProvider


class TestASXProviderObservability(unittest.TestCase):
    def test_marketwide_records_discovery_failures(self):
        p = ASXProvider(timeout=1.0)

        with mock.patch.object(p, "_discover_with_params", side_effect=ASXDiscoveryError("request_fail", "boom")):
            docs = p.discover_marketwide(start=__import__("datetime").datetime(2026, 1, 1), end=__import__("datetime").datetime(2026, 1, 2))

        self.assertEqual(docs, [])
        self.assertGreaterEqual(p.last_discovery_metrics.get("request_ok", 0), 0)
        self.assertTrue(any(item.get("kind") == "request_fail" for item in p.last_discovery_failures))


if __name__ == "__main__":
    unittest.main()
