#!/usr/bin/env python3
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
NEWS = load_module(SCRIPTS / "build_news_context_db.py", "build_news_context_db_rss_mode")


class BuildNewsContextDbRssModeTests(unittest.TestCase):
    def _run_build(
        self,
        *,
        feeds_file: Path,
        out_db: Path,
        allowlist: Path,
        identity_map: Path,
        health_json: Path,
        rss_min_text_chars: int | None = None,
        min_text_chars: int | None = None,
    ) -> int:
        argv = [
            "build_news_context_db.py",
            "--input-rss-feeds-file",
            str(feeds_file),
            "--ticker-allowlist-path",
            str(allowlist),
            "--rss-identity-map-path",
            str(identity_map),
            "--db",
            "sqlite",
            "--out",
            str(out_db),
            "--embed-backend",
            "hash",
            "--hash-dim",
            "64",
            "--row-batch-size",
            "1",
            "--health-json",
            str(health_json),
            "--research-only-ack",
        ]
        if min_text_chars is not None:
            argv.extend(["--min-text-chars", str(int(min_text_chars))])
        if rss_min_text_chars is not None:
            argv.extend(["--rss-min-text-chars", str(int(rss_min_text_chars))])
        with mock.patch.object(sys, "argv", argv):
            return int(NEWS.main())

    def test_rss_mode_forces_news_asx_rss_and_indexes_rows(self):
        fixture_feed = (SCRIPTS / "testdata" / "asx_rss_fixture.xml").resolve()
        self.assertTrue(fixture_feed.exists(), "missing RSS test fixture")

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            feeds_file = tmp / "feeds.txt"
            out_db = tmp / "news.sqlite"
            allowlist = tmp / "asx_tickers.txt"
            identity_map = tmp / "ticker_identity_map.json"

            feeds_file.write_text(str(fixture_feed) + "\n", encoding="utf-8")
            allowlist.write_text("CSL\nBHP\nWBC\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps(
                    {
                        "CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL Ltd"]},
                        "BHP": {"canonical_names": ["BHP Group", "BHP Group Limited"], "aliases": []},
                    }
                ),
                encoding="utf-8",
            )

            rc = self._run_build(
                feeds_file=feeds_file,
                out_db=out_db,
                allowlist=allowlist,
                identity_map=identity_map,
                health_json=tmp / "missing_health_snapshot.json",
            )
            self.assertEqual(rc, 0)

            conn = sqlite3.connect(str(out_db))
            try:
                cur = conn.cursor()
                row = cur.execute("SELECT COUNT(*), MIN(corpus), MAX(corpus) FROM context_chunks").fetchone()
                count = int((row or [0])[0] or 0)
                min_corpus = str((row or ["", "", ""])[1] or "")
                max_corpus = str((row or ["", "", ""])[2] or "")
            finally:
                conn.close()

            self.assertGreater(count, 0)
            self.assertEqual(min_corpus, "news_asx_rss")
            self.assertEqual(max_corpus, "news_asx_rss")

    def test_rss_min_text_chars_controls_short_headline_indexing(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            feed_xml = tmp / "short_feed.xml"
            feeds_file = tmp / "feeds.txt"
            allowlist = tmp / "asx_tickers.txt"
            identity_map = tmp / "ticker_identity_map.json"

            feed_xml.write_text(
                (
                    "<?xml version='1.0' encoding='UTF-8'?>\n"
                    "<rss version='2.0'>\n"
                    "  <channel>\n"
                    "    <title>Fixture ASX Feed</title>\n"
                    "    <item>\n"
                    "      <title>CSL Limited trading update</title>\n"
                    "      <link>https://fixture.com.au/news/csl-short</link>\n"
                    "      <pubDate>Tue, 24 Feb 2026 09:30:00 GMT</pubDate>\n"
                    "      <description>CSL Limited confirms guidance and dividend plan.</description>\n"
                    "    </item>\n"
                    "  </channel>\n"
                    "</rss>\n"
                ),
                encoding="utf-8",
            )
            feeds_file.write_text(str(feed_xml) + "\n", encoding="utf-8")
            allowlist.write_text("CSL\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps({"CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL Ltd"]}}),
                encoding="utf-8",
            )

            out_db_low = tmp / "news_low.sqlite"
            rc_low = self._run_build(
                feeds_file=feeds_file,
                out_db=out_db_low,
                allowlist=allowlist,
                identity_map=identity_map,
                health_json=tmp / "missing_health_low.json",
                min_text_chars=200,
                rss_min_text_chars=40,
            )
            self.assertEqual(rc_low, 0)
            conn = sqlite3.connect(str(out_db_low))
            try:
                low_count = int((conn.execute("SELECT COUNT(*) FROM context_chunks").fetchone() or [0])[0] or 0)
            finally:
                conn.close()
            self.assertGreater(low_count, 0)

            out_db_high = tmp / "news_high.sqlite"
            rc_high = self._run_build(
                feeds_file=feeds_file,
                out_db=out_db_high,
                allowlist=allowlist,
                identity_map=identity_map,
                health_json=tmp / "missing_health_high.json",
                min_text_chars=200,
                rss_min_text_chars=200,
            )
            self.assertEqual(rc_high, 1)
            conn = sqlite3.connect(str(out_db_high))
            try:
                high_count = int((conn.execute("SELECT COUNT(*) FROM context_chunks").fetchone() or [0])[0] or 0)
            finally:
                conn.close()
            self.assertEqual(high_count, 0)


if __name__ == "__main__":
    unittest.main()
