import importlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
DB = importlib.import_module("news_pipeline.db")
MODELS = importlib.import_module("news_pipeline.models")


class StoreTests(unittest.TestCase):
    def _candidate(
        self,
        *,
        provider: str,
        provider_item_id: str,
        url: str,
        title: str,
        description: str,
        fetched_at_utc: str = "2026-02-25T00:00:00Z",
    ):
        return MODELS.ArticleCandidate(
            provider=provider,
            provider_item_id=provider_item_id,
            canonical_url=url,
            title=title,
            description=description,
            body="Body text",
            source_name="source",
            language="en",
            published_at_utc="2026-02-24T09:30:00Z",
            fetched_at_utc=fetched_at_utc,
            provider_published_at_raw="2026-02-24T09:30:00Z",
            raw_payload={"id": provider_item_id},
        )

    def test_article_upsert_and_dedupe(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            store = DB.NewsArticleStore(db_path)
            try:
                run_id = store.start_provider_run("gdelt", "daily", params={})
                self.assertTrue(run_id)
                a1 = self._candidate(
                    provider="gdelt",
                    provider_item_id="a1",
                    url="https://example.com/article-1",
                    title="BHP update",
                    description="Guidance up",
                )
                up1 = store.upsert_article(a1, lane="high_precision")
                self.assertTrue(up1.inserted)

                a2 = self._candidate(
                    provider="eodhd",
                    provider_item_id="a2",
                    url="https://example.com/article-1",
                    title="BHP update",
                    description="Guidance up again",
                )
                up2 = store.upsert_article(a2, lane="high_precision")
                self.assertFalse(up2.inserted)
                self.assertEqual(up2.dedupe_reason, "dedupe_url")

                a3 = self._candidate(
                    provider="gdelt",
                    provider_item_id="a3",
                    url="",
                    title="CSL earnings",
                    description="Revenue up 10%",
                )
                up3 = store.upsert_article(a3, lane="high_recall")
                self.assertTrue(up3.inserted)
                a4 = self._candidate(
                    provider="rss",
                    provider_item_id="a4",
                    url="",
                    title="CSL earnings",
                    description="Revenue up 10%",
                )
                up4 = store.upsert_article(a4, lane="high_recall")
                self.assertFalse(up4.inserted)
                self.assertEqual(up4.dedupe_reason, "dedupe_exact")

                # Equal rank/length: newer fetch should become canonical best snapshot.
                a5 = self._candidate(
                    provider="gdelt",
                    provider_item_id="a5",
                    url="https://example.com/fetch-tie",
                    title="Fetch tie story",
                    description="Same body",
                    fetched_at_utc="2026-02-25T00:00:00Z",
                )
                up5 = store.upsert_article(a5, lane="high_precision")
                self.assertTrue(up5.inserted)
                a6 = self._candidate(
                    provider="gdelt",
                    provider_item_id="a6",
                    url="https://example.com/fetch-tie",
                    title="Fetch tie story",
                    description="Same body",
                    fetched_at_utc="2026-02-25T01:00:00Z",
                )
                up6 = store.upsert_article(a6, lane="high_precision")
                self.assertFalse(up6.inserted)
                row = store.conn.execute("SELECT provider_item_id FROM articles WHERE article_id = ?", (up5.article_id,)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(str(row[0] or ""), "a6")

                store.record_window(
                    run_id=run_id,
                    provider="gdelt",
                    window_start_utc="2026-02-24T00:00:00Z",
                    window_end_utc="2026-02-24T23:59:59Z",
                    status="completed",
                    fetched=10,
                    inserted=2,
                    deduped=1,
                    rejected=0,
                    errors=0,
                )
                completed = store.completed_windows(run_id, "gdelt")
                self.assertIn(("2026-02-24T00:00:00Z", "2026-02-24T23:59:59Z"), completed)
            finally:
                store.close()

    def test_duplicate_article_id_is_deduped_even_when_secondary_hashes_drift(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            store = DB.NewsArticleStore(db_path)
            try:
                candidate = self._candidate(
                    provider="newspaper4k",
                    provider_item_id="n4k-1",
                    url="https://example.com/legacy-id",
                    title="Legacy id story",
                    description="Original story",
                )
                article_id = "art_" + DB.sha1_hex(candidate.canonical_url)[:24]
                store.conn.execute(
                    """
                    INSERT INTO articles(
                        article_id, canonical_url, url_hash, title, description, body,
                        source_name, language, published_at_utc, fetched_at_utc,
                        provider_best, provider_item_id, content_hash_exact,
                        content_hash_near, quality_score, lane
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article_id,
                        "",
                        "legacy-url-hash",
                        "Legacy id story",
                        "Legacy row with drifted hashes",
                        "Legacy body",
                        "source",
                        "en",
                        "2026-02-24T09:30:00Z",
                        "2026-02-24T09:30:00Z",
                        "newspaper4k",
                        "legacy",
                        "legacy-exact",
                        "legacy-near",
                        1.0,
                        "high_precision",
                    ),
                )
                store.conn.commit()

                result = store.upsert_article(candidate, lane="high_precision")

                self.assertFalse(result.inserted)
                self.assertEqual(result.article_id, article_id)
                self.assertEqual(result.dedupe_reason, "dedupe_article_id")
                count = int((store.conn.execute("SELECT COUNT(*) FROM articles").fetchone() or [0])[0] or 0)
                self.assertEqual(count, 1)
            finally:
                store.close()

    def test_finalize_stale_running_runs_marks_old_rows(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            store = DB.NewsArticleStore(db_path)
            try:
                stale_run = store.start_provider_run("gdelt", "backfill", params={})
                fresh_run = store.start_provider_run("eodhd", "daily", params={})
                store.conn.execute(
                    "UPDATE provider_runs SET started_at = ? WHERE run_id = ?",
                    ("2026-01-01T00:00:00Z", stale_run),
                )
                store.conn.execute(
                    "UPDATE provider_runs SET started_at = ? WHERE run_id = ?",
                    ("2099-01-01T00:00:00Z", fresh_run),
                )
                store.conn.commit()

                updated = store.finalize_stale_running_runs(older_than_hours=2, to_status="failed")
                self.assertEqual(updated, 1)

                row_stale = store.run_row(stale_run)
                row_fresh = store.run_row(fresh_run)
                self.assertEqual(str(row_stale.get("status") or ""), "failed")
                self.assertTrue(str(row_stale.get("finished_at") or "").strip())
                self.assertEqual(str(row_fresh.get("status") or ""), "running")
            finally:
                store.close()

    def test_finalize_stale_running_runs_rejects_invalid_status(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_articles.sqlite"
            store = DB.NewsArticleStore(db_path)
            try:
                with self.assertRaises(ValueError):
                    store.finalize_stale_running_runs(older_than_hours=2, to_status="success")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
