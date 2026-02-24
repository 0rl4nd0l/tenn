import importlib.util
import json
import sys
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


if __name__ == "__main__":
    unittest.main()
