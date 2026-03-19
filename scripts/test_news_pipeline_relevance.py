from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPTS_DIR))

from news_pipeline.db import NewsArticleStore  # type: ignore  # noqa: E402
from news_pipeline.models import ArticleCandidate, EntityLink  # type: ignore  # noqa: E402
from news_pipeline.relevance import choose_primary_ticker, infer_ticker_relevance_from_text, score_article_relevance  # type: ignore  # noqa: E402


class NewsPipelineRelevanceTests(unittest.TestCase):
    def test_choose_primary_ticker_returns_empty_for_weak_multi_ticker_rows(self) -> None:
        rows = infer_ticker_relevance_from_text(
            title="Global markets update",
            body="Central banks and tariffs remain the focus for investors this week.",
            tickers=["COMPANY", "IS", "WITH"],
        )
        self.assertEqual(choose_primary_ticker(rows, ["COMPANY", "IS", "WITH"]), "")

    def test_high_precision_chunk_build_falls_back_to_high_recall_relevance_and_selects_primary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            store = NewsArticleStore(db_path)
            try:
                title = "ASX:BHP lifts guidance after strong quarter"
                body = "CBA analysts reacted to BHP's stronger quarter while BHP maintained output guidance."
                candidate = ArticleCandidate(
                    provider="eodhd",
                    provider_item_id="item1",
                    canonical_url="https://example.com/article",
                    title=title,
                    description="",
                    body=body,
                    source_name="Example Source",
                    language="en",
                    published_at_utc="2026-02-24T00:00:00Z",
                    fetched_at_utc="2026-02-24T01:00:00Z",
                )
                upsert = store.upsert_article(candidate, lane="high_precision")
                body_offset = len(title) + 2
                cba_pos = body.index("CBA")
                bhp_body_pos = body.index("BHP")
                links = [
                    EntityLink(
                        article_id=upsert.article_id,
                        ticker="BHP",
                        confidence=0.85,
                        lane="high_recall",
                        method="explicit_symbol",
                        matched_alias="ASX:BHP",
                        matched_span_start=0,
                        matched_span_end=7,
                        published_at_utc="2026-02-24T00:00:00Z",
                    ),
                    EntityLink(
                        article_id=upsert.article_id,
                        ticker="BHP",
                        confidence=0.45,
                        lane="high_recall",
                        method="ticker_token",
                        matched_alias="BHP",
                        matched_span_start=body_offset + bhp_body_pos,
                        matched_span_end=body_offset + bhp_body_pos + 3,
                        published_at_utc="2026-02-24T00:00:00Z",
                    ),
                    EntityLink(
                        article_id=upsert.article_id,
                        ticker="CBA",
                        confidence=0.45,
                        lane="high_recall",
                        method="ticker_token",
                        matched_alias="CBA",
                        matched_span_start=body_offset + cba_pos,
                        matched_span_end=body_offset + cba_pos + 3,
                        published_at_utc="2026-02-24T00:00:00Z",
                    ),
                ]
                store.replace_entity_links(upsert.article_id, links)
                store.replace_article_relevance(
                    upsert.article_id,
                    score_article_relevance(
                        article_id=upsert.article_id,
                        title=title,
                        description="",
                        body=body,
                        links=links,
                    ),
                )

                articles = store.get_articles_for_chunk_build(lane="high_precision")
                self.assertEqual(len(articles), 1)
                article = articles[0]
                self.assertEqual(article["linked_tickers"], ["BHP", "CBA"])
                self.assertEqual(article["primary_ticker"], "BHP")
                self.assertGreater(float(article["primary_relevance_score"] or 0.0), 0.5)
                relevance_map = json.loads(str(article["ticker_relevance_json"] or "{}"))
                self.assertIn("BHP", relevance_map)
                self.assertIn("CBA", relevance_map)
                self.assertGreater(float(relevance_map["BHP"]["score"]), float(relevance_map["CBA"]["score"]))
                self.assertEqual(str(relevance_map["BHP"]["label"]), "primary_company")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
