#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
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
SCRIPTS = ROOT / "scripts"
MOD = load_module(SCRIPTS / "ingest_asx_rss_headlines.py", "ingest_asx_rss_headlines")


class IngestAsxRssHeadlinesTests(unittest.TestCase):
    def test_fixture_parsing_dedupe_and_identity_filtering(self):
        fixture_feed = (SCRIPTS / "testdata" / "asx_rss_fixture.xml").resolve()
        self.assertTrue(fixture_feed.exists(), "missing test fixture feed XML")

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            feeds_file = tmp / "feeds.txt"
            out_jsonl = tmp / "rss_rows.jsonl"
            asx_tickers = tmp / "asx_tickers.txt"
            identity_map = tmp / "ticker_identity_map.json"

            feeds_file.write_text(str(fixture_feed) + "\n", encoding="utf-8")
            asx_tickers.write_text("CSL\nBHP\nWBC\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps(
                    {
                        "CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL Ltd"]},
                        "BHP": {"canonical_names": ["BHP Group", "BHP Group Limited"], "aliases": []},
                    }
                ),
                encoding="utf-8",
            )

            report = MOD.ingest_asx_rss_headlines(
                feed_urls=[],
                feeds_file=feeds_file,
                out_jsonl=out_jsonl,
                asx_tickers_file=asx_tickers,
                identity_map_path=identity_map,
                corpus="news_asx_rss",
                topic="asx_rss_headline",
            )
            self.assertEqual(int(report["rows_written"]), 3)
            self.assertEqual(int(report["stats"]["duplicates_dropped"]), 1)
            self.assertEqual(int(report["stats"]["items_with_ticker"]), 2)

            rows = [json.loads(line) for line in out_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), 3)

            by_url = {str(row.get("url", "")): row for row in rows}
            csl_strong = by_url["https://www.fixture.com.au/news/csl-guidance"]
            csl_ambiguous = by_url["https://www.fixture.com.au/news/csl-ambiguous"]
            bhp_medium = by_url["https://www.fixture.com.au/news/bhp-dividend"]

            self.assertEqual(csl_strong.get("ticker"), "|CSL|")
            self.assertEqual(csl_strong.get("date"), "2026-02-24")
            self.assertEqual(csl_strong.get("source"), "fixture.com.au")
            self.assertEqual(csl_strong.get("corpus"), "news_asx_rss")
            self.assertEqual(csl_strong.get("topic"), "asx_rss_headline")
            self.assertEqual(csl_strong.get("extra_fields", {}).get("ticker_identity_strength"), "strong")

            self.assertEqual(csl_ambiguous.get("ticker"), "")
            self.assertIn("ambiguous_tickers", csl_ambiguous.get("extra_fields", {}))
            self.assertIn("CSL", csl_ambiguous.get("extra_fields", {}).get("ambiguous_tickers", []))
            self.assertEqual(csl_ambiguous.get("extra_fields", {}).get("ticker_identity_strength"), "ambiguous")

            self.assertEqual(bhp_medium.get("ticker"), "|BHP|")
            self.assertEqual(bhp_medium.get("extra_fields", {}).get("ticker_identity_strength"), "medium")
            self.assertEqual(
                bhp_medium.get("extra_fields", {}).get("source_domain"),
                "fixture.com.au",
            )

    def test_headline_token_path_accepts_non_ambiguous_and_gates_ambiguous(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            feed_xml = tmp / "ticker_tokens.xml"
            feeds_file = tmp / "feeds.txt"
            out_jsonl = tmp / "rss_rows.jsonl"
            asx_tickers = tmp / "asx_tickers.txt"
            identity_map = tmp / "ticker_identity_map.json"

            feed_xml.write_text(
                (
                    "<?xml version='1.0' encoding='UTF-8'?>\n"
                    "<rss version='2.0'>\n"
                    "  <channel>\n"
                    "    <title>Token Fixture Feed</title>\n"
                    "    <item>\n"
                    "      <title>BHP shares rise on earnings</title>\n"
                    "      <link>https://www.fixture.com.au/news/bhp-shares</link>\n"
                    "      <pubDate>Tue, 24 Feb 2026 09:30:00 GMT</pubDate>\n"
                    "      <description>Short market update.</description>\n"
                    "    </item>\n"
                    "    <item>\n"
                    "      <title>ASX:BHP shares rise on earnings</title>\n"
                    "      <link>https://www.fixture.com.au/news/bhp-asx-prefix</link>\n"
                    "      <pubDate>Tue, 24 Feb 2026 09:35:00 GMT</pubDate>\n"
                    "      <description>Short market update.</description>\n"
                    "    </item>\n"
                    "    <item>\n"
                    "      <title>CSL shares rise after broker note</title>\n"
                    "      <link>https://www.fixture.com/news/csl-non-au</link>\n"
                    "      <pubDate>Tue, 24 Feb 2026 09:45:00 GMT</pubDate>\n"
                    "      <description>Short market update.</description>\n"
                    "    </item>\n"
                    "    <item>\n"
                    "      <title>CSL shares rise as Communications Sales &amp; Leasing updates leasing portfolio</title>\n"
                    "      <link>https://www.fixture.com.au/news/csl-collision</link>\n"
                    "      <pubDate>Tue, 24 Feb 2026 10:00:00 GMT</pubDate>\n"
                    "      <description>Short market update.</description>\n"
                    "    </item>\n"
                    "    <item>\n"
                    "      <title>CSL shares rise on earnings outlook</title>\n"
                    "      <link>https://www.fixture.com.au/news/csl-confirmed</link>\n"
                    "      <pubDate>Tue, 24 Feb 2026 10:10:00 GMT</pubDate>\n"
                    "      <description>Short market update.</description>\n"
                    "    </item>\n"
                    "    <item>\n"
                    "      <title>RIO.AX dividend update</title>\n"
                    "      <link>https://www.fixture.com.au/news/rio-dividend</link>\n"
                    "      <pubDate>Tue, 24 Feb 2026 10:15:00 GMT</pubDate>\n"
                    "      <description>Short market update.</description>\n"
                    "    </item>\n"
                    "    <item>\n"
                    "      <title>CSL Limited confirms FY26 guidance</title>\n"
                    "      <link>https://www.fixture.com.au/news/csl-canonical</link>\n"
                    "      <pubDate>Tue, 24 Feb 2026 10:20:00 GMT</pubDate>\n"
                    "      <description>CSL Limited reaffirmed guidance.</description>\n"
                    "    </item>\n"
                    "  </channel>\n"
                    "</rss>\n"
                ),
                encoding="utf-8",
            )
            feeds_file.write_text(str(feed_xml) + "\n", encoding="utf-8")
            asx_tickers.write_text("BHP\nCSL\nRIO\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps(
                    {
                        "BHP": {"canonical_names": ["BHP Group Limited"], "aliases": ["BHP Group"]},
                        "CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL Ltd"]},
                        "RIO": {"canonical_names": ["Rio Tinto Limited"], "aliases": ["Rio Tinto"]},
                    }
                ),
                encoding="utf-8",
            )

            report = MOD.ingest_asx_rss_headlines(
                feed_urls=[],
                feeds_file=feeds_file,
                out_jsonl=out_jsonl,
                asx_tickers_file=asx_tickers,
                identity_map_path=identity_map,
                corpus="news_asx_rss",
                topic="asx_rss_headline",
            )
            stats = report["stats"]
            self.assertGreaterEqual(int(stats.get("ticker_token_hits", 0)), 4)
            self.assertGreaterEqual(int(stats.get("ticker_token_accepted", 0)), 2)
            self.assertGreaterEqual(int(stats.get("ticker_token_rejected_ambiguous", 0)), 2)

            rows = [json.loads(line) for line in out_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
            by_url = {str(row.get("url", "")): row for row in rows}

            bhp_row = by_url["https://www.fixture.com.au/news/bhp-shares"]
            self.assertEqual(bhp_row.get("ticker"), "|BHP|")
            self.assertEqual(bhp_row.get("extra_fields", {}).get("ticker_identity_strength"), "medium")
            self.assertIn("BHP", bhp_row.get("extra_fields", {}).get("ticker_token_matched", []))

            bhp_asx = by_url["https://www.fixture.com.au/news/bhp-asx-prefix"]
            self.assertEqual(bhp_asx.get("ticker"), "|BHP|")
            self.assertEqual(bhp_asx.get("extra_fields", {}).get("ticker_identity_strength"), "medium")

            csl_non_au = by_url["https://www.fixture.com/news/csl-non-au"]
            self.assertEqual(csl_non_au.get("ticker"), "")
            self.assertEqual(csl_non_au.get("extra_fields", {}).get("ticker_identity_strength"), "ambiguous")
            self.assertIn("CSL", csl_non_au.get("extra_fields", {}).get("ambiguous_tickers", []))

            csl_collision = by_url["https://www.fixture.com.au/news/csl-collision"]
            self.assertEqual(csl_collision.get("ticker"), "")
            self.assertIn(
                "CSL",
                csl_collision.get("extra_fields", {}).get("ticker_token_rejected_ambiguous", []),
            )

            csl_confirmed = by_url["https://www.fixture.com.au/news/csl-confirmed"]
            self.assertEqual(csl_confirmed.get("ticker"), "|CSL|")
            self.assertEqual(csl_confirmed.get("extra_fields", {}).get("ticker_identity_strength"), "medium")

            rio_row = by_url["https://www.fixture.com.au/news/rio-dividend"]
            self.assertEqual(rio_row.get("ticker"), "|RIO|")

            csl_canonical = by_url["https://www.fixture.com.au/news/csl-canonical"]
            self.assertEqual(csl_canonical.get("ticker"), "|CSL|")
            self.assertEqual(csl_canonical.get("extra_fields", {}).get("ticker_identity_strength"), "strong")


if __name__ == "__main__":
    unittest.main()
