#!/usr/bin/env python3
import importlib.util
import json
import sqlite3
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
MOD = load_module(ROOT / "scripts" / "quantify_asx_news_identity_coverage.py", "quantify_asx_news_identity_coverage")


def _init_db(path: Path) -> None:
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
                "c1",
                "news",
                "CSL Limited announces FY26 guidance",
                "The company said earnings are on track.",
                "https://www.afr.com.au/markets/csl-guidance",
                "afr.com.au",
                "|CSL|",
            ),
            (
                "c2",
                "news",
                "Communications Sales & Leasing (CSL) posts update",
                "A US REIT update for the landlord business.",
                "https://www.reuters.com/world/us/csl-update",
                "reuters.com",
                "|CSL|",
            ),
            (
                "c3",
                "news",
                "ASX:BHP earnings beat forecasts",
                "BHP posted stronger-than-expected production.",
                "https://www.example.com.au/markets/bhp-earnings",
                "example.com.au",
                "|BHP|",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO context_chunks(
                chunk_id, corpus, title, text, url, source, ticker
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


class QuantifyAsxIdentityCoverageTests(unittest.TestCase):
    def test_identity_aware_baseline_counts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db_path = root / "news.sqlite"
            tickers_file = root / "asx.txt"
            identity_map_path = root / "ticker_identity_map.json"
            out_json = root / "out.json"

            _init_db(db_path)
            tickers_file.write_text("CSL\nBHP\nWBC\n", encoding="utf-8")
            identity_map_path.write_text(
                json.dumps(
                    {
                        "CSL": {
                            "canonical_names": ["CSL Limited"],
                            "aliases": ["CSL Ltd"],
                        },
                        "BHP": {
                            "canonical_names": ["BHP Group", "BHP Group Limited"],
                            "aliases": [],
                        },
                    }
                ),
                encoding="utf-8",
            )

            payload = MOD.quantify_asx_news_identity_coverage(
                news_db_path=db_path,
                corpus="news",
                asx_tickers_file=tickers_file,
                identity_map_path=identity_map_path,
            )
            MOD._atomic_write_json(out_json, payload)
            persisted = json.loads(out_json.read_text(encoding="utf-8"))

            self.assertEqual(int(persisted["total_chunks"]), 3)
            self.assertEqual(int(persisted["unique_articles_estimated"]), 3)

            summary = persisted["asx_identity_summary"]
            self.assertEqual(int(summary["asx_chunks_strong_or_medium"]), 2)
            self.assertEqual(int(summary["asx_chunks_ambiguous"]), 1)
            self.assertAlmostEqual(float(summary["pct_chunks_strong_or_medium"]), 66.6667, places=4)
            self.assertAlmostEqual(float(summary["pct_chunks_ambiguous"]), 33.3333, places=4)

            csl = persisted["per_ticker_identity_counts"]["CSL"]
            bhp = persisted["per_ticker_identity_counts"]["BHP"]
            wbc = persisted["per_ticker_identity_counts"]["WBC"]
            self.assertEqual(int(csl["strong"]), 1)
            self.assertEqual(int(csl["ambiguous"]), 1)
            self.assertEqual(int(bhp["medium"]), 1)
            self.assertEqual(int(wbc["strong"]), 0)
            self.assertEqual(int(wbc["medium"]), 0)
            self.assertEqual(int(wbc["ambiguous"]), 0)

            self.assertIn("WBC", persisted["tickers_with_zero_strong_hits"])
            self.assertNotIn("BHP", persisted["tickers_with_zero_strong_hits"])
            self.assertNotIn("CSL", persisted["tickers_with_zero_strong_hits"])

            top_au = persisted["top_au_domains"]
            self.assertEqual(int(top_au.get("afr.com.au", 0)), 1)
            self.assertEqual(int(top_au.get("example.com.au", 0)), 1)


if __name__ == "__main__":
    unittest.main()
