import importlib.util
import json
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

NEWS = load_module(str(SCRIPTS / "build_news_context_db.py"), "build_news_context_db")
CTX = load_module(str(SCRIPTS / "build_qualitative_context_db.py"), "build_qualitative_context_db")


class TestBuildNewsContextDb(unittest.TestCase):
    def test_normalize_news_row_maps_fields(self):
        row = {
            "date": "2026-02-20T10:00:00Z",
            "text": "Apple gains after earnings beat.\n\nApple stock rose as revenue topped estimates.",
            "extra_fields": json.dumps(
                {
                    "source": "Reuters",
                    "category": "earnings",
                    "url": "https://example.com/apple",
                    "stocks": ["AAPL"],
                }
            ),
        }
        rec, reason = NEWS.normalize_news_row(row, min_text_chars=30, keep_non_english=False)
        self.assertEqual(reason, "ok")
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec.source, "Reuters")
        self.assertEqual(rec.doc_date, "2026-02-20")
        self.assertEqual(rec.topic, "earnings")
        self.assertEqual(rec.url, "https://example.com/apple")
        self.assertTrue(CTX.ticker_blob_contains(rec.ticker, "AAPL"))

    def test_normalize_news_row_filters_ticker_allowlist_without_dropping(self):
        row = {
            "date": "2026-02-20T10:00:00Z",
            "title": "AGL and TSLA move after guidance",
            "text": "NYSE:AGL rose while ASX:TSLA is unrelated and AGL remains in scope for AU names.",
            "extra_fields": {"source": "Reuters", "stocks": ["AGL", "TSLA"]},
        }
        rec, reason = NEWS.normalize_news_row(
            row,
            min_text_chars=20,
            keep_non_english=False,
            ticker_allowlist={"AGL"},
            drop_ticker_nonmatching_rows=False,
        )
        self.assertEqual(reason, "ok")
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertTrue(CTX.ticker_blob_contains(rec.ticker, "AGL"))
        self.assertFalse(CTX.ticker_blob_contains(rec.ticker, "TSLA"))

    def test_normalize_news_row_drops_when_allowlist_enabled_and_no_match(self):
        row = {
            "date": "2026-02-20T10:00:00Z",
            "title": "TSLA guidance update",
            "text": "NASDAQ:TSLA updated guidance with significant revisions.",
            "extra_fields": {"source": "Reuters", "stocks": ["TSLA"]},
        }
        rec, reason = NEWS.normalize_news_row(
            row,
            min_text_chars=20,
            keep_non_english=False,
            ticker_allowlist={"AGL"},
            drop_ticker_nonmatching_rows=True,
        )
        self.assertIsNone(rec)
        self.assertEqual(reason, "ticker_not_allowlisted")

    def test_load_ticker_allowlist_from_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "allowlist.txt"
            path.write_text("AGL\nTSLA\n# comment\n", encoding="utf-8")
            allow = NEWS.load_ticker_allowlist(path)
            self.assertIn("AGL", allow)
            self.assertIn("TSLA", allow)

    def test_normalize_records_deduplicates_url_and_near_duplicates(self):
        rows = [
            {
                "id": "one",
                "date": "2026-02-20",
                "text": "Market update title\n\nStocks rallied on lower yields and better guidance outlook.",
                "extra_fields": {"source": "CNBC", "url": "https://example.com/one", "stocks": ["MSFT"]},
            },
            {
                "id": "two",
                "date": "2026-02-20",
                "text": "Market update title\n\nStocks rallied on lower yields and better guidance outlook.",
                "extra_fields": {"source": "CNBC", "url": "https://example.com/one", "stocks": ["MSFT"]},
            },
            {
                "id": "three",
                "date": "2026-02-20",
                "text": "Market update title\n\nStocks rallied on lower yields and better guidance outlook today.",
                "extra_fields": {"source": "CNBC", "url": "https://example.com/three", "stocks": ["MSFT"]},
            },
        ]
        kept, stats = NEWS.normalize_records(rows=rows, min_text_chars=20, keep_non_english=False, max_rows=0)
        self.assertEqual(len(kept), 1)
        self.assertEqual(stats["dropped_duplicate_url"], 1)
        self.assertEqual(stats["dropped_duplicate_near"], 1)

    def test_build_chunk_records_assigns_news_metadata(self):
        rows = [
            NEWS.NormalizedNewsRecord(
                record_id="abc",
                source="Reuters",
                published_at="2026-02-20T10:00:00Z",
                doc_date="2026-02-20",
                title="Tesla updates delivery outlook",
                body="Tesla announced updated delivery guidance and margin expectations." * 10,
                ticker=CTX.serialize_tickers(["TSLA"]),
                topic="guidance",
                url="https://example.com/tesla",
            )
        ]
        chunks = NEWS.build_chunk_records(rows, corpus="news", doc_type="news_article", max_chars=220, overlap_words=20)
        self.assertTrue(chunks)
        self.assertTrue(all(ch.corpus == "news" for ch in chunks))
        self.assertTrue(all(ch.doc_type == "news_article" for ch in chunks))
        self.assertTrue(all(ch.source == "Reuters" for ch in chunks))
        self.assertTrue(all(CTX.ticker_blob_contains(ch.ticker, "TSLA") for ch in chunks))

    def test_infer_tickers_detects_asx_prefix_and_ax_suffix(self):
        blob = NEWS.infer_tickers(
            title="ASX:AGL jumps after update",
            body="BHP.AX also moved on revised guidance for FY26.",
            existing=[],
            allowlist={"AGL", "BHP"},
        )
        self.assertTrue(CTX.ticker_blob_contains(blob, "AGL"))
        self.assertTrue(CTX.ticker_blob_contains(blob, "BHP"))

    def test_main_writes_manifest_on_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / "news.jsonl"
            out_path = tmp / "news.sqlite"
            manifest_path = tmp / "manifest.json"
            rows = [
                {
                    "id": "n1",
                    "date": "2026-02-20T10:00:00Z",
                    "title": "ASX:AGL updates guidance",
                    "text": "ASX:AGL provided updated guidance and revenue outlook for FY26." * 6,
                    "extra_fields": {"source": "Reuters", "url": "https://example.com/1", "stocks": ["AGL"]},
                },
                {
                    "id": "n2",
                    "date": "2026-02-21T10:00:00Z",
                    "title": "BHP.AX earnings beat",
                    "text": "BHP.AX beat estimates with stronger production and cash generation." * 6,
                    "extra_fields": {"source": "CNBC", "url": "https://example.com/2", "stocks": ["BHP"]},
                },
            ]
            with input_path.open("w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row) + "\n")

            argv = [
                "build_news_context_db.py",
                "--input-path",
                str(input_path),
                "--db",
                "sqlite",
                "--out",
                str(out_path),
                "--embed-backend",
                "hash",
                "--hash-dim",
                "64",
                "--row-batch-size",
                "1",
                "--min-text-chars",
                "20",
                "--manifest-json",
                str(manifest_path),
                "--manifest-write-every",
                "1",
                "--health-json",
                str(tmp / "missing_health.json"),
                "--research-only-ack",
            ]
            with mock.patch.object(sys, "argv", argv):
                rc = NEWS.main()
            self.assertEqual(rc, 0)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest.get("status"), "success")
            stats = manifest.get("stats", {})
            self.assertEqual(int(stats.get("input_rows", 0)), 2)
            self.assertEqual(int(stats.get("kept_rows", 0)), 2)
            self.assertGreaterEqual(int(stats.get("flush_batches", 0)), 2)
            self.assertGreaterEqual(int(stats.get("unique_tickers", 0)), 2)

    def test_main_writes_failed_manifest_with_live_counters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / "news.jsonl"
            out_path = tmp / "news.sqlite"
            manifest_path = tmp / "manifest_failed.json"
            row = {
                "id": "n1",
                "date": "2026-02-20T10:00:00Z",
                "title": "ASX:AGL updates guidance",
                "text": "ASX:AGL provided updated guidance and revenue outlook for FY26." * 6,
                "extra_fields": {"source": "Reuters", "url": "https://example.com/1", "stocks": ["AGL"]},
            }
            input_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

            argv = [
                "build_news_context_db.py",
                "--input-path",
                str(input_path),
                "--db",
                "sqlite",
                "--out",
                str(out_path),
                "--embed-backend",
                "hash",
                "--hash-dim",
                "64",
                "--row-batch-size",
                "1",
                "--min-text-chars",
                "20",
                "--manifest-json",
                str(manifest_path),
                "--manifest-write-every",
                "1",
                "--health-json",
                str(tmp / "missing_health.json"),
                "--research-only-ack",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(NEWS, "flush_batch", side_effect=RuntimeError("synthetic_flush_failure")),
            ):
                with self.assertRaises(RuntimeError):
                    NEWS.main()

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest.get("status"), "failed")
            self.assertIn("synthetic_flush_failure", str(manifest.get("error", "")))
            stats = manifest.get("stats", {})
            self.assertGreaterEqual(int(stats.get("input_rows", 0)), 1)
            self.assertGreaterEqual(int(stats.get("kept_rows", 0)), 1)


if __name__ == "__main__":
    unittest.main()
