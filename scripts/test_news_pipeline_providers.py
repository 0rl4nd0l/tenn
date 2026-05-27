import importlib
import datetime as dt
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
GDELT = importlib.import_module("news_pipeline.providers.gdelt")
EODHD = importlib.import_module("news_pipeline.providers.eodhd")
WORLDMONITOR = importlib.import_module("news_pipeline.providers.worldmonitor")
NEWSPAPER4K = importlib.import_module("news_pipeline.providers.newspaper4k")
CLI_COMMON = importlib.import_module("news_pipeline.cli_common")


class ProviderTests(unittest.TestCase):
    def test_newspaper4k_defaults_to_bounded_daily_profile(self):
        provider = NEWSPAPER4K.Newspaper4kProvider()
        self.assertEqual(provider.source_profile, "daily")
        self.assertEqual(
            provider.sources_file.name, "sources_au_finance_rss_only.txt"
        )
        self.assertEqual(provider.max_articles_per_source, 15)
        self.assertEqual(provider.max_total_articles, 60)
        self.assertEqual(provider.request_timeout_seconds, 10)
        self.assertTrue(provider.no_playwright)
        settings = CLI_COMMON.provider_settings(provider)
        self.assertEqual(settings["source_profile"], "daily")
        self.assertEqual(settings["sources_file"], str(provider.sources_file))

    def test_build_provider_can_select_broad_newspaper4k_profile(self):
        with tempfile.TemporaryDirectory() as td:
            provider = CLI_COMMON.build_provider(
                provider_name="newspaper4k",
                eodhd_api_key="",
                eodhd_capture_dir=Path(td),
                allow_missing_eodhd_captures=False,
                newspaper4k_kwargs={
                    "source_profile": "broad",
                    "max_total_articles": 12,
                    "request_timeout_seconds": 7,
                },
            )
        self.assertEqual(provider.source_profile, "broad")
        self.assertEqual(provider.sources_file.name, "sources_all_au_finance.txt")
        self.assertEqual(provider.max_total_articles, 12)
        self.assertEqual(provider.request_timeout_seconds, 7)
        self.assertFalse(provider.no_playwright)

    def test_newspaper4k_cli_kwargs_default_daily_disables_playwright(self):
        kwargs = CLI_COMMON.newspaper4k_kwargs_from_args(SimpleNamespace())
        self.assertEqual(kwargs["source_profile"], "daily")
        self.assertTrue(kwargs["no_playwright"])

    def test_newspaper4k_cli_kwargs_broad_keeps_playwright_available(self):
        kwargs = CLI_COMMON.newspaper4k_kwargs_from_args(
            SimpleNamespace(newspaper4k_source_profile="broad")
        )
        self.assertEqual(kwargs["source_profile"], "broad")
        self.assertFalse(kwargs["no_playwright"])

    def test_newspaper4k_batches_source_rows_while_preserving_fetch_window_list(self):
        class Source:
            def __init__(self, url: str) -> None:
                self.url = url

        class Article:
            def __init__(self, suffix: str) -> None:
                self.article_url = f"https://example.com/{suffix}"
                self.title = f"BHP update {suffix}"
                self.body = f"ASX:BHP update body {suffix}"
                self.source_name = "Example Finance"
                self.language = "en"
                self.published_at = dt.datetime(2026, 5, 7, 1, 0, tzinfo=dt.timezone.utc)
                self.authors = []
                self.keyword_hits = []
                self.body_source = "mock"
                self.body_lengths = {"body": len(self.body)}
                self.source_url = "https://example.com/source"

        class FakeCollector:
            DEFAULT_FINANCE_URL_INCLUDE_TOKENS = []
            DEFAULT_FINANCE_URL_EXCLUDE_TOKENS = []

            @staticmethod
            def parse_sources(_path: Path) -> list[Source]:
                return [Source("https://example.com/source-1"), Source("https://example.com/source-2")]

            @staticmethod
            def parse_keywords(_path: object, _raw: str) -> list[str]:
                return []

            @staticmethod
            def iso_utc(value: dt.datetime) -> str:
                return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

            @staticmethod
            def extract_from_source(source: Source, **_kwargs: object):
                suffix = source.url.rsplit("-", 1)[-1]
                return [Article(suffix)], {"source_articles_seen": 1, "download_errors": 0}

        previous = NEWSPAPER4K._collector
        NEWSPAPER4K._collector = FakeCollector
        try:
            provider = NEWSPAPER4K.Newspaper4kProvider(sources_file=Path("unused.txt"), sleep_seconds=0)
            batches = list(
                provider.fetch_window_batches(
                    window_start_utc="2026-05-07T00:00:00Z",
                    window_end_utc="2026-05-07T23:59:59Z",
                    tickers=["BHP"],
                )
            )
            self.assertEqual([len(batch) for batch in batches], [1, 1])

            rows = provider.fetch_window(
                window_start_utc="2026-05-07T00:00:00Z",
                window_end_utc="2026-05-07T23:59:59Z",
                tickers=["BHP"],
            )
            self.assertIsInstance(rows, list)
            self.assertEqual(len(rows), 2)
        finally:
            NEWSPAPER4K._collector = previous

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

    def test_gdelt_phrase_too_short_triggers_base_fallback(self):
        """GDELT's newer 'The specified phrase is too short.' error must trigger the
        base-query fallback, not silently swallow the failure."""
        class FakeProvider(GDELT.GdeltProvider):
            def __init__(self):
                super().__init__(max_records=50, max_ticker_batches=0, ticker_query_batch_size=0)
                self.queries = []

            def _request_json(self, url: str):
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("query", [""])[0]
                self.queries.append(query)
                # Simulate the newer GDELT API error variant (observed March 2026).
                if ".AX" in query or "Australian shares" in query:
                    raise RuntimeError(
                        "GDELT returned non-JSON payload: Expecting value: line 1 column 1 (char 0) "
                        "| preview='The specified phrase is too short.'"
                    )
                return {"articles": [{"title": "ASX news", "url": "https://example.com/asx", "seendate": "20260309143000"}]}

        provider = FakeProvider()
        rows = provider.fetch_window(
            window_start_utc="2026-03-09T00:00:00Z",
            window_end_utc="2026-03-09T23:59:59Z",
            tickers=[],
        )
        self.assertEqual(len(rows), 1, "base-query fallback must recover one article")
        self.assertGreaterEqual(len(provider.queries), 2, "must have attempted fallback query")
        self.assertGreaterEqual(int(provider.last_fetch_diagnostics.get("fallback_base_simple", 0)), 1)

    def test_gdelt_ticker_query_no_double_paren_on_base(self):
        """Combined ticker query must not double-wrap query_base — GDELT rejects ((base)) AND (...)."""
        provider = GDELT.GdeltProvider()
        query = provider._build_ticker_query(["BHP", "CBA"], include_query_base=True)
        # query_base already starts with '(' — wrapping again produces '((' which GDELT rejects.
        self.assertFalse(query.startswith("(("), f"double-paren detected: {query[:60]}")
        # The base expression must still appear at the start.
        self.assertTrue(query.startswith('("Australian'), f"base expression missing: {query[:60]}")

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
