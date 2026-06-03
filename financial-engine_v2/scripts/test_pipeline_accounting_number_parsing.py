import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.pipeline import _coerce_float  # noqa: E402


class AccountingNumberParsingTests(unittest.TestCase):
    def test_common_accounting_formats(self):
        self.assertEqual(_coerce_float("1,234"), 1234.0)
        self.assertEqual(_coerce_float("(123)"), -123.0)
        self.assertEqual(_coerce_float("$1.2m"), 1_200_000.0)
        self.assertEqual(_coerce_float("A$ 2.5 million"), 2_500_000.0)
        self.assertEqual(_coerce_float("3bn"), 3_000_000_000.0)
        self.assertIsNone(_coerce_float("not disclosed"))


if __name__ == "__main__":
    unittest.main()
