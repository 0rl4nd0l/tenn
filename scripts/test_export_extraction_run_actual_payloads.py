import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.export_extraction_run_actual_payloads import build_export


class ExportExtractionRunActualPayloadsTest(unittest.TestCase):
    def _db(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        tmp = tempfile.TemporaryDirectory()
        db_path = Path(tmp.name) / "runs.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE extraction_runs (
                    run_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    extractor_version TEXT,
                    model_name TEXT,
                    prompt_hash TEXT,
                    status TEXT NOT NULL,
                    confidence_overall REAL,
                    error TEXT,
                    structured_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
        return tmp, db_path

    def _insert(
        self,
        db_path: Path,
        *,
        run_id: str = "11111111-1111-1111-1111-111111111111",
        document_id: str = "22222222-2222-2222-2222-222222222222",
        status: str = "ok",
        structured_json: dict | str | None = None,
        created_at: str = "2026-06-01 00:00:00",
    ) -> None:
        if structured_json is None:
            structured_json = {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 100.0, "net_debt": None},
                "provenance": {"revenue": "income_statement:page_1:Revenue"},
                "row_refs": {"revenue": "Revenue", "net_debt": "unknown"},
            }
        raw_json = (
            structured_json
            if isinstance(structured_json, str)
            else json.dumps(structured_json)
        )
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO extraction_runs (
                    run_id, document_id, extractor_version, model_name,
                    prompt_hash, status, confidence_overall, error,
                    structured_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    document_id,
                    "docling_multipass_v1",
                    "qwen2.5-14b-instruct",
                    "prompt-hash",
                    status,
                    0.91,
                    None,
                    raw_json,
                    created_at,
                ),
            )

    def test_exports_run_payload_keyed_by_document_id(self) -> None:
        tmp, db_path = self._db()
        self.addCleanup(tmp.cleanup)
        self._insert(db_path)

        actuals, summary = build_export(
            db_path=db_path,
            run_ids=["11111111-1111-1111-1111-111111111111"],
            document_ids=[],
            allowed_statuses=["ok"],
            key="document_id",
        )

        document_id = "22222222-2222-2222-2222-222222222222"
        payload = actuals[document_id]
        self.assertEqual(payload["period_type"], "H")
        self.assertEqual(payload["metrics"]["revenue"], 100.0)
        self.assertIn("revenue", payload["evidence"])
        self.assertNotIn("net_debt", payload["evidence"])
        self.assertFalse(payload["extraction_run_provenance"]["gold_label"])
        self.assertFalse(summary["failed_closed"])
        self.assertEqual(summary["exported_payload_count"], 1)
        self.assertFalse(summary["boundaries"]["mutated_database"])

    def test_rejects_failed_status_by_default(self) -> None:
        tmp, db_path = self._db()
        self.addCleanup(tmp.cleanup)
        self._insert(db_path, status="failed")

        actuals, summary = build_export(
            db_path=db_path,
            run_ids=["11111111-1111-1111-1111-111111111111"],
            document_ids=[],
            allowed_statuses=["ok", "ok_low_confidence"],
            key="document_id",
        )

        self.assertEqual(actuals, {})
        self.assertTrue(summary["failed_closed"])
        self.assertIn("not in allowed statuses", summary["errors"][0]["error"])

    def test_rejects_payload_without_metrics_object(self) -> None:
        tmp, db_path = self._db()
        self.addCleanup(tmp.cleanup)
        self._insert(
            db_path,
            structured_json={
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
            },
        )

        actuals, summary = build_export(
            db_path=db_path,
            run_ids=["11111111-1111-1111-1111-111111111111"],
            document_ids=[],
            allowed_statuses=["ok"],
            key="document_id",
        )

        self.assertEqual(actuals, {})
        self.assertTrue(summary["failed_closed"])
        self.assertEqual(
            summary["errors"][0]["error"],
            "structured_json.metrics must be a JSON object",
        )

    def test_document_selector_uses_latest_allowed_status_run(self) -> None:
        tmp, db_path = self._db()
        self.addCleanup(tmp.cleanup)
        document_id = "22222222-2222-2222-2222-222222222222"
        self._insert(
            db_path,
            run_id="11111111-1111-1111-1111-111111111111",
            document_id=document_id,
            structured_json={
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 10.0},
            },
            created_at="2026-06-01 00:00:00",
        )
        self._insert(
            db_path,
            run_id="33333333-3333-3333-3333-333333333333",
            document_id=document_id,
            structured_json={
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "millions",
                "metrics": {"revenue": 20.0},
            },
            created_at="2026-06-01 01:00:00",
        )

        actuals, summary = build_export(
            db_path=db_path,
            run_ids=[],
            document_ids=[document_id],
            allowed_statuses=["ok"],
            key="document_id",
        )

        self.assertEqual(actuals[document_id]["metrics"]["revenue"], 20.0)
        self.assertEqual(
            summary["selected_runs"][0]["run_id"],
            "33333333-3333-3333-3333-333333333333",
        )

    def test_missing_run_fails_closed(self) -> None:
        tmp, db_path = self._db()
        self.addCleanup(tmp.cleanup)

        actuals, summary = build_export(
            db_path=db_path,
            run_ids=["99999999-9999-9999-9999-999999999999"],
            document_ids=[],
            allowed_statuses=["ok"],
            key="document_id",
        )

        self.assertEqual(actuals, {})
        self.assertTrue(summary["failed_closed"])
        self.assertEqual(summary["errors"][0]["error"], "run not found")


if __name__ == "__main__":
    unittest.main()
