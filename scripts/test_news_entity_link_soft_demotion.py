from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPTS_DIR))

from news_pipeline.db import NewsArticleStore  # type: ignore  # noqa: E402
from news_pipeline.models import ArticleCandidate, EntityLink  # type: ignore  # noqa: E402


class EntityLinkSoftDemotionTests(unittest.TestCase):
    def test_high_precision_chunk_build_uses_high_recall_links_when_missing_high_precision(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            store = NewsArticleStore(db_path)
            try:
                candidate = ArticleCandidate(
                    provider="eodhd",
                    provider_item_id="item1",
                    canonical_url="https://example.com/article",
                    title="Example title",
                    description="Example description",
                    body="Example body text.",
                    source_name="Example Source",
                    language="en",
                    published_at_utc="2026-02-24T00:00:00Z",
                    fetched_at_utc="2026-02-24T01:00:00Z",
                )
                upsert = store.upsert_article(candidate, lane="high_precision")

                link = EntityLink(
                    article_id=upsert.article_id,
                    ticker="BHP",
                    confidence=0.5,
                    lane="high_recall",
                    method="test_case",
                    matched_alias="BHP",
                    matched_span_start=-1,
                    matched_span_end=-1,
                    published_at_utc="2026-02-24T00:00:00Z",
                )
                store.replace_entity_links(upsert.article_id, [link])

                articles = store.get_articles_for_chunk_build(lane="high_precision")
                self.assertEqual(len(articles), 1)
                self.assertEqual(articles[0]["article_id"], upsert.article_id)
                self.assertEqual(articles[0]["linked_tickers"], ["BHP"])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()

