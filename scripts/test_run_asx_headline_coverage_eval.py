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
MOD = load_module(SCRIPTS / "run_asx_headline_coverage_eval.py", "run_asx_headline_coverage_eval")


def init_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE context_chunks (
                chunk_id TEXT PRIMARY KEY,
                corpus TEXT,
                title TEXT,
                text TEXT,
                url TEXT,
                source TEXT,
                ticker TEXT
            )
            """
        )
        rows = [
            (
                "n1",
                "news",
                "CSL Limited announces earnings guidance",
                "CSL Limited said FY guidance remains intact.",
                "https://www.afr.com.au/markets/csl-guidance",
                "afr.com.au",
                "|CSL|",
            ),
            (
                "n2",
                "news",
                "Global macro update",
                "US markets were mixed after macro releases.",
                "https://www.example.com/world/macro",
                "example.com",
                "",
            ),
            (
                "r1",
                "news_asx_rss",
                "ASX:BHP dividend lift",
                "BHP announced higher dividends after stronger earnings.",
                "https://www.fixture.com.au/news/bhp-dividend",
                "fixture.com.au",
                "|BHP|",
            ),
            (
                "r2",
                "news_asx_rss",
                "CSL Limited updates outlook",
                "CSL Limited provided an updated outlook for FY26.",
                "https://www.fixture.com.au/news/csl-outlook",
                "fixture.com.au",
                "|CSL|",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO context_chunks(chunk_id, corpus, title, text, url, source, ticker)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


class RunAsxHeadlineCoverageEvalTests(unittest.TestCase):
    def test_summary_metrics_and_delta(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "news.sqlite"
            tickers_file = tmp / "asx.txt"
            identity_map = tmp / "ticker_identity_map.json"
            out_json = tmp / "summary.json"
            init_db(db_path)
            tickers_file.write_text("CSL\nBHP\nWBC\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps(
                    {
                        "CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL Ltd"]},
                        "BHP": {"canonical_names": ["BHP Group", "BHP Group Limited"], "aliases": []},
                    }
                ),
                encoding="utf-8",
            )

            argv = [
                "run_asx_headline_coverage_eval.py",
                "--news-db-path",
                str(db_path),
                "--asx-tickers-file",
                str(tickers_file),
                "--identity-map-path",
                str(identity_map),
                "--baseline-corpus",
                "news",
                "--rss-corpus",
                "news_asx_rss",
                "--out-json",
                str(out_json),
            ]
            with mock.patch.object(sys, "argv", argv):
                rc = MOD.main()
            self.assertEqual(rc, 0)

            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["baseline"]["corpus"], "news")
            self.assertEqual(payload["rss"]["corpus"], "news_asx_rss")
            self.assertAlmostEqual(float(payload["baseline"]["pct_chunks_strong_or_medium"]), 50.0, places=4)
            self.assertAlmostEqual(float(payload["rss"]["pct_chunks_strong_or_medium"]), 100.0, places=4)
            self.assertEqual(int(payload["baseline"]["tickers_zero_hits"]), 2)
            self.assertEqual(int(payload["rss"]["tickers_zero_hits"]), 1)
            self.assertAlmostEqual(float(payload["delta_pct_points"]), 50.0, places=4)


if __name__ == "__main__":
    unittest.main()
