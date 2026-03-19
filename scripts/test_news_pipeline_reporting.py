import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
DB = importlib.import_module("news_pipeline.db")
REPORT = importlib.import_module("news_pipeline.reporting")


class ReportingTests(unittest.TestCase):
    def _insert_article(
        self,
        *,
        conn,
        article_id: str,
        provider: str,
        published_at_utc: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO articles(
                article_id, canonical_url, url_hash, title, description, body, source_name, language,
                published_at_utc, fetched_at_utc, provider_best, provider_item_id,
                content_hash_exact, content_hash_near, quality_score, lane
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                f"https://example.com/{article_id}",
                f"urlhash_{article_id}",
                f"title {article_id}",
                "desc",
                "body",
                "example",
                "en",
                published_at_utc,
                "2026-02-24T12:00:00Z",
                provider,
                f"item_{article_id}",
                f"exact_{article_id}",
                f"near_{article_id}",
                0.8,
                "high_precision",
            ),
        )

    def test_write_run_reports_materializes_declared_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "news_articles.sqlite"
            tickers = tmp / "tickers.txt"
            out_dir = tmp / "reports"
            tickers.write_text("BHP\nCSL\n", encoding="utf-8")
            store = DB.NewsArticleStore(db_path)
            store.close()

            summary = REPORT.write_run_reports(
                db_path=db_path,
                run_id="run_missing",
                out_dir=out_dir,
                ticker_universe_path=tickers,
                failures=None,
            )

            outputs = dict(summary.get("outputs") or {})
            for rel_path in outputs.values():
                self.assertTrue((out_dir / str(rel_path)).exists(), str(rel_path))
            bands_payload = json.loads((out_dir / "entity_link_confidence_bands.json").read_text(encoding="utf-8"))
            windows_payload = json.loads((out_dir / "provider_run_windows_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(dict(bands_payload.get("lanes") or {}), {})
            self.assertEqual(dict(windows_payload.get("providers") or {}), {})

    def test_confidence_bands_are_scoped_to_run_windows(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "news_articles.sqlite"
            tickers = tmp / "tickers.txt"
            out_dir = tmp / "reports"
            tickers.write_text("BHP\n", encoding="utf-8")
            store = DB.NewsArticleStore(db_path)
            try:
                conn = store.conn
                conn.execute(
                    """
                    INSERT INTO provider_runs(run_id, provider, mode, params_json, started_at, status)
                    VALUES (?, ?, 'backfill', '{}', ?, 'success')
                    """,
                    ("run_scope", "gdelt", "2026-02-25T00:00:00Z"),
                )
                conn.execute(
                    """
                    INSERT INTO provider_run_windows(
                        run_id, provider, window_start_utc, window_end_utc, status,
                        fetched, inserted, deduped, rejected, errors
                    ) VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 0)
                    """,
                    (
                        "run_scope",
                        "gdelt",
                        "2026-02-24T00:00:00Z",
                        "2026-02-25T00:00:00Z",
                        "completed",
                    ),
                )
                self._insert_article(
                    conn=conn,
                    article_id="art_in",
                    provider="gdelt",
                    published_at_utc="2026-02-24T12:00:00Z",
                )
                self._insert_article(
                    conn=conn,
                    article_id="art_out",
                    provider="gdelt",
                    published_at_utc="2026-02-26T12:00:00Z",
                )
                conn.execute(
                    """
                    INSERT INTO entity_links(article_id, ticker, confidence, lane, method, published_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("art_in", "BHP", 0.95, "high_precision", "alias", "2026-02-24T12:00:00Z"),
                )
                conn.execute(
                    """
                    INSERT INTO entity_links(article_id, ticker, confidence, lane, method, published_at_utc)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("art_out", "BHP", 0.2, "high_precision", "alias", "2026-02-26T12:00:00Z"),
                )
                conn.commit()
            finally:
                store.close()

            REPORT.write_run_reports(
                db_path=db_path,
                run_id="run_scope",
                out_dir=out_dir,
                ticker_universe_path=tickers,
                failures=None,
            )
            bands_payload = json.loads((out_dir / "entity_link_confidence_bands.json").read_text(encoding="utf-8"))
            hp = dict((bands_payload.get("lanes") or {}).get("high_precision") or {})
            self.assertEqual(int(hp.get("total", 0)), 1)
            bands = dict(hp.get("bands") or {})
            self.assertEqual(int(dict(bands.get("0.9-1.0") or {}).get("count", 0)), 1)
            self.assertEqual(int(dict(bands.get("0.0-0.4") or {}).get("count", 0)), 0)


if __name__ == "__main__":
    unittest.main()
