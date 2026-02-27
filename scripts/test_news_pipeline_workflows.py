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
BACKFILL = load_module(ROOT / "scripts" / "backfill_news.py", "news_pipeline_backfill_news")
DAILY = load_module(ROOT / "scripts" / "fetch_daily_news.py", "news_pipeline_fetch_daily_news")
CHUNKS = load_module(ROOT / "scripts" / "build_news_chunks.py", "news_pipeline_build_news_chunks")
REPORT = load_module(ROOT / "scripts" / "report_news_coverage.py", "news_pipeline_report_news_coverage")


class WorkflowTests(unittest.TestCase):
    def test_backfill_resume_daily_idempotence_chunks_and_reports(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            news_articles_db = tmp / "news_articles.sqlite"
            news_context_db = tmp / "news.sqlite"
            tickers_file = tmp / "tickers.txt"
            identity_map = tmp / "identity_map.json"
            capture_dir = tmp / "captures"
            runs_root = tmp / "news_runs"
            capture_dir.mkdir(parents=True, exist_ok=True)

            tickers_file.write_text("BHP\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps({"BHP": {"canonical_names": ["BHP Group"], "aliases": ["BHP"]}}),
                encoding="utf-8",
            )
            (capture_dir / "market_news_sample.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "mk1",
                            "title": "ASX:BHP posts production update",
                            "link": "https://example.com/market/bhp",
                            "date": "2026-02-24T09:30:00Z",
                            "source": "Example AU",
                            "description": "BHP released an ASX production update.",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (capture_dir / "symbol_BHP_sample.json").write_text(
                json.dumps(
                    [
                        {
                            "id": "sym1",
                            "title": "ASX:BHP guidance reaffirmed",
                            "link": "https://example.com/symbol/bhp",
                            "date": "2026-02-24T11:00:00Z",
                            "source": "Example AU",
                            "description": "Guidance remains unchanged.",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            rc = BACKFILL.main(
                [
                    "--provider",
                    "eodhd",
                    "--from",
                    "2026-02-24",
                    "--to",
                    "2026-02-24",
                    "--run-id",
                    "run_backfill_test",
                    "--news-articles-db",
                    str(news_articles_db),
                    "--tickers-file",
                    str(tickers_file),
                    "--identity-map-path",
                    str(identity_map),
                    "--eodhd-capture-dir",
                    str(capture_dir),
                    "--news-runs-root",
                    str(runs_root),
                ]
            )
            self.assertEqual(rc, 0)

            conn = sqlite3.connect(str(news_articles_db))
            try:
                row = conn.execute("SELECT fetched, inserted, deduped FROM provider_runs WHERE run_id = 'run_backfill_test'").fetchone()
                self.assertIsNotNone(row)
                fetched_1, inserted_1, deduped_1 = int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)
                self.assertGreater(fetched_1, 0)
                self.assertGreater(inserted_1, 0)
            finally:
                conn.close()

            rc = BACKFILL.main(
                [
                    "--provider",
                    "eodhd",
                    "--from",
                    "2026-02-24",
                    "--to",
                    "2026-02-24",
                    "--run-id",
                    "run_backfill_test",
                    "--news-articles-db",
                    str(news_articles_db),
                    "--tickers-file",
                    str(tickers_file),
                    "--identity-map-path",
                    str(identity_map),
                    "--eodhd-capture-dir",
                    str(capture_dir),
                    "--news-runs-root",
                    str(runs_root),
                ]
            )
            self.assertEqual(rc, 0)
            conn = sqlite3.connect(str(news_articles_db))
            try:
                row = conn.execute("SELECT fetched, inserted, deduped FROM provider_runs WHERE run_id = 'run_backfill_test'").fetchone()
                self.assertIsNotNone(row)
                fetched_2, inserted_2, deduped_2 = int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)
                self.assertEqual(fetched_2, fetched_1)
                self.assertEqual(inserted_2, inserted_1)
                self.assertEqual(deduped_2, deduped_1)
                win_count = int((conn.execute("SELECT COUNT(*) FROM provider_run_windows WHERE run_id = 'run_backfill_test'").fetchone() or [0])[0] or 0)
                self.assertEqual(win_count, 1)
            finally:
                conn.close()

            rc = DAILY.main(
                [
                    "--providers",
                    "eodhd",
                    "--since-hours",
                    "36",
                    "--lane",
                    "high_precision",
                    "--news-articles-db",
                    str(news_articles_db),
                    "--tickers-file",
                    str(tickers_file),
                    "--identity-map-path",
                    str(identity_map),
                    "--eodhd-capture-dir",
                    str(capture_dir),
                    "--news-runs-root",
                    str(runs_root),
                ]
            )
            self.assertEqual(rc, 0)
            rc = DAILY.main(
                [
                    "--providers",
                    "eodhd",
                    "--since-hours",
                    "36",
                    "--lane",
                    "high_precision",
                    "--news-articles-db",
                    str(news_articles_db),
                    "--tickers-file",
                    str(tickers_file),
                    "--identity-map-path",
                    str(identity_map),
                    "--eodhd-capture-dir",
                    str(capture_dir),
                    "--news-runs-root",
                    str(runs_root),
                ]
            )
            self.assertEqual(rc, 0)

            conn = sqlite3.connect(str(news_articles_db))
            try:
                articles_count = int((conn.execute("SELECT COUNT(*) FROM articles").fetchone() or [0])[0] or 0)
                self.assertGreaterEqual(articles_count, 1)
            finally:
                conn.close()

            rc = CHUNKS.main(
                [
                    "--from-db",
                    str(news_articles_db),
                    "--to-db",
                    str(news_context_db),
                    "--lane",
                    "high_precision",
                    "--embed-backend",
                    "hash",
                ]
            )
            self.assertEqual(rc, 0)
            conn = sqlite3.connect(str(news_context_db))
            try:
                ids_1 = [row[0] for row in conn.execute("SELECT chunk_id FROM context_chunks WHERE chunk_id LIKE 'news:%' ORDER BY chunk_id")]
                self.assertTrue(ids_1)
            finally:
                conn.close()

            rc = CHUNKS.main(
                [
                    "--from-db",
                    str(news_articles_db),
                    "--to-db",
                    str(news_context_db),
                    "--lane",
                    "high_precision",
                    "--embed-backend",
                    "hash",
                ]
            )
            self.assertEqual(rc, 0)
            conn = sqlite3.connect(str(news_context_db))
            try:
                ids_2 = [row[0] for row in conn.execute("SELECT chunk_id FROM context_chunks WHERE chunk_id LIKE 'news:%' ORDER BY chunk_id")]
            finally:
                conn.close()
            self.assertEqual(ids_1, ids_2)

            # report generation should produce required artifacts for latest run.
            rc = REPORT.main(
                [
                    "--news-articles-db",
                    str(news_articles_db),
                    "--tickers-file",
                    str(tickers_file),
                    "--news-runs-root",
                    str(runs_root),
                ]
            )
            self.assertEqual(rc, 0)
            run_dirs = [path for path in runs_root.iterdir() if path.is_dir()]
            self.assertTrue(run_dirs)
            latest = sorted(run_dirs)[-1]
            required = [
                latest / "articles_per_day_by_provider.csv",
                latest / "ticker_coverage_1_7_30_days.json",
                latest / "rejections_by_reason.csv",
                latest / "duplicate_rates.json",
                latest / "top_uncovered_tickers.csv",
                latest / "failure_bucket_samples",
            ]
            for path in required:
                self.assertTrue(path.exists(), str(path))


if __name__ == "__main__":
    unittest.main()

