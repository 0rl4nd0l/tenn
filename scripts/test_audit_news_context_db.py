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
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

AUDIT = load_module(str(SCRIPTS / "audit_news_context_db.py"), "audit_news_context_db")


class TestAuditNewsContextDb(unittest.TestCase):
    def test_build_report_flags_unknown_tickers_against_allowlist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "news.sqlite"
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE context_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        corpus TEXT,
                        doc_type TEXT,
                        doc_date TEXT,
                        published_at TEXT,
                        source TEXT,
                        ticker TEXT,
                        topic TEXT,
                        url TEXT,
                        file TEXT,
                        title TEXT,
                        company TEXT,
                        text TEXT
                    )
                    """
                )
                conn.executemany(
                    """
                    INSERT INTO context_chunks(
                        chunk_id, corpus, doc_type, doc_date, published_at, source, ticker,
                        topic, url, file, title, company, text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            "c1",
                            "news_gdelt",
                            "news_article",
                            "2026-02-24",
                            "2026-02-24T01:00:00Z",
                            "reuters.com",
                            "|AGL|",
                            "ASX",
                            "https://example.com/a1",
                            "https://example.com/a1",
                            "ASX:AGL guidance update",
                            "AGL",
                            "ASX:AGL updated guidance outlook in Australia.",
                        ),
                        (
                            "c2",
                            "news_gdelt",
                            "news_article",
                            "2026-02-24",
                            "2026-02-24T02:00:00Z",
                            "pr-inside.com",
                            "|TSLA|",
                            "lawsuit",
                            "https://example.com/a2",
                            "https://example.com/a2",
                            "NASDAQ:TSLA lawsuit notice",
                            "TSLA",
                            "NASDAQ:TSLA lawsuit notice unrelated to ASX.",
                        ),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

            report = AUDIT.build_report(
                db_path=db_path,
                corpus_filter="news_gdelt",
                doc_type_filter="news_article",
                top_n=5,
                ticker_allowlist={"AGL"},
            )

            self.assertEqual(report["coverage"]["chunks_total"], 2)
            self.assertEqual(report["coverage"]["chunks_with_ticker"], 2)
            self.assertEqual(report["ticker_quality"]["chunks_with_unknown_ticker"], 1)
            self.assertEqual(report["ticker_quality"]["chunks_all_tickers_allowlisted"], 1)


if __name__ == "__main__":
    unittest.main()
