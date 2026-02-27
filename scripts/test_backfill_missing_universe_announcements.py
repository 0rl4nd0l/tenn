import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
MOD = load_module(
    str(ROOT / "scripts" / "backfill_missing_universe_announcements.py"),
    "backfill_missing_universe_announcements",
)


class BackfillMissingUniverseAnnouncementsTests(unittest.TestCase):
    def test_extract_candidate_signals_captures_multiple_cues(self):
        signals = MOD._extract_candidate_signals(
            title="ASX:STO outlook update",
            description="Energy peer WDS.AX also moved.",
            body="mapped_tickers=STO,WDS\nsee XASX:QAN:ABC123",
            canonical_url="https://www.marketindex.com.au/asx/fmg/announcements/example",
        )
        self.assertIn("STO", signals)
        self.assertIn("WDS", signals)
        self.assertIn("QAN", signals)
        self.assertIn("FMG", signals)
        self.assertIn("asx_tag", signals["STO"])
        self.assertIn("mapped_tickers", signals["STO"])
        self.assertIn("ax_suffix", signals["WDS"])
        self.assertIn("xasx_tag", signals["QAN"])
        self.assertIn("url_asx_path", signals["FMG"])

    def test_collect_ticker_evidence_filters_by_provider_and_since(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "news_articles.sqlite"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE articles (
                        article_id TEXT PRIMARY KEY,
                        canonical_url TEXT,
                        url_hash TEXT,
                        title TEXT,
                        description TEXT,
                        body TEXT,
                        source_name TEXT,
                        language TEXT,
                        published_at_utc TEXT,
                        fetched_at_utc TEXT,
                        provider_best TEXT,
                        provider_item_id TEXT,
                        content_hash_exact TEXT,
                        content_hash_near TEXT,
                        quality_score REAL,
                        lane TEXT
                    )
                    """
                )
                conn.executemany(
                    """
                    INSERT INTO articles(
                        article_id, canonical_url, url_hash, title, description, body, source_name, language,
                        published_at_utc, fetched_at_utc, provider_best, provider_item_id,
                        content_hash_exact, content_hash_near, quality_score, lane
                    ) VALUES (?, ?, '', ?, ?, ?, '', 'en', ?, ?, ?, '', '', '', 0, 'high_precision')
                    """,
                    [
                        (
                            "a1",
                            "https://example.com/a1",
                            "World monitor cue",
                            "",
                            "mapped_tickers=STO,WDS",
                            "2026-02-27T00:00:00Z",
                            "2026-02-27T00:10:00Z",
                            "worldmonitor",
                        ),
                        (
                            "a2",
                            "https://example.com/a2",
                            "ASX:QAN expands route network",
                            "",
                            "",
                            "2026-02-27T00:00:00Z",
                            "2026-02-27T00:10:00Z",
                            "gdelt",
                        ),
                        (
                            "a3",
                            "https://example.com/a3",
                            "ASX:FMG old mention",
                            "",
                            "",
                            "2025-01-01T00:00:00Z",
                            "2025-01-01T00:10:00Z",
                            "gdelt",
                        ),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

            scanned, evidence = MOD.collect_ticker_evidence(
                news_articles_db=db_path,
                provider_filter=["worldmonitor", "gdelt"],
                since_utc="2026-01-01T00:00:00Z",
            )
            self.assertEqual(scanned, 2)
            self.assertIn("STO", evidence)
            self.assertIn("WDS", evidence)
            self.assertIn("QAN", evidence)
            self.assertNotIn("FMG", evidence)
            self.assertEqual(len(evidence["STO"].article_ids), 1)
            self.assertIn("worldmonitor", evidence["STO"].providers)

    def test_build_full_history_command(self):
        cmd = MOD.build_full_history_command(
            python_bin="/usr/bin/python3",
            full_history_script=Path("/repo/financial-engine_v2/scripts/full_history_ticker_sync.py"),
            tickers=["QAN", "STO", "QAN"],
            years=1,
            process_documents=True,
            full_history_report=Path("/repo/financial-engine_v2/reports/asx/report.json"),
            allow_warning=True,
        )
        self.assertEqual(
            cmd,
            [
                "/usr/bin/python3",
                "/repo/financial-engine_v2/scripts/full_history_ticker_sync.py",
                "--ticker",
                "QAN,STO",
                "--years",
                "1",
                "--report",
                "/repo/financial-engine_v2/reports/asx/report.json",
                "--process-documents",
                "--allow-warning",
            ],
        )


if __name__ == "__main__":
    unittest.main()
