import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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
PROBE = load_module(ROOT / "scripts" / "probe_news_provider_coverage.py", "news_pipeline_probe_news_provider_coverage")


class ProbeProviderCoverageTests(unittest.TestCase):
    def test_probe_from_eodhd_capture(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            tickers = tmp / "tickers.txt"
            captures = tmp / "captures"
            captures.mkdir(parents=True, exist_ok=True)
            tickers.write_text("BHP\n", encoding="utf-8")
            (captures / "symbol_BHP_sample.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "1",
                            "title": "ASX:BHP guidance update",
                            "link": "https://example.com/bhp",
                            "date": "2026-02-24T09:30:00Z",
                            "source": "Example",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = PROBE.main(
                    [
                        "--provider",
                        "eodhd",
                        "--window-days",
                        "30",
                        "--tickers",
                        "BHP",
                        "--tickers-file",
                        str(tickers),
                        "--eodhd-capture-dir",
                        str(captures),
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertIn("providers", payload)
            self.assertEqual(payload["providers"][0]["provider"], "eodhd")
            bhp = payload["providers"][0]["tickers"]["BHP"]
            self.assertEqual(int(bhp["articles_returned"]), 1)
            self.assertEqual(float(bhp["pct_valid_published_at"]), 100.0)

    def test_probe_keeps_requested_tickers_not_in_universe(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            tickers = tmp / "tickers.txt"
            captures = tmp / "captures"
            captures.mkdir(parents=True, exist_ok=True)
            tickers.write_text("BHP\n", encoding="utf-8")

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = PROBE.main(
                    [
                        "--provider",
                        "eodhd",
                        "--window-days",
                        "30",
                        "--tickers",
                        "BHP,CBA.AX",
                        "--tickers-file",
                        str(tickers),
                        "--eodhd-capture-dir",
                        str(captures),
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["tickers"], ["BHP", "CBA"])
            self.assertEqual(payload["unknown_tickers_not_in_universe"], ["CBA"])

    def test_probe_gdelt_batches_fetch_once_and_splits_by_ticker(self):
        class FakeCandidate:
            def __init__(self, title: str, url: str, source_name: str):
                self.title = title
                self.canonical_url = url
                self.source_name = source_name

        class FakeParseResult:
            def __init__(self, candidate):
                self.candidate = candidate

        class FakeGdeltProvider:
            name = "gdelt"

            def __init__(self):
                self.calls = 0

            def fetch_window(self, *, window_start_utc, window_end_utc, tickers):
                self.calls += 1
                return [
                    {"title": "ASX:BHP rises after update", "url": "https://example.com/bhp"},
                    {"title": "ASX:CSL guidance unchanged", "url": "https://example.com/csl"},
                    {"title": "Macro headline", "url": "https://example.com/macro"},
                ]

            def parse_item(self, item, fetched_at_utc):
                title = str(item.get("title") or "")
                return FakeParseResult(FakeCandidate(title=title, url=str(item.get("url") or ""), source_name="Example"))

        provider = FakeGdeltProvider()
        summary = PROBE._probe_provider(
            provider_name="gdelt",
            provider_obj=provider,
            tickers=["BHP", "CSL"],
            window_start_utc="2026-01-26T00:00:00Z",
            window_end_utc="2026-02-25T00:00:00Z",
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(int(summary["tickers"]["BHP"]["articles_returned"]), 1)
        self.assertEqual(int(summary["tickers"]["CSL"]["articles_returned"]), 1)

    def test_row_mentions_short_symbol_requires_asx_context(self):
        us_row = {
            "title": "Western Midstream Partners (NYSE: WES) upgraded",
            "url": "https://example.com/us-wes",
        }
        asx_row = {
            "title": "WES rises after earnings update",
            "url": "https://example.com/asx-wes",
        }
        self.assertFalse(PROBE._row_mentions_ticker(us_row, "WES"))
        self.assertTrue(PROBE._row_mentions_ticker(asx_row, "WES"))

    def test_probe_gdelt_asx_wide_mode(self):
        class FakeCandidate:
            def __init__(self, title: str, url: str, source_name: str):
                self.title = title
                self.canonical_url = url
                self.source_name = source_name

        class FakeParseResult:
            def __init__(self, candidate):
                self.candidate = candidate

        class FakeGdeltProvider:
            name = "gdelt"

            def __init__(self):
                self.calls = 0
                self.last_tickers = None

            def fetch_window(self, *, window_start_utc, window_end_utc, tickers):
                self.calls += 1
                self.last_tickers = list(tickers)
                return [
                    {"title": "ASX market wraps higher", "url": "https://example.com/1"},
                    {"title": "ASX miners mixed", "url": "https://example.com/2"},
                ]

            def parse_item(self, item, fetched_at_utc):
                return FakeParseResult(
                    FakeCandidate(
                        title=str(item.get("title") or ""),
                        url=str(item.get("url") or ""),
                        source_name="Example",
                    )
                )

        provider = FakeGdeltProvider()
        summary = PROBE._probe_provider(
            provider_name="gdelt",
            provider_obj=provider,
            tickers=["BHP", "CSL"],
            window_start_utc="2026-01-26T00:00:00Z",
            window_end_utc="2026-02-25T00:00:00Z",
            asx_wide=True,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(provider.last_tickers, [])
        self.assertEqual(int(summary["provider_articles_fetched_total"]), 2)
        self.assertIn("asx_wide", summary)
        self.assertEqual(int(summary["asx_wide"]["articles_returned"]), 2)
        self.assertEqual(float(summary["asx_wide"]["pct_valid_published_at"]), 100.0)

    def test_probe_worldmonitor_forces_asx_wide_mode(self):
        class FakeCandidate:
            def __init__(self, title: str, url: str, source_name: str):
                self.title = title
                self.canonical_url = url
                self.source_name = source_name

        class FakeParseResult:
            def __init__(self, candidate):
                self.candidate = candidate

        class FakeWorldMonitorProvider:
            name = "worldmonitor"

            def __init__(self):
                self.calls = 0
                self.last_tickers = None

            def fetch_window(self, *, window_start_utc, window_end_utc, tickers):
                self.calls += 1
                self.last_tickers = list(tickers)
                return [{"title": "World monitor theater posture", "url": "https://example.com/wm"}]

            def parse_item(self, item, fetched_at_utc):
                return FakeParseResult(
                    FakeCandidate(
                        title=str(item.get("title") or ""),
                        url=str(item.get("url") or ""),
                        source_name="worldmonitor",
                    )
                )

        provider = FakeWorldMonitorProvider()
        summary = PROBE._probe_provider(
            provider_name="worldmonitor",
            provider_obj=provider,
            tickers=["BHP", "CSL"],
            window_start_utc="2026-01-26T00:00:00Z",
            window_end_utc="2026-02-25T00:00:00Z",
            asx_wide=False,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(provider.last_tickers, [])
        self.assertIn("asx_wide", summary)
        self.assertEqual(int(summary["asx_wide"]["articles_returned"]), 1)


if __name__ == "__main__":
    unittest.main()
