import importlib.util
import json
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
    def _make_alpha_intelligence_rows(self):
        return [
            SENT.ArticleIntelligenceRow(
                article_lookup_key="aaa-1",
                article_key="aaa-1",
                ticker="AAA",
                title="AAA wins contract",
                source="Reuters",
                url="https://example.com/aaa-1",
                published_at="2026-02-01T10:00:00Z",
                doc_date="2026-02-01",
                topic="contracts",
                corpus="news",
                sentiment_score=0.65,
                sentiment_confidence=0.9,
                event_family="contract_customer_demand",
                event_materiality=0.8,
                relation_type="primary_company",
                relevance_score=0.9,
                ret_1d=1.2,
                ret_3d=2.1,
                ret_5d=2.9,
                abs_ret_1d=1.2,
                price_confirmation_score=0.4,
                narrative_shock_flag=0,
                shock_severity=0.0,
            ),
            SENT.ArticleIntelligenceRow(
                article_lookup_key="aaa-2",
                article_key="aaa-2",
                ticker="AAA",
                title="AAA signs customer deal",
                source="Reuters",
                url="https://example.com/aaa-2",
                published_at="2026-02-02T10:00:00Z",
                doc_date="2026-02-02",
                topic="contracts",
                corpus="news",
                sentiment_score=0.55,
                sentiment_confidence=0.85,
                event_family="contract_customer_demand",
                event_materiality=0.75,
                relation_type="primary_company",
                relevance_score=0.88,
                ret_1d=0.8,
                ret_3d=1.6,
                ret_5d=2.2,
                abs_ret_1d=0.8,
                price_confirmation_score=0.25,
                narrative_shock_flag=0,
                shock_severity=0.0,
            ),
            SENT.ArticleIntelligenceRow(
                article_lookup_key="aaa-3",
                article_key="aaa-3",
                ticker="AAA",
                title="AAA expands pipeline",
                source="Bloomberg",
                url="https://example.com/aaa-3",
                published_at="2026-02-03T10:00:00Z",
                doc_date="2026-02-03",
                topic="contracts",
                corpus="news",
                sentiment_score=0.6,
                sentiment_confidence=0.82,
                event_family="contract_customer_demand",
                event_materiality=0.72,
                relation_type="primary_company",
                relevance_score=0.86,
                ret_1d=1.0,
                ret_3d=1.8,
                ret_5d=2.4,
                abs_ret_1d=1.0,
                price_confirmation_score=0.3,
                narrative_shock_flag=1,
                shock_severity=62.0,
            ),
            SENT.ArticleIntelligenceRow(
                article_lookup_key="aaa-4",
                article_key="aaa-4",
                ticker="AAA",
                title="AAA customer backlog rises",
                source="Reuters",
                url="https://example.com/aaa-4",
                published_at="2026-02-04T10:00:00Z",
                doc_date="2026-02-04",
                topic="contracts",
                corpus="news",
                sentiment_score=0.5,
                sentiment_confidence=0.8,
                event_family="contract_customer_demand",
                event_materiality=0.7,
                relation_type="primary_company",
                relevance_score=0.83,
                ret_1d=-0.4,
                ret_3d=0.9,
                ret_5d=1.6,
                abs_ret_1d=0.4,
                price_confirmation_score=0.15,
                narrative_shock_flag=0,
                shock_severity=0.0,
            ),
            SENT.ArticleIntelligenceRow(
                article_lookup_key="aaa-5",
                article_key="aaa-5",
                ticker="AAA",
                title="AAA renews major contract",
                source="Dow Jones",
                url="https://example.com/aaa-5",
                published_at="2026-02-05T10:00:00Z",
                doc_date="2026-02-05",
                topic="contracts",
                corpus="news",
                sentiment_score=0.58,
                sentiment_confidence=0.84,
                event_family="contract_customer_demand",
                event_materiality=0.78,
                relation_type="primary_company",
                relevance_score=0.9,
                ret_1d=1.4,
                ret_3d=2.5,
                ret_5d=3.1,
                abs_ret_1d=1.4,
                price_confirmation_score=0.45,
                narrative_shock_flag=1,
                shock_severity=71.0,
            ),
            SENT.ArticleIntelligenceRow(
                article_lookup_key="bbb-1",
                article_key="bbb-1",
                ticker="BBB",
                title="BBB lands supply agreement",
                source="Reuters",
                url="https://example.com/bbb-1",
                published_at="2026-02-06T10:00:00Z",
                doc_date="2026-02-06",
                topic="contracts",
                corpus="news",
                sentiment_score=0.42,
                sentiment_confidence=0.76,
                event_family="contract_customer_demand",
                event_materiality=0.64,
                relation_type="primary_company",
                relevance_score=0.81,
                ret_1d=0.3,
                ret_3d=1.1,
                ret_5d=1.4,
                abs_ret_1d=0.3,
                price_confirmation_score=0.1,
                narrative_shock_flag=0,
                shock_severity=0.0,
            ),
            SENT.ArticleIntelligenceRow(
                article_lookup_key="ccc-1",
                article_key="ccc-1",
                ticker="CCC",
                title="CCC wins new customer",
                source="Reuters",
                url="https://example.com/ccc-1",
                published_at="2026-02-07T10:00:00Z",
                doc_date="2026-02-07",
                topic="contracts",
                corpus="news",
                sentiment_score=0.48,
                sentiment_confidence=0.79,
                event_family="contract_customer_demand",
                event_materiality=0.66,
                relation_type="primary_company",
                relevance_score=0.8,
                ret_1d=0.6,
                ret_3d=1.3,
                ret_5d=1.9,
                abs_ret_1d=0.6,
                price_confirmation_score=0.2,
                narrative_shock_flag=0,
                shock_severity=0.0,
            ),
            SENT.ArticleIntelligenceRow(
                article_lookup_key="ddd-1",
                article_key="ddd-1",
                ticker="DDD",
                title="DDD faces legal action",
                source="Reuters",
                url="https://example.com/ddd-1",
                published_at="2026-02-08T10:00:00Z",
                doc_date="2026-02-08",
                topic="legal",
                corpus="news",
                sentiment_score=-0.72,
                sentiment_confidence=0.9,
                event_family="regulatory_legal",
                event_materiality=0.9,
                relation_type="primary_company",
                relevance_score=0.92,
                ret_1d=-1.8,
                ret_3d=-2.7,
                ret_5d=-3.3,
                abs_ret_1d=1.8,
                price_confirmation_score=0.55,
                narrative_shock_flag=1,
                shock_severity=78.0,
            ),
            SENT.ArticleIntelligenceRow(
                article_lookup_key="eee-1",
                article_key="eee-1",
                ticker="EEE",
                title="EEE receives regulatory notice",
                source="Bloomberg",
                url="https://example.com/eee-1",
                published_at="2026-02-09T10:00:00Z",
                doc_date="2026-02-09",
                topic="legal",
                corpus="news",
                sentiment_score=-0.6,
                sentiment_confidence=0.88,
                event_family="regulatory_legal",
                event_materiality=0.86,
                relation_type="primary_company",
                relevance_score=0.9,
                ret_1d=-0.9,
                ret_3d=-1.4,
                ret_5d=-1.8,
                abs_ret_1d=0.9,
                price_confirmation_score=0.4,
                narrative_shock_flag=1,
                shock_severity=67.0,
            ),
        ]

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

    def test_build_alpha_stats_and_predictions(self):
        intelligence_rows = self._make_alpha_intelligence_rows()

        global_stats, ticker_stats = SENT.build_alpha_statistics(intelligence_rows=intelligence_rows)
        predictions = SENT.build_alpha_article_predictions(
            intelligence_rows=intelligence_rows,
            global_event_stats=global_stats,
            ticker_event_stats=ticker_stats,
        )

        global_contract_3d = next(
            row
            for row in global_stats
            if row.event_family == "contract_customer_demand" and row.window_days == 3
        )
        self.assertEqual(global_contract_3d.sample_size, 7)
        self.assertAlmostEqual(global_contract_3d.shock_rate, 2.0 / 7.0, places=6)

        aaa_contract_3d = next(
            row
            for row in ticker_stats
            if row.ticker == "AAA" and row.event_family == "contract_customer_demand" and row.window_days == 3
        )
        self.assertEqual(aaa_contract_3d.sample_size, 5)

        aaa_prediction = next(
            row
            for row in predictions
            if row.article_lookup_key == "aaa-1" and row.ticker == "AAA" and row.window_days == 3
        )
        self.assertEqual(aaa_prediction.prior_source, "ticker_event")
        self.assertEqual(aaa_prediction.sample_size_used, 5)
        self.assertAlmostEqual(aaa_prediction.expected_return, aaa_contract_3d.avg_ret, places=6)

        ccc_prediction = next(
            row
            for row in predictions
            if row.article_lookup_key == "ccc-1" and row.ticker == "CCC" and row.window_days == 3
        )
        self.assertEqual(ccc_prediction.prior_source, "global_event")
        self.assertEqual(ccc_prediction.sample_size_used, 7)

        regulatory_predictions = [
            row for row in predictions if row.event_family == "regulatory_legal"
        ]
        self.assertEqual(regulatory_predictions, [])

        explanation = json.loads(aaa_prediction.prediction_explanation_json)
        self.assertEqual(explanation["event_family"], "contract_customer_demand")
        self.assertEqual(explanation["prior_source"], "ticker_event")
        self.assertEqual(explanation["sample_size_used"], 5)
        self.assertTrue(explanation["advisory_only"])

    def test_store_sqlite_writes_alpha_tables(self):
        intelligence_rows = self._make_alpha_intelligence_rows()
        global_stats, ticker_stats = SENT.build_alpha_statistics(intelligence_rows=intelligence_rows)
        predictions = SENT.build_alpha_article_predictions(
            intelligence_rows=intelligence_rows,
            global_event_stats=global_stats,
            ticker_event_stats=ticker_stats,
        )

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news_sentiment_features.sqlite"
            SENT.store_sqlite(
                db_path=db_path,
                article_rows=[],
                ticker_rows=[],
                intelligence_rows=intelligence_rows,
                cluster_rows=[],
                narrative_rows=[],
                alpha_event_stats=global_stats,
                alpha_ticker_event_stats=ticker_stats,
                alpha_predictions=predictions,
            )

            conn = sqlite3.connect(str(db_path))
            try:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                self.assertIn("news_alpha_event_stats", tables)
                self.assertIn("news_alpha_ticker_event_stats", tables)
                self.assertIn("news_alpha_article_predictions", tables)
                event_count = conn.execute("SELECT COUNT(*) FROM news_alpha_event_stats").fetchone()[0]
                ticker_count = conn.execute("SELECT COUNT(*) FROM news_alpha_ticker_event_stats").fetchone()[0]
                prediction_count = conn.execute("SELECT COUNT(*) FROM news_alpha_article_predictions").fetchone()[0]
            finally:
                conn.close()

        self.assertGreater(event_count, 0)
        self.assertGreater(ticker_count, 0)
        self.assertGreater(prediction_count, 0)


if __name__ == "__main__":
    unittest.main()
