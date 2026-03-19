import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

QUANT = load_module(str(SCRIPTS / "quantify_asx_news_coverage.py"), "quantify_asx_news_coverage")
COMPARE = load_module(str(SCRIPTS / "compare_asx_coverage.py"), "compare_asx_coverage")


def make_news_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE context_chunks (
                chunk_id TEXT PRIMARY KEY,
                corpus TEXT NOT NULL,
                ticker TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        rows = [
            (
                "c1",
                "news",
                "|BHP|",
                "ASX: BHP shares rise on earnings beat",
                "BHP rose after guidance upgrades.",
                "https://www.news.com.au/markets/a1",
                "news.com.au",
            ),
            (
                "c2",
                "news",
                "",
                "ASX: BHP shares rise on earnings beat",
                "ASX investors tracked BHP momentum into close.",
                "https://www.news.com.au/markets/a1",
                "news.com.au",
            ),
            (
                "c3",
                "news",
                "",
                "RIO dividend guidance update",
                "RIO announced a larger dividend and FY guidance.",
                "https://www.abc.com.au/business/a2",
                "abc.com.au",
            ),
            (
                "c4",
                "news",
                "",
                "Wall Street opens mixed",
                "US equities were mixed in late trading.",
                "https://example.com/us/a3",
                "example.com",
            ),
            (
                "c5",
                "news_gdelt",
                "|BHP|",
                "Other corpus row",
                "Ignored by corpus filter",
                "https://www.news.com.au/markets/a4",
                "news.com.au",
            ),
        ]
        cur.executemany(
            "INSERT INTO context_chunks(chunk_id, corpus, ticker, title, text, url, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


class TestAsxCoverageQuantification(unittest.TestCase):
    def test_quantify_asx_news_coverage_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db_path = tmp / "news.sqlite"
            tickers_path = tmp / "asx_tickers.txt"
            out_path = tmp / "baseline.json"
            make_news_db(db_path)
            tickers_path.write_text("BHP\nRIO\nCSL\n", encoding="utf-8")

            argv = [
                "quantify_asx_news_coverage.py",
                "--news-db-path",
                str(db_path),
                "--corpus",
                "news",
                "--asx-tickers-file",
                str(tickers_path),
                "--out-json",
                str(out_path),
            ]
            with mock.patch.object(sys, "argv", argv):
                rc = QUANT.main()
            self.assertEqual(rc, 0)

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(int(payload["total_chunks"]), 4)
            self.assertEqual(int(payload["articles_estimated"]), 3)

            asx_summary = payload["asx_summary"]
            self.assertEqual(int(asx_summary["tickers_total"]), 3)
            self.assertEqual(int(asx_summary["tickers_with_hits"]), 2)
            self.assertEqual(int(asx_summary["tickers_zero_hits"]), 1)
            self.assertEqual(float(asx_summary["chunks_with_asx_ticker_pct"]), 75.0)
            self.assertEqual(float(asx_summary["median_articles_per_ticker"]), 1.0)
            self.assertEqual(float(payload["asx_keyword_pct"]), 50.0)

            self.assertEqual(int(payload["per_ticker_counts"]["BHP"]), 1)
            self.assertEqual(int(payload["per_ticker_counts"]["RIO"]), 1)
            self.assertEqual(int(payload["per_ticker_counts"]["CSL"]), 0)
            self.assertEqual(payload["zero_hit_tickers"], ["CSL"])
            self.assertEqual(int(payload["top_au_domains"]["news.com.au"]), 2)
            self.assertEqual(int(payload["top_au_domains"]["abc.com.au"]), 1)

    def test_compare_asx_coverage_deltas(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            baseline_path = tmp / "baseline.json"
            optimised_path = tmp / "optimised.json"
            out_path = tmp / "compare.json"

            baseline_payload = {
                "asx_summary": {
                    "chunks_with_asx_ticker_pct": 10.0,
                    "tickers_with_hits": 5,
                    "median_articles_per_ticker": 1.2,
                }
            }
            optimised_payload = {
                "asx_summary": {
                    "chunks_with_asx_ticker_pct": 35.0,
                    "tickers_with_hits": 9,
                    "median_articles_per_ticker": 2.0,
                }
            }
            baseline_path.write_text(json.dumps(baseline_payload), encoding="utf-8")
            optimised_path.write_text(json.dumps(optimised_payload), encoding="utf-8")

            argv = [
                "compare_asx_coverage.py",
                "--baseline-json",
                str(baseline_path),
                "--optimised-json",
                str(optimised_path),
                "--out-json",
                str(out_path),
            ]
            with mock.patch.object(sys, "argv", argv):
                rc = COMPARE.main()
            self.assertEqual(rc, 0)

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(float(payload["baseline_chunks_with_asx_pct"]), 10.0)
            self.assertEqual(float(payload["optimised_chunks_with_asx_pct"]), 35.0)
            self.assertEqual(int(payload["baseline_tickers_with_hits"]), 5)
            self.assertEqual(int(payload["optimised_tickers_with_hits"]), 9)
            self.assertEqual(float(payload["coverage_delta_pct"]), 25.0)
            self.assertEqual(float(payload["median_articles_delta"]), 0.8)


if __name__ == "__main__":
    unittest.main()
