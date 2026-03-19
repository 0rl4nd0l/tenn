"""Unit tests for news context drift detection (baseline vs actual)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS.parent
for p in (str(SCRIPTS), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_qualitative_context_db as ctx  # noqa: E402


def _run_drift(db_path: Path, baseline_path: Path, extra_args: list | None = None) -> int:
    from detect_news_context_drift import main
    args = ["--db", str(db_path), "--baseline", str(baseline_path)]
    if extra_args:
        args.extend(extra_args)
    return main(args)


def _create_minimal_news_db(path: Path, corpus: str = "news", n_chunks: int = 5) -> None:
    """Create a minimal context_chunks DB for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(n_chunks):
        records.append(
            ctx.ChunkRecord(
                chunk_id=f"{corpus}:doc{i}:0:abc",
                company="NEWS",
                file="https://example.com/1",
                section="fulltext_context",
                text="chunk text",
                corpus=corpus,
                doc_type="news_article",
                doc_date="2026-01-01",
                source="test",
                ticker="",
                topic="",
                url="https://example.com/1",
                title="Title",
                published_at="2026-01-01T00:00:00Z",
            )
        )
    ctx.store_sqlite(records, [[0.0] * 64] * n_chunks, path)


class TestDriftMissingCorpus(unittest.TestCase):
    """Missing baseline corpus triggers drift by default."""

    def test_missing_corpus_fails_drift(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            _create_minimal_news_db(db_path, corpus="news", n_chunks=3)

            baseline_path = Path(td) / "baseline.json"
            baseline_path.write_text(
                json.dumps({
                    "version": 2,
                    "total_chunks": 3,
                    "by_corpus": {"news": 3},
                    "corpus_hash": "x",
                    "chunk_id_sample_hash": "",
                    "doc_id_sample_hash": "",
                    "top_sources_hash": "",
                }, indent=2),
                encoding="utf-8",
            )

            # Replace DB with one that has different corpus (simulate missing "news")
            db_path.unlink()
            _create_minimal_news_db(db_path, corpus="news_other", n_chunks=3)

            # Run drift with default (fail on missing corpus)
            exit_code = _run_drift(db_path, baseline_path)
            self.assertNotEqual(exit_code, 0, "drift should fail when baseline corpus is missing")

    def test_same_corpus_and_count_no_drift(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            _create_minimal_news_db(db_path, corpus="news", n_chunks=3)

            baseline_path = Path(td) / "baseline.json"
            baseline_path.write_text(
                json.dumps({
                    "version": 2,
                    "total_chunks": 3,
                    "by_corpus": {"news": 3},
                    "corpus_hash": "x",
                    "chunk_id_sample_hash": "",
                    "doc_id_sample_hash": "",
                    "top_sources_hash": "",
                }, indent=2),
                encoding="utf-8",
            )

            exit_code = _run_drift(db_path, baseline_path)
            self.assertEqual(exit_code, 0)

    def test_no_fail_on_missing_corpus_allows_missing_baseline_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            _create_minimal_news_db(db_path, corpus="news_other", n_chunks=3)

            baseline_path = Path(td) / "baseline.json"
            baseline_path.write_text(
                json.dumps({
                    "version": 2,
                    "total_chunks": 3,
                    "by_corpus": {"news": 3},
                    "corpus_hash": "x",
                    "chunk_id_sample_hash": "",
                    "doc_id_sample_hash": "",
                    "top_sources_hash": "",
                }, indent=2),
                encoding="utf-8",
            )

            exit_code = _run_drift(db_path, baseline_path, ["--no-fail-on-missing-corpus"])
            self.assertEqual(exit_code, 0)


class TestDriftTolerance(unittest.TestCase):
    """Tolerance: corpus can drop up to tolerance-pct before drift."""

    def test_small_drop_within_tolerance_passes(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            _create_minimal_news_db(db_path, corpus="news", n_chunks=8)  # 8 vs 10 = 20% drop

            baseline_path = Path(td) / "baseline.json"
            baseline_path.write_text(
                json.dumps({
                    "version": 2,
                    "total_chunks": 10,
                    "by_corpus": {"news": 10},
                    "corpus_hash": "x",
                    "chunk_id_sample_hash": "",
                    "doc_id_sample_hash": "",
                    "top_sources_hash": "",
                }, indent=2),
                encoding="utf-8",
            )

            # 20% drop with default 25% tolerance should pass
            exit_code = _run_drift(db_path, baseline_path, ["--tolerance-pct", "25"])
            self.assertEqual(exit_code, 0)

    def test_large_drop_beyond_tolerance_fails(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            _create_minimal_news_db(db_path, corpus="news", n_chunks=5)  # 5 vs 10 = 50% drop

            baseline_path = Path(td) / "baseline.json"
            baseline_path.write_text(
                json.dumps({
                    "version": 2,
                    "total_chunks": 10,
                    "by_corpus": {"news": 10},
                    "corpus_hash": "x",
                    "chunk_id_sample_hash": "",
                    "doc_id_sample_hash": "",
                    "top_sources_hash": "",
                }, indent=2),
                encoding="utf-8",
            )

            exit_code = _run_drift(db_path, baseline_path, ["--tolerance-pct", "25"])
            self.assertNotEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
