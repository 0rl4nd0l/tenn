import contextlib
import importlib
import io
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
NEWSPAPER4K = importlib.import_module("news_pipeline.providers.newspaper4k")
CLI_COMMON = importlib.import_module("news_pipeline.cli_common")


class ProviderTests(unittest.TestCase):
    def test_newspaper4k_defaults_to_bounded_daily_profile(self):
        provider = NEWSPAPER4K.Newspaper4kProvider()
        self.assertEqual(provider.source_profile, "daily")
        self.assertEqual(provider.sources_file.name, "sources_au_finance_rss_only.txt")
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
        self.assertEqual(provider.sources_file.name, "sources_au_finance.txt")
        self.assertEqual(provider.max_total_articles, 12)
        self.assertEqual(provider.request_timeout_seconds, 7)
        self.assertFalse(provider.no_playwright)

    def test_newspaper4k_cli_kwargs_default_daily_disables_playwright(self):
        class Args:
            pass

        kwargs = CLI_COMMON.newspaper4k_kwargs_from_args(Args())
        self.assertEqual(kwargs["source_profile"], "daily")
        self.assertTrue(kwargs["no_playwright"])

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
                self.published_at = None
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
            def iso_utc(_value: object) -> str:
                return "2026-05-07T01:00:00Z"

            captured_kwargs: list[dict[str, object]] = []

            @classmethod
            def extract_from_source(cls, source: Source, **kwargs: object):
                cls.captured_kwargs.append(dict(kwargs))
                suffix = source.url.rsplit("-", 1)[-1]
                return [Article(suffix)], {"source_articles_seen": 1, "download_errors": 0}

        previous = NEWSPAPER4K._collector
        NEWSPAPER4K._collector = FakeCollector
        try:
            provider = NEWSPAPER4K.Newspaper4kProvider(sources_file=Path("unused.txt"), sleep_seconds=0)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                batches = list(
                    provider.fetch_window_batches(
                        window_start_utc="2026-05-07T00:00:00Z",
                        window_end_utc="2026-05-07T23:59:59Z",
                        tickers=["BHP"],
                    )
                )
            self.assertEqual([len(batch) for batch in batches], [1, 1])
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("[newspaper4k]", stderr.getvalue())
            self.assertTrue(FakeCollector.captured_kwargs)
            self.assertFalse(any("playwright_domains" in item for item in FakeCollector.captured_kwargs))

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                rows = provider.fetch_window(
                    window_start_utc="2026-05-07T00:00:00Z",
                    window_end_utc="2026-05-07T23:59:59Z",
                    tickers=["BHP"],
                )
            self.assertEqual(len(rows), 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("[newspaper4k]", stderr.getvalue())
        finally:
            NEWSPAPER4K._collector = previous

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
