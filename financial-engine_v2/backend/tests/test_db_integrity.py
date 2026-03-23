"""
test_db_integrity.py — structural and data integrity regression guards.

Tests in this file:
  - PROMPT_HASH is a real hash (not the hardcoded "v1" literal)
  - PROMPT_HASH is deterministic across imports
  - ExtractionRun uses PROMPT_HASH at construction sites (code inspection)
  - Upserted financial rows have a real (non-placeholder) source_document_id
  - No placeholder UUIDs survive the upsert path

All tests are pure unit/structural tests — no network, no real DB, no LLM.
"""
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.asx_financials import ASXPeriodicFinancial
from app.models.extractions import ExtractionRun
from app.services.multipass_extraction import PROMPT_HASH, EXTRACTOR_VERSION
from app.services.pipeline import _upsert_financial_rows


# ---------------------------------------------------------------------------
# PROMPT_HASH integrity
# ---------------------------------------------------------------------------

class TestPromptHash:
    def test_prompt_hash_is_hex_string(self):
        """PROMPT_HASH must be a hex string, not the legacy literal 'v1'."""
        assert PROMPT_HASH != "v1", (
            "PROMPT_HASH is still the hardcoded literal 'v1'. "
            "It must be a sha256 hexdigest of the extraction prompt templates."
        )
        assert re.fullmatch(r"[0-9a-f]+", PROMPT_HASH), (
            f"PROMPT_HASH must contain only hex characters, got: {PROMPT_HASH!r}"
        )

    def test_prompt_hash_length(self):
        """PROMPT_HASH is a 16-char hex prefix of sha256."""
        assert len(PROMPT_HASH) == 16, (
            f"Expected 16-char hex prefix, got length {len(PROMPT_HASH)}: {PROMPT_HASH!r}"
        )

    def test_prompt_hash_deterministic(self):
        """Importing PROMPT_HASH twice must yield the same value."""
        from app.services.multipass_extraction import PROMPT_HASH as ph2
        assert PROMPT_HASH == ph2

    def test_extractor_version_non_empty(self):
        assert EXTRACTOR_VERSION and len(EXTRACTOR_VERSION) > 0


# ---------------------------------------------------------------------------
# Code inspection: prompt_hash "v1" literal must not appear in pipeline code
# ---------------------------------------------------------------------------

PIPELINE_FILES = [
    Path(__file__).resolve().parent.parent / "app" / "services" / "pipeline.py",
]

WORKER_FILES = [
    Path(__file__).resolve().parent.parent.parent.parent
    / "worker" / "app" / "tasks.py",
]


class TestPromptHashInPipeline:
    def test_pipeline_does_not_use_hardcoded_v1(self):
        """pipeline.py must not pass prompt_hash='v1' to ExtractionRun."""
        for path in PIPELINE_FILES:
            if not path.exists():
                pytest.skip(f"{path} not found")
            source = path.read_text()
            assert 'prompt_hash="v1"' not in source, (
                f"{path.name}: hardcoded prompt_hash='v1' found. "
                "Must use PROMPT_HASH from multipass_extraction."
            )
            assert "prompt_hash='v1'" not in source

    def test_pipeline_imports_prompt_hash(self):
        """pipeline.py must import PROMPT_HASH from multipass_extraction."""
        for path in PIPELINE_FILES:
            if not path.exists():
                pytest.skip(f"{path} not found")
            source = path.read_text()
            assert "PROMPT_HASH" in source, (
                f"{path.name}: PROMPT_HASH not imported. "
                "ExtractionRun will receive a stale prompt_hash."
            )


# ---------------------------------------------------------------------------
# Source document ID — no placeholder UUIDs in upserted rows
# ---------------------------------------------------------------------------

_PLACEHOLDER_UUID_PREFIX = "00000000-0000-0000-0000-"


class TestNoPlaceholderSourceDocumentId:
    """
    The audit found 3 NAB financial records with source_document_id =
    '00000000-0000-0000-0000-000000000001/002/003' — fabricated UUIDs with no
    corresponding document row. These must not be produced by the pipeline.

    This test verifies that _upsert_financial_rows stores the actual document_id
    from the Document object, not a placeholder.
    """

    def _make_session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        return Session()

    def _minimal_payload(self):
        return {
            "period_type": "A",
            "period_end": "2024-09-30",
            "confidence_metrics": 0.85,
            "metrics": {
                "revenue": 22_600_000_000.0,
                "ebit": 8_400_000_000.0,
                "np_attributable": 7_500_000_000.0,
                "operating_cf": 9_300_000_000.0,
                "investing_cf": None,
                "financing_cf": None,
                "capex": -800_000_000.0,
                "cash_end": None,
                "net_debt": 10_900_000_000.0,
                "shares_outstanding": None,
            },
            "risk_summary": None,
            "risk_bullets": None,
            "guidance_summary": None,
            "material_changes": None,
            "confidence_narrative": 0.7,
        }

    def test_upserted_row_uses_real_document_id(self):
        """source_document_id on upserted row must match the document's document_id."""
        session = self._make_session()
        real_doc_id = uuid.uuid4()
        doc = SimpleNamespace(ticker="NAB", document_id=real_doc_id)

        try:
            _upsert_financial_rows(session, doc, self._minimal_payload())
            row = session.query(ASXPeriodicFinancial).filter_by(ticker="NAB").first()
            assert row is not None
            assert row.source_document_id == real_doc_id, (
                f"source_document_id should be {real_doc_id}, got {row.source_document_id}"
            )
        finally:
            session.close()

    def test_upserted_row_does_not_use_placeholder_uuid(self):
        """source_document_id must never be a placeholder UUID starting with 00000000-0000-."""
        session = self._make_session()
        real_doc_id = uuid.uuid4()
        doc = SimpleNamespace(ticker="NAB", document_id=real_doc_id)

        try:
            _upsert_financial_rows(session, doc, self._minimal_payload())
            row = session.query(ASXPeriodicFinancial).filter_by(ticker="NAB").first()
            assert row is not None
            stored_id = str(row.source_document_id)
            assert not stored_id.startswith(_PLACEHOLDER_UUID_PREFIX), (
                f"source_document_id is a placeholder UUID: {stored_id}. "
                "This indicates manual test data injection, not a pipeline extraction."
            )
        finally:
            session.close()

    def test_upsert_preserves_document_id_across_updates(self):
        """source_document_id must survive an upsert update (second call same key)."""
        session = self._make_session()
        real_doc_id = uuid.uuid4()
        doc = SimpleNamespace(ticker="NAB", document_id=real_doc_id)
        payload = self._minimal_payload()

        try:
            _upsert_financial_rows(session, doc, payload)
            # Second upsert with updated revenue
            payload["metrics"]["revenue"] = 23_000_000_000.0
            _upsert_financial_rows(session, doc, payload)

            rows = session.query(ASXPeriodicFinancial).filter_by(ticker="NAB").all()
            assert len(rows) == 1, "Upsert must not create duplicates"
            assert rows[0].source_document_id == real_doc_id
        finally:
            session.close()
