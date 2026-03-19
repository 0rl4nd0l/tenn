import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from news_pipeline.db import NewsArticleStore  # noqa: E402
from news_pipeline.entity_linker import EntityLinker  # noqa: E402
from news_pipeline.ingest import run_provider_backfill, run_provider_daily, run_provider_probe  # noqa: E402


class _InterruptProvider:
    name = "interrupt_provider"

    def fetch_window(self, *, window_start_utc, window_end_utc, tickers):
        raise KeyboardInterrupt("stop")

    def parse_item(self, item, fetched_at_utc):
        raise AssertionError("parse_item should not be called")


def _build_linker(tmp: Path) -> EntityLinker:
    tickers_file = tmp / "tickers.txt"
    tickers_file.write_text("BHP\n", encoding="utf-8")
    identity_map = tmp / "identity_map.json"
    identity_map.write_text("{}", encoding="utf-8")
    return EntityLinker(ticker_universe_path=tickers_file, identity_map_path=identity_map)


class IngestFinalizationTests(unittest.TestCase):
    def test_backfill_marks_run_failed_on_keyboard_interrupt(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            store = NewsArticleStore(tmp / "news_articles.sqlite")
            try:
                linker = _build_linker(tmp)
                with self.assertRaises(KeyboardInterrupt):
                    run_provider_backfill(
                        store=store,
                        linker=linker,
                        provider=_InterruptProvider(),
                        lane="high_recall",
                        tickers=["BHP"],
                        from_day="2026-02-24",
                        to_day="2026-02-24",
                        resume=False,
                        run_id="run_backfill_interrupt",
                    )
                row = store.run_row("run_backfill_interrupt")
                self.assertEqual(row.get("status"), "failed")
                self.assertTrue(str(row.get("finished_at") or "").strip())
            finally:
                store.close()

    def test_daily_marks_run_failed_on_keyboard_interrupt(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            store = NewsArticleStore(tmp / "news_articles.sqlite")
            try:
                linker = _build_linker(tmp)
                with self.assertRaises(KeyboardInterrupt):
                    run_provider_daily(
                        store=store,
                        linker=linker,
                        provider=_InterruptProvider(),
                        lane="high_precision",
                        tickers=["BHP"],
                        since_hours=24,
                        run_id="run_daily_interrupt",
                    )
                row = store.run_row("run_daily_interrupt")
                self.assertEqual(row.get("status"), "failed")
                self.assertTrue(str(row.get("finished_at") or "").strip())
            finally:
                store.close()

    def test_probe_marks_run_failed_on_keyboard_interrupt(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            store = NewsArticleStore(tmp / "news_articles.sqlite")
            try:
                linker = _build_linker(tmp)
                with self.assertRaises(KeyboardInterrupt):
                    run_provider_probe(
                        store=store,
                        linker=linker,
                        provider=_InterruptProvider(),
                        lane="high_precision",
                        tickers=["BHP"],
                        window_days=7,
                        run_id="run_probe_interrupt",
                    )
                row = store.run_row("run_probe_interrupt")
                self.assertEqual(row.get("status"), "failed")
                self.assertTrue(str(row.get("finished_at") or "").strip())
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
