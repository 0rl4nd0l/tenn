import importlib
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
GDELT = importlib.import_module("news_pipeline.providers.gdelt")
EODHD = importlib.import_module("news_pipeline.providers.eodhd")
WORLDMONITOR = importlib.import_module("news_pipeline.providers.worldmonitor")
CLI_COMMON = importlib.import_module("news_pipeline.cli_common")


class ProviderTests(unittest.TestCase):
    def test_build_provider_auto_enables_live_when_captures_missing_and_api_key_present(self):
        with tempfile.TemporaryDirectory() as td:
            provider = CLI_COMMON.build_provider(
                provider_name="eodhd",
                eodhd_api_key="demo-key",
                eodhd_capture_dir=Path(td) / "missing_captures",
                allow_missing_eodhd_captures=False,
            )
            self.assertFalse(provider.require_capture_contract)
            self.assertTrue(provider.allow_live_without_captures)
            settings = CLI_COMMON.provider_settings(provider)
            policy = dict(settings.get("capture_policy") or {})
            self.assertEqual(policy.get("mode"), "auto_live_missing_capture")
            self.assertTrue(bool(policy.get("api_key_present")))
            self.assertTrue(bool(policy.get("auto_live_when_capture_missing_effective")))

    def test_build_provider_keeps_strict_contract_without_api_key(self):
        with tempfile.TemporaryDirectory() as td:
            provider = CLI_COMMON.build_provider(
                provider_name="eodhd",
                eodhd_api_key="",
                eodhd_capture_dir=Path(td) / "missing_captures",
                allow_missing_eodhd_captures=False,
            )
            self.assertTrue(provider.require_capture_contract)
            self.assertFalse(provider.allow_live_without_captures)
            settings = CLI_COMMON.provider_settings(provider)
            policy = dict(settings.get("capture_policy") or {})
            self.assertEqual(policy.get("mode"), "capture_contract")

    def test_build_provider_auto_live_flag_still_enables_auto_mode(self):
        with tempfile.TemporaryDirectory() as td:
            provider = CLI_COMMON.build_provider(
                provider_name="eodhd",
                eodhd_api_key="demo-key",
                eodhd_capture_dir=Path(td) / "missing_captures",
                allow_missing_eodhd_captures=False,
                auto_live_when_capture_missing=True,
            )
            self.assertFalse(provider.require_capture_contract)
            self.assertTrue(provider.allow_live_without_captures)
            settings = CLI_COMMON.provider_settings(provider)
            policy = dict(settings.get("capture_policy") or {})
            self.assertEqual(policy.get("mode"), "auto_live_missing_capture")

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

    def test_gdelt_query_length_error_splits_batches_and_recovers(self):
        class FakeProvider(GDELT.GdeltProvider):
            def __init__(self):
                super().__init__(max_records=50, max_ticker_batches=1, ticker_query_batch_size=4)
                self.queries = []

            def _request_json(self, url: str):
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("query", [""])[0]
                self.queries.append(query)
                # Simulate DOC API query-length rejection for wider ticker batches.
                if query.count('"ASX:') >= 2:
                    raise RuntimeError(
                        "GDELT returned non-JSON payload: Expecting value: line 1 column 1 (char 0) "
                        "| preview='Your query was too short or too long.'"
                    )
                if "ASX:BHP" in query:
                    return {"articles": [{"title": "BHP update", "url": "https://example.com/bhp", "seendate": "20260224143000"}]}
                return {"articles": []}

        provider = FakeProvider()
        rows = provider.fetch_window(
            window_start_utc="2026-02-24T00:00:00Z",
            window_end_utc="2026-02-24T23:59:59Z",
            tickers=["BHP", "CSL", "WBC", "NAB"],
        )
        self.assertEqual(len(rows), 1)
        self.assertGreaterEqual(int(provider.last_fetch_diagnostics.get("fallback_splits", 0)), 1)
        self.assertGreaterEqual(int(provider.last_fetch_diagnostics.get("queries_attempted", 0)), 3)

    def test_gdelt_query_length_http_error_splits_batches_and_recovers(self):
        class FakeProvider(GDELT.GdeltProvider):
            def __init__(self):
                super().__init__(max_records=50, max_ticker_batches=1, ticker_query_batch_size=4)
                self.queries = []

            def _request_json(self, url: str):
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("query", [""])[0]
                self.queries.append(query)
                # Simulate provider-side query-length rejection via HTTP status.
                if query.count('"ASX:') >= 2:
                    raise urllib.error.HTTPError(url, 414, "URI Too Long", hdrs=None, fp=None)
                if "ASX:BHP" in query:
                    return {"articles": [{"title": "BHP update", "url": "https://example.com/bhp", "seendate": "20260224143000"}]}
                return {"articles": []}

        provider = FakeProvider()
        rows = provider.fetch_window(
            window_start_utc="2026-02-24T00:00:00Z",
            window_end_utc="2026-02-24T23:59:59Z",
            tickers=["BHP", "CSL", "WBC", "NAB"],
        )
        self.assertEqual(len(rows), 1)
        self.assertGreaterEqual(int(provider.last_fetch_diagnostics.get("fallback_splits", 0)), 1)

    def test_gdelt_raises_when_only_base_query_succeeds_empty_but_ticker_queries_fail(self):
        class FakeProvider(GDELT.GdeltProvider):
            def _request_json(self, url: str):
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("query", [""])[0]
                if query.count('"ASX:') >= 1:
                    raise RuntimeError(
                        "GDELT returned non-JSON payload: Expecting value: line 1 column 1 (char 0) "
                        "| preview='Your query was too short or too long.'"
                    )
                return {"articles": []}

        provider = FakeProvider(max_ticker_batches=1, ticker_query_batch_size=2)
        with self.assertRaises(RuntimeError):
            provider.fetch_window(
                window_start_utc="2026-02-24T00:00:00Z",
                window_end_utc="2026-02-24T23:59:59Z",
                tickers=["BHP", "CSL"],
            )
        self.assertGreaterEqual(int(provider.last_fetch_diagnostics.get("queries_succeeded", 0)), 1)
        self.assertGreaterEqual(int(provider.last_fetch_diagnostics.get("ticker_query_errors", 0)), 1)

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

    def test_eodhd_live_url_uses_au_suffix_and_offset(self):
        provider = EODHD.EodhdProvider(api_key="demo-key", require_capture_contract=False, allow_live_without_captures=True)
        url = provider._build_live_url(
            ticker="BHP",
            window_start_utc="2026-02-24T00:00:00Z",
            window_end_utc="2026-02-24T23:59:59Z",
            limit=5000,
            offset=1000,
        )
        parsed = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertEqual(parsed.get("s"), ["BHP.AU"])
        self.assertEqual(parsed.get("limit"), ["1000"])
        self.assertEqual(parsed.get("offset"), ["1000"])

    def test_eodhd_live_fetch_paginates_until_short_page(self):
        class FakeProvider(EODHD.EodhdProvider):
            def __init__(self):
                super().__init__(api_key="demo-key", require_capture_contract=False, allow_live_without_captures=True, symbol_limit=2)
                self.offsets = []

            def _request_json(self, url: str):
                parsed = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
                offset = int(parsed.get("offset", ["0"])[0])
                self.offsets.append(offset)
                if offset == 0:
                    return [
                        {"id": "1", "title": "BHP item 1", "url": "https://example.com/1", "date": "2026-02-24T09:30:00Z"},
                        {"id": "2", "title": "BHP item 2", "url": "https://example.com/2", "date": "2026-02-24T10:30:00Z"},
                    ]
                if offset == 2:
                    return [{"id": "3", "title": "BHP item 3", "url": "https://example.com/3", "date": "2026-02-24T11:30:00Z"}]
                return []

        provider = FakeProvider()
        rows = provider.fetch_symbol_window(
            ticker="BHP",
            window_start_utc="2026-02-24T00:00:00Z",
            window_end_utc="2026-02-24T23:59:59Z",
        )
        self.assertEqual(provider.offsets, [0, 2])
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.get("_eodhd_ticker") == "BHP" for row in rows))

    def test_worldmonitor_fetch_and_parse_from_capture(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            capture = tmp / "api-cache.json"
            capture.write_text(
                json.dumps(
                    {
                        "theater-posture:v4": {
                            "value": {
                                "timestamp": "2026-02-24T12:00:00Z",
                                "source": "opensky",
                                "totalFlights": 123,
                                "postures": [
                                    {
                                        "theaterId": "iran-theater",
                                        "theaterName": "Iran Theater",
                                        "headline": "Normal activity - Iran Theater",
                                        "summary": "2 other",
                                        "postureLevel": "normal",
                                        "trend": "stable",
                                        "changePercent": 0,
                                        "totalAircraft": 2,
                                        "totalVessels": 0,
                                        "strikeCapable": False,
                                    }
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            provider = WORLDMONITOR.WorldMonitorProvider(capture_path=capture)
            rows = provider.fetch_window(
                window_start_utc="2026-02-24T00:00:00Z",
                window_end_utc="2026-02-24T23:59:59Z",
                tickers=["BHP"],
            )
            self.assertEqual(len(rows), 1)
            parsed = provider.parse_item(rows[0], fetched_at_utc="2026-02-25T00:00:00Z")
            self.assertIsNotNone(parsed.candidate)
            assert parsed.candidate is not None
            self.assertEqual(parsed.candidate.provider, "worldmonitor")
            self.assertEqual(parsed.candidate.source_name, "opensky")
            self.assertEqual(parsed.candidate.published_at_utc, "2026-02-24T12:00:00Z")

    def test_worldmonitor_respects_window_filter(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            capture = tmp / "api-cache.json"
            capture.write_text(
                json.dumps(
                    {
                        "theater-posture:v4": {
                            "value": {
                                "timestamp": "2026-02-20T12:00:00Z",
                                "source": "opensky",
                                "totalFlights": 123,
                                "postures": [{"theaterId": "iran-theater", "theaterName": "Iran Theater"}],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            provider = WORLDMONITOR.WorldMonitorProvider(capture_path=capture)
            rows = provider.fetch_window(
                window_start_utc="2026-02-24T00:00:00Z",
                window_end_utc="2026-02-24T23:59:59Z",
                tickers=[],
            )
            self.assertEqual(rows, [])

    def test_worldmonitor_dedupes_cache_variants_and_prefers_primary(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            capture = tmp / "api-cache.json"
            capture.write_text(
                json.dumps(
                    {
                        "theater-posture:stale:v4": {
                            "value": {
                                "timestamp": "2026-02-24T12:00:00Z",
                                "source": "opensky",
                                "postures": [
                                    {
                                        "theaterId": "iran-theater",
                                        "theaterName": "Iran Theater",
                                        "summary": "stale",
                                    }
                                ],
                            }
                        },
                        "theater-posture:v4": {
                            "value": {
                                "timestamp": "2026-02-24T12:00:00Z",
                                "source": "opensky",
                                "postures": [
                                    {
                                        "theaterId": "iran-theater",
                                        "theaterName": "Iran Theater",
                                        "summary": "primary",
                                    }
                                ],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            provider = WORLDMONITOR.WorldMonitorProvider(capture_path=capture)
            rows = provider.fetch_window(
                window_start_utc="2026-02-24T00:00:00Z",
                window_end_utc="2026-02-24T23:59:59Z",
                tickers=[],
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].get("cache_key"), "theater-posture:v4")
            self.assertEqual(rows[0].get("posture", {}).get("summary"), "primary")

    def test_worldmonitor_applies_theater_ticker_mapping_hints(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            capture = tmp / "api-cache.json"
            mapping = tmp / "worldmonitor_theater_ticker_map.json"
            capture.write_text(
                json.dumps(
                    {
                        "theater-posture:v4": {
                            "value": {
                                "timestamp": "2026-02-24T12:00:00Z",
                                "source": "opensky",
                                "postures": [
                                    {
                                        "theaterId": "iran-theater",
                                        "theaterName": "Iran Theater",
                                        "headline": "Normal activity - Iran Theater",
                                    }
                                ],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            mapping.write_text(
                json.dumps(
                    {
                        "theaters": {
                            "iran-theater": {
                                "tickers": ["WDS", "STO.AX"],
                                "note": "Energy sensitivity",
                                "aliases": ["Iran Theater"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            provider = WORLDMONITOR.WorldMonitorProvider(capture_path=capture, theater_map_path=mapping)
            rows = provider.fetch_window(
                window_start_utc="2026-02-24T00:00:00Z",
                window_end_utc="2026-02-24T23:59:59Z",
                tickers=[],
            )
            self.assertEqual(len(rows), 1)
            parsed = provider.parse_item(rows[0], fetched_at_utc="2026-02-25T00:00:00Z")
            self.assertIsNotNone(parsed.candidate)
            assert parsed.candidate is not None
            self.assertIn("asx_exposure_hint=ASX:STO", parsed.candidate.body)
            self.assertIn("asx_exposure_hint=ASX:WDS", parsed.candidate.body)
            self.assertEqual(parsed.candidate.raw_payload.get("mapped_tickers"), ["STO", "WDS"])


if __name__ == "__main__":
    unittest.main()
