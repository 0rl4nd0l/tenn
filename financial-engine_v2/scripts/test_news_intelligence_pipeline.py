#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.models.base import Base  # noqa: E402
from app.models.documents import Document  # noqa: E402
import app.services.news_intelligence as ni  # noqa: E402


class NewsIntelligencePipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = Path(self._tmpdir.name) / "news_intelligence.sqlite"
        engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.session = self.Session()
        self.addCleanup(self.session.close)

        base_ts = datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc)
        rows = [
            Document(
                document_id=uuid.uuid4(),
                ticker="BHP",
                exchange="ASX",
                doc_class="quarterly",
                doc_subtype="other",
                title="BHP announces production growth",
                source_url="https://www.asx.com.au/asx/v2/statistics/displayAnnouncement.do?idsId=03000001",
                pdf_path=str(Path(self._tmpdir.name) / "bhp_1.pdf"),
                pdf_sha256="",
                published_at=base_ts,
                ingested_at=base_ts,
            ),
            Document(
                document_id=uuid.uuid4(),
                ticker="BHP",
                exchange="ASX",
                doc_class="quarterly",
                doc_subtype="other",
                title="BHP announces production growth update",
                source_url="https://www.asx.com.au/asx/v2/statistics/displayAnnouncement.do?idsId=03000002",
                pdf_path=str(Path(self._tmpdir.name) / "bhp_2.pdf"),
                pdf_sha256="",
                published_at=base_ts + timedelta(hours=2),
                ingested_at=base_ts + timedelta(hours=2),
            ),
            Document(
                document_id=uuid.uuid4(),
                ticker="BHP",
                exchange="ASX",
                doc_class="quarterly",
                doc_subtype="other",
                title="BHP warns of outage risk",
                source_url="https://www.asx.com.au/asx/v2/statistics/displayAnnouncement.do?idsId=03000003",
                pdf_path=str(Path(self._tmpdir.name) / "bhp_3.pdf"),
                pdf_sha256="",
                published_at=base_ts + timedelta(days=1),
                ingested_at=base_ts + timedelta(days=1),
            ),
            Document(
                document_id=uuid.uuid4(),
                ticker="RIO",
                exchange="ASX",
                doc_class="quarterly",
                doc_subtype="other",
                title="RIO production growth",
                source_url="https://www.asx.com.au/asx/v2/statistics/displayAnnouncement.do?idsId=03000004",
                pdf_path=str(Path(self._tmpdir.name) / "rio_1.pdf"),
                pdf_sha256="",
                published_at=base_ts + timedelta(days=1),
                ingested_at=base_ts + timedelta(days=1),
            ),
        ]
        self.session.add_all(rows)
        self.session.commit()

    def test_builds_deterministic_snapshot_with_dedup_and_sentiment(self):
        with mock.patch.object(ni.settings, "enable_embeddings", False), mock.patch.object(
            ni.settings, "enable_qdrant", False
        ):
            result = ni.build_news_intelligence_for_ticker(self.session, "BHP", run_mode="backfill")

        self.assertEqual(result["articles_processed"], 3)
        self.assertEqual(result["unresolved_mappings"], 0)
        self.assertGreaterEqual(result["duplicates_detected"], 1)
        self.assertGreaterEqual(result["narrative_count"], 1)

        company_news = ni.get_company_news(self.session, "BHP", window="30d", limit=10)
        self.assertEqual(len(company_news["items"]), 3)
        self.assertTrue(all(item["canonical_story_id"] for item in company_news["items"]))
        self.assertTrue(all(item["mapping_confidence"] == 1.0 for item in company_news["items"]))

        sentiment = ni.get_company_sentiment(self.session, "BHP", window="30d")
        self.assertIn(sentiment["trend_direction"], {"improving", "deteriorating", "flat"})
        self.assertEqual(sentiment["method_version"], ni.SENTIMENT_METHOD_VERSION)

        narratives = ni.get_company_narratives(self.session, "BHP", window="30d", limit=5)
        self.assertGreaterEqual(len(narratives["items"]), 1)

        snapshot_one = ni.get_company_news_snapshot(self.session, "BHP")
        snapshot_two = ni.get_company_news_snapshot(self.session, "BHP")
        self.assertEqual(snapshot_one, snapshot_two)
        self.assertEqual(snapshot_one["ticker"], "BHP")
        self.assertTrue(snapshot_one["latest_headlines"])
        self.assertTrue(snapshot_one["supporting_article_ids"])

    def test_semantic_search_reports_data_missing_when_vector_stack_disabled(self):
        with mock.patch.object(ni.settings, "enable_embeddings", False), mock.patch.object(
            ni.settings, "enable_qdrant", False
        ):
            payload = ni.semantic_news_search(self.session, query="BHP production growth", filters={"ticker": "BHP"})
        self.assertEqual(payload.get("status"), ni.DATA_MISSING)


if __name__ == "__main__":
    unittest.main()
