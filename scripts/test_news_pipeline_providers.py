import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
GDELT = importlib.import_module("news_pipeline.providers.gdelt")
EODHD = importlib.import_module("news_pipeline.providers.eodhd")


class ProviderTests(unittest.TestCase):
    def test_gdelt_query_includes_asx_variants(self):
        provider = GDELT.GdeltProvider(max_ticker_batches=1, ticker_query_batch_size=3)
        queries = provider._build_query_list(["BHP", "CSL"])
        merged = "\n".join(queries)
        self.assertIn("BHP.AX", merged)
        self.assertIn('"ASX:BHP"', merged)
        self.assertIn("CSL.AX", merged)

    def test_gdelt_parse_legacy_seendate_raw(self):
        provider = GDELT.GdeltProvider()
        row = {
            "title": "BHP guidance update",
            "url": "https://example.com/bhp",
            "extra_fields": {"seendate_raw": "20260224T143000Z"},
        }
        result = provider.parse_item(row, fetched_at_utc="2026-02-25T00:00:00Z")
        self.assertIsNotNone(result.candidate)
        assert result.candidate is not None
        self.assertEqual(result.candidate.published_at_utc, "2026-02-24T14:30:00Z")

    def test_gdelt_parse_missing_timestamp_rejected(self):
        provider = GDELT.GdeltProvider()
        row = {"title": "No timestamp", "url": "https://example.com/no-ts"}
        result = provider.parse_item(row, fetched_at_utc="2026-02-25T00:00:00Z")
        self.assertIsNone(result.candidate)
        self.assertEqual(result.reject_reason, "missing_published_at")

    def test_gdelt_fetch_window_mocked(self):
        class FakeProvider(GDELT.GdeltProvider):
            def _request_json(self, url: str):
                return {
                    "articles": [
                        {"title": "A", "url": "https://example.com/a", "seendate": "20260224143000"},
                        {"title": "A", "url": "https://example.com/a", "seendate": "20260224143000"},
                    ]
                }

        provider = FakeProvider(max_records=50, max_ticker_batches=1, ticker_query_batch_size=2)
        rows = provider.fetch_window(
            window_start_utc="2026-02-24T00:00:00Z",
            window_end_utc="2026-02-24T23:59:59Z",
            tickers=["BHP", "CSL"],
        )
        self.assertEqual(len(rows), 1)

    def test_eodhd_fetch_from_capture_and_parse(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            capture_dir = tmp / "captures"
            capture_dir.mkdir(parents=True, exist_ok=True)
            (capture_dir / "symbol_BHP_sample.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "1",
                            "title": "BHP market update",
                            "link": "https://example.com/bhp",
                            "date": "2026-02-24T09:30:00Z",
                            "source": "Example",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            provider = EODHD.EodhdProvider(capture_dir=capture_dir, require_capture_contract=True)
            rows = provider.fetch_symbol_window(
                ticker="BHP",
                window_start_utc="2026-02-24T00:00:00Z",
                window_end_utc="2026-02-24T23:59:59Z",
            )
            self.assertEqual(len(rows), 1)
            parsed = provider.parse_item(rows[0], fetched_at_utc="2026-02-25T00:00:00Z")
            self.assertIsNotNone(parsed.candidate)
            assert parsed.candidate is not None
            self.assertEqual(parsed.candidate.published_at_utc, "2026-02-24T09:30:00Z")

    def test_eodhd_capture_contract_missing_raises(self):
        with tempfile.TemporaryDirectory() as td:
            provider = EODHD.EodhdProvider(
                capture_dir=Path(td) / "missing",
                require_capture_contract=True,
                allow_live_without_captures=False,
            )
            with self.assertRaises(RuntimeError):
                provider.fetch_window(
                    window_start_utc="2026-02-24T00:00:00Z",
                    window_end_utc="2026-02-24T23:59:59Z",
                    tickers=["BHP"],
                )


if __name__ == "__main__":
    unittest.main()
