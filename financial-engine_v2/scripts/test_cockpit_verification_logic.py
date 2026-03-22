#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.verification import run_verification  # noqa: E402


class _MockDbReader:
    """Minimal stub for the db_reader interface used by run_verification."""

    def __init__(
        self,
        docs: list[dict] | None = None,
        extraction_failures: list[dict] | None = None,
        low_confidence: list[dict] | None = None,
    ) -> None:
        self._docs = docs or []
        self._extraction_failures = extraction_failures or []
        self._low_confidence = low_confidence or []

    def get_docs(self, ticker: str | None = None, limit: int = 500) -> list[dict]:
        return list(self._docs)

    def get_extraction_failures(self, limit: int = 100) -> list[dict]:
        return list(self._extraction_failures)

    def get_low_confidence_financials(self, limit: int = 100) -> list[dict]:
        return list(self._low_confidence)


class VerificationLogicTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Blank ticker — no docs queried, all counts zero
    # ------------------------------------------------------------------
    def test_blank_ticker_returns_zero_counts(self) -> None:
        db = _MockDbReader(
            docs=[{"pdf_sha256": "abc123", "pdf_path": "/some/path.pdf"}],
        )
        result = run_verification(db, ticker=None)
        checks = result["checks"]
        self.assertEqual(checks["missing_pdf_files"], 0)
        self.assertEqual(checks["blocked_documents"], 0)
        self.assertEqual(checks["pending_downloads"], 0)
        # ticker should be None / falsy
        self.assertIsNone(result["ticker"])
        # remediation should be empty (no pending/blocked for blank ticker)
        # extraction_failures and low_confidence still come from db (not ticker-scoped)
        # but our mock returns empty lists → no remediation from those either
        self.assertEqual(result["remediation"], [])

    # ------------------------------------------------------------------
    # 2. Blocked document — sha256 starts with "blocked_"
    # ------------------------------------------------------------------
    def test_blocked_document_counted_and_remediation_mentions_recover(self) -> None:
        db = _MockDbReader(
            docs=[{"pdf_sha256": "blocked_deadbeef", "pdf_path": "/docs/blocked.pdf"}],
        )
        result = run_verification(db, ticker="BHP")
        self.assertEqual(result["checks"]["blocked_documents"], 1)
        self.assertEqual(result["checks"]["pending_downloads"], 0)
        self.assertEqual(result["checks"]["missing_pdf_files"], 0)
        remediation_text = " ".join(result["remediation"])
        self.assertIn("recover", remediation_text.lower())

    # ------------------------------------------------------------------
    # 3. Pending download — empty / None pdf_sha256
    # ------------------------------------------------------------------
    def test_pending_download_empty_sha256(self) -> None:
        db = _MockDbReader(
            docs=[{"pdf_sha256": "", "pdf_path": "/docs/pending.pdf"}],
        )
        result = run_verification(db, ticker="CBA")
        self.assertEqual(result["checks"]["pending_downloads"], 1)
        self.assertEqual(result["checks"]["blocked_documents"], 0)
        remediation_text = " ".join(result["remediation"])
        self.assertIn("resume_pending", remediation_text)

    def test_pending_download_none_sha256(self) -> None:
        db = _MockDbReader(
            docs=[{"pdf_sha256": None, "pdf_path": "/docs/pending2.pdf"}],
        )
        result = run_verification(db, ticker="NAB")
        self.assertEqual(result["checks"]["pending_downloads"], 1)

    # ------------------------------------------------------------------
    # 4. Missing PDF file — sha256 present but path does not exist on disk
    # ------------------------------------------------------------------
    def test_missing_pdf_file_nonexistent_path(self) -> None:
        db = _MockDbReader(
            docs=[{
                "pdf_sha256": "realsha256abc",
                "pdf_path": "/nonexistent/path/does_not_exist_abc123.pdf",
            }],
        )
        result = run_verification(db, ticker="WBC")
        self.assertEqual(result["checks"]["missing_pdf_files"], 1)
        # A missing file should appear in samples
        self.assertEqual(len(result["samples"]["missing_pdf_files"]), 1)

    # ------------------------------------------------------------------
    # 5. All clear — no issues → empty remediation
    # ------------------------------------------------------------------
    def test_all_clear_no_remediation(self) -> None:
        # Create a real temp file so the path existence check passes
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = f.name
        try:
            db = _MockDbReader(
                docs=[{"pdf_sha256": "cleansha256", "pdf_path": pdf_path}],
            )
            result = run_verification(db, ticker="ANZ")
            self.assertEqual(result["checks"]["missing_pdf_files"], 0)
            self.assertEqual(result["checks"]["blocked_documents"], 0)
            self.assertEqual(result["checks"]["pending_downloads"], 0)
            self.assertEqual(result["checks"]["extraction_failures"], 0)
            self.assertEqual(result["checks"]["low_confidence_financials"], 0)
            self.assertEqual(result["remediation"], [])
        finally:
            os.unlink(pdf_path)

    # ------------------------------------------------------------------
    # 6. Return structure shape
    # ------------------------------------------------------------------
    def test_return_structure_has_expected_keys(self) -> None:
        db = _MockDbReader()
        result = run_verification(db, ticker="MQG")
        self.assertIn("ticker", result)
        self.assertIn("checks", result)
        self.assertIn("samples", result)
        self.assertIn("remediation", result)
        for key in ("missing_pdf_files", "blocked_documents", "pending_downloads",
                    "extraction_failures", "low_confidence_financials"):
            self.assertIn(key, result["checks"])
            self.assertIn(key, result["samples"])


if __name__ == "__main__":
    unittest.main()
