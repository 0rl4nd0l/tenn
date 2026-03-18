import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class TestWorkerWrapperParity(unittest.TestCase):
    def test_backfill_ticker_delegates_to_pipeline_service(self):
        try:
            import app.worker_tasks as wt
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional dependency missing: {exc}")

        expected = {
            "ticker": "BHP",
            "found": 1,
            "inserted": 1,
            "processed": 0,
            "processed_ok_count": 0,
            "extraction_failed_count": 0,
            "skipped_download": 0,
            "process_documents": False,
            "importance_classification": None,
            "provider_metrics": {},
            "provider_failures_sample": [],
            "errors": [],
            "error_count": 0,
        }

        with mock.patch("app.worker_tasks.run_pipeline_sync", return_value=expected) as patched:
            out = wt.backfill_ticker(ticker="BHP", years=3, process_documents=False)

        self.assertEqual(out, expected)
        patched.assert_called_once()
        spec = patched.call_args.args[0]
        self.assertEqual(spec.ticker, "BHP")
        self.assertEqual(spec.years, 3)
        self.assertFalse(spec.process_documents)
        self.assertEqual(spec.mode, "celery")


if __name__ == "__main__":
    unittest.main()
