import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from news_pipeline.db import NewsArticleStore  # noqa: E402
from news_pipeline.ingest import run_provider_daily  # noqa: E402
from news_pipeline.models import ArticleCandidate  # noqa: E402
from news_pipeline.providers.base import ParseResult, ProviderClient  # noqa: E402


class NullLinker:
    def link_article(self, **_kwargs: object) -> list[object]:
        return []


class CandidateProvider(ProviderClient):
    name = "testprovider"

    def _row_to_candidate(self, item: Dict[str, Any], fetched_at_utc: str) -> ArticleCandidate:
        item_id = str(item["id"])
        return ArticleCandidate(
            provider=self.name,
            provider_item_id=item_id,
            canonical_url=f"https://example.com/{item_id}",
            title=str(item["title"]),
            description=str(item.get("description") or "ASX market update"),
            body=str(item.get("body") or "ASX:BHP market update with enough context."),
            source_name="Example Finance",
            language="en",
            published_at_utc=str(item.get("published_at") or "2026-05-07T01:00:00Z"),
            fetched_at_utc=fetched_at_utc,
            provider_published_at_raw=str(item.get("published_at") or "2026-05-07T01:00:00Z"),
            raw_payload=item,
        )

    def parse_item(self, item: Dict[str, Any], fetched_at_utc: str) -> ParseResult:
        return ParseResult(candidate=self._row_to_candidate(item, fetched_at_utc))


class InterruptingBatchProvider(CandidateProvider):
    def fetch_window_batches(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> Iterable[List[Dict[str, Any]]]:
        yield [{"id": "early", "title": "Early BHP update"}]
        raise RuntimeError("late source failed")

    def fetch_window(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> List[Dict[str, Any]]:
        raise AssertionError("streaming provider should not use fetch_window")


class TerminatingBatchProvider(CandidateProvider):
    def fetch_window_batches(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> Iterable[List[Dict[str, Any]]]:
        yield [{"id": "before-termination", "title": "BHP update before termination"}]
        raise SystemExit("terminated")

    def fetch_window(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> List[Dict[str, Any]]:
        raise AssertionError("streaming provider should not use fetch_window")


class LegacyListProvider(CandidateProvider):
    def fetch_window(
        self,
        *,
        window_start_utc: str,
        window_end_utc: str,
        tickers: Sequence[str],
    ) -> List[Dict[str, Any]]:
        return [
            {"id": "one", "title": "First BHP update"},
            {"id": "two", "title": "Second BHP update"},
        ]


class NewsPipelineIngestResilienceTests(unittest.TestCase):
    def _run_provider(self, provider: ProviderClient) -> tuple[Path, str]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "news_articles.sqlite"
        store = NewsArticleStore(db_path)
        self.addCleanup(store.close)
        run_id, _failures = run_provider_daily(
            store=store,
            linker=NullLinker(),  # type: ignore[arg-type]
            provider=provider,
            lane="high_precision",
            tickers=["BHP"],
            since_hours=24,
            run_id=f"run_{provider.__class__.__name__}",
        )
        return db_path, run_id

    def test_streaming_provider_commits_early_batch_before_later_source_error(self):
        db_path, run_id = self._run_provider(InterruptingBatchProvider())

        conn = sqlite3.connect(str(db_path))
        try:
            run = conn.execute(
                "SELECT status, fetched, inserted, deduped, rejected, errors FROM provider_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            self.assertEqual(run, ("partial_failed", 1, 1, 0, 0, 1))
            article_count = int((conn.execute("SELECT COUNT(*) FROM articles").fetchone() or [0])[0] or 0)
            version_count = int((conn.execute("SELECT COUNT(*) FROM article_versions").fetchone() or [0])[0] or 0)
            self.assertEqual(article_count, 1)
            self.assertEqual(version_count, 1)
            window = conn.execute(
                "SELECT status, fetched, inserted, errors FROM provider_run_windows WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            self.assertEqual(window, ("failed", 1, 1, 1))
        finally:
            conn.close()

    def test_legacy_list_provider_keeps_aggregate_counters_once(self):
        db_path, run_id = self._run_provider(LegacyListProvider())

        conn = sqlite3.connect(str(db_path))
        try:
            run = conn.execute(
                "SELECT status, fetched, inserted, deduped, rejected, errors FROM provider_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            self.assertEqual(run, ("success", 2, 2, 0, 0, 0))
            window = conn.execute(
                "SELECT status, fetched, inserted, deduped, rejected, errors FROM provider_run_windows WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            self.assertEqual(window, ("completed", 2, 2, 0, 0, 0))
        finally:
            conn.close()

    def test_base_exception_marks_run_failed_after_committed_batch(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "news_articles.sqlite"
        store = NewsArticleStore(db_path)
        self.addCleanup(store.close)

        with self.assertRaises(SystemExit):
            run_provider_daily(
                store=store,
                linker=NullLinker(),  # type: ignore[arg-type]
                provider=TerminatingBatchProvider(),
                lane="high_precision",
                tickers=["BHP"],
                since_hours=24,
                run_id="run_terminated",
            )

        conn = sqlite3.connect(str(db_path))
        try:
            run = conn.execute(
                "SELECT status, fetched, inserted, deduped, rejected, errors FROM provider_runs WHERE run_id = ?",
                ("run_terminated",),
            ).fetchone()
            self.assertEqual(run, ("failed", 1, 1, 0, 0, 0))
            article_count = int((conn.execute("SELECT COUNT(*) FROM articles").fetchone() or [0])[0] or 0)
            self.assertEqual(article_count, 1)
            window = conn.execute(
                "SELECT status, fetched, inserted, errors FROM provider_run_windows WHERE run_id = ?",
                ("run_terminated",),
            ).fetchone()
            self.assertEqual(window, ("failed", 1, 1, 0))
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
