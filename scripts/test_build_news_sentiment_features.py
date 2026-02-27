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
SENT = load_module(str(ROOT / "scripts" / "build_news_sentiment_features.py"), "build_news_sentiment_features")


class TestBuildNewsSentimentFeatures(unittest.TestCase):
    def test_parse_windows(self):
        self.assertEqual(SENT.parse_windows("90,30,7,30"), [7, 30, 90])
        with self.assertRaises(ValueError):
            SENT.parse_windows("0,-1")

    def test_lexical_scoring_positive_and_negative(self):
        bullish = SENT.NewsArticle(
            article_key="a1",
            title="Company raises guidance after beating estimates",
            source="Reuters",
            url="https://example.com/a1",
            published_at="2026-02-24T10:00:00Z",
            doc_date="2026-02-24",
            ticker_blob="|AAA|",
            topic="earnings",
            text="The company beat estimates and reported strong demand with margin expansion.",
        )
        bearish = SENT.NewsArticle(
            article_key="a2",
            title="Company cuts guidance after downgrade",
            source="Reuters",
            url="https://example.com/a2",
            published_at="2026-02-24T10:00:00Z",
            doc_date="2026-02-24",
            ticker_blob="|AAA|",
            topic="earnings",
            text="Management cut guidance with margin pressure and rising default risk.",
        )
        up = SENT.score_article_lexical(bullish)
        down = SENT.score_article_lexical(bearish)
        self.assertGreater(up.sentiment_score, 0.2)
        self.assertLess(down.sentiment_score, -0.2)
        self.assertGreater(up.signal_hits, 0)
        self.assertGreater(down.signal_hits, 0)

    def test_aggregate_prefers_recent_articles(self):
        recent = SENT.ArticleSentiment(
            article_key="r1",
            title="",
            source="Reuters",
            url="",
            published_at="2026-02-24T08:00:00Z",
            doc_date="2026-02-24",
            ticker_blob="|AAA|",
            topic="",
            sentiment_score=0.8,
            confidence=0.8,
            positive_hits=3,
            negative_hits=0,
            signal_hits=3,
            scorer="lexical",
        )
        older = SENT.ArticleSentiment(
            article_key="r2",
            title="",
            source="Reuters",
            url="",
            published_at="2026-02-10T08:00:00Z",
            doc_date="2026-02-10",
            ticker_blob="|AAA|",
            topic="",
            sentiment_score=-0.7,
            confidence=0.8,
            positive_hits=0,
            negative_hits=3,
            signal_hits=3,
            scorer="lexical",
        )
        rows = SENT.aggregate_ticker_windows(
            article_scores=[recent, older],
            as_of_date=SENT.dt.date(2026, 2, 24),
            windows=[7, 30],
            half_life_days=7.0,
            ticker_filter="",
        )
        seven = [row for row in rows if row.ticker == "AAA" and row.window_days == 7][0]
        thirty = [row for row in rows if row.ticker == "AAA" and row.window_days == 30][0]
        self.assertEqual(seven.article_count, 1)
        self.assertGreater(seven.weighted_sentiment, 0.6)
        self.assertEqual(thirty.article_count, 2)
        self.assertGreater(thirty.weighted_sentiment, 0.0)
        self.assertLess(thirty.weighted_sentiment, seven.weighted_sentiment)

    def test_load_news_articles_from_sqlite_merges_chunks(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            conn = sqlite3.connect(str(db_path))
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE context_chunks (
                        chunk_id TEXT PRIMARY KEY,
                        corpus TEXT,
                        doc_type TEXT,
                        title TEXT,
                        source TEXT,
                        url TEXT,
                        published_at TEXT,
                        doc_date TEXT,
                        ticker TEXT,
                        topic TEXT,
                        company TEXT,
                        text TEXT
                    )
                    """
                )
                cur.executemany(
                    """
                    INSERT INTO context_chunks(
                        chunk_id, corpus, doc_type, title, source, url, published_at, doc_date, ticker, topic, company, text
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            "n1:0",
                            "news",
                            "news_article",
                            "AAA raises guidance",
                            "Reuters",
                            "https://example.com/aaa",
                            "2026-02-24T10:00:00Z",
                            "2026-02-24",
                            "|AAA|",
                            "earnings",
                            "AAA",
                            "AAA raises guidance after beating estimates.",
                        ),
                        (
                            "n1:1",
                            "news",
                            "news_article",
                            "AAA raises guidance",
                            "Reuters",
                            "https://example.com/aaa",
                            "2026-02-24T10:00:00Z",
                            "2026-02-24",
                            "|AAA|",
                            "earnings",
                            "AAA",
                            "Management highlighted strong demand and margin expansion.",
                        ),
                        (
                            "n2:0",
                            "news",
                            "news_article",
                            "BBB cuts guidance",
                            "Bloomberg",
                            "https://example.com/bbb",
                            "2026-02-23T09:00:00Z",
                            "2026-02-23",
                            "|BBB|",
                            "guidance",
                            "BBB",
                            "BBB cut guidance due to weak demand and margin pressure.",
                        ),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

            rows = SENT.load_news_articles_from_sqlite(
                db_path=db_path,
                doc_type_filter="news_article",
                min_text_chars=20,
                max_article_chars=500,
                max_articles=0,
            )
            self.assertEqual(len(rows), 2)
            merged = [row for row in rows if row.url == "https://example.com/aaa"][0]
            self.assertIn("beating estimates", merged.text)
            self.assertIn("margin expansion", merged.text)

    def test_infer_ticker_blob_from_company_and_text(self):
        blob = SENT.infer_ticker_blob(
            title="ASX:XYZ receives permit and expands project",
            text="Company said $XYZ remains on track. Peer MCHP.O is bidding.",
            existing_blob="",
            company_fallback="NEWS",
        )
        parsed = SENT.parse_ticker_blob(blob)
        self.assertIn("MCHP", parsed)
        self.assertIn("XYZ", parsed)


if __name__ == "__main__":
    unittest.main()
