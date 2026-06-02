#!/usr/bin/env python3
import importlib.util
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if "app.core.config" not in sys.modules:
    cfg_stub = types.ModuleType("app.core.config")
    cfg_stub.PROJECT_ROOT = REPO_ROOT
    cfg_stub.settings = SimpleNamespace(
        database_url="sqlite:////tmp/fe_local.db",
        celery_broker_url="memory://",
        celery_result_backend="cache+memory://",
        task_mode="sync",
        enable_importance_classification=False,
        importance_output_root=None,
        importance_materialize_output=False,
        importance_include_pdf_text=False,
        importance_link_mode="symlink",
        importance_sort_source_docs=False,
        enable_embeddings=True,
        enable_qdrant=True,
    )
    sys.modules["app.core.config"] = cfg_stub

if "app.services.pipeline" not in sys.modules:
    pipe_stub = types.ModuleType("app.services.pipeline")
    pipe_stub.EXTRACTION_FAILURE_TAXONOMY = (
        "ocr_or_text_unavailable",
        "parser_timeout",
        "llm_invalid_json",
        "provider_network",
        "corrupted_pdf",
        "unknown",
    )

    def _classify(error_text, structured_json=None):  # noqa: ANN001, ANN201
        text = str(error_text or "").lower()
        if "json" in text:
            return "llm_invalid_json"
        if "connection" in text:
            return "provider_network"
        if "timeout" in text:
            return "parser_timeout"
        return "unknown"

    pipe_stub.classify_extraction_failure = _classify  # type: ignore[attr-defined]
    pipe_stub.discover_and_insert_documents = lambda *args, **kwargs: {}  # type: ignore[attr-defined]
    pipe_stub.download_pdf_for_document = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    pipe_stub.process_document = lambda document_id: {"document_id": document_id, "extraction_status": "ok"}  # type: ignore[attr-defined]
    pipe_stub.backfill_ticker_sync = lambda *args, **kwargs: {}  # type: ignore[attr-defined]
    sys.modules["app.services.pipeline"] = pipe_stub


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = load_module(REPO_ROOT / "scripts" / "audit_extraction_backlog.py", "audit_extraction_backlog")
RUN = load_module(REPO_ROOT / "scripts" / "run_extraction_backlog.py", "run_extraction_backlog")
CLASSIFY = load_module(REPO_ROOT / "scripts" / "classify_extraction_failures.py", "classify_extraction_failures")


def _build_test_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE documents (
                document_id TEXT PRIMARY KEY,
                ticker TEXT,
                doc_class TEXT,
                doc_subtype TEXT,
                published_at TEXT,
                ingested_at TEXT,
                title TEXT,
                pdf_path TEXT,
                pdf_sha256 TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE extraction_runs (
                run_id TEXT PRIMARY KEY,
                document_id TEXT,
                status TEXT,
                error TEXT,
                structured_json TEXT,
                created_at TEXT
            )
            """
        )
        cur.executemany(
            """
            INSERT INTO documents(
                document_id, ticker, doc_class, doc_subtype, published_at, ingested_at, title, pdf_path, pdf_sha256
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "doc-1",
                    "BHP",
                    "announcement",
                    "results",
                    "2026-02-20T00:00:00Z",
                    "2026-02-20T01:00:00Z",
                    "Doc 1",
                    "/tmp/doc1.pdf",
                    "sha_doc1",
                ),
                (
                    "doc-2",
                    "CBA",
                    "announcement",
                    "update",
                    "2026-02-19T00:00:00Z",
                    "2026-02-19T01:00:00Z",
                    "Doc 2",
                    "/tmp/doc2.pdf",
                    "sha_doc2",
                ),
                (
                    "doc-3",
                    "NAB",
                    "announcement",
                    "update",
                    "2026-02-18T00:00:00Z",
                    "2026-02-18T01:00:00Z",
                    "Doc 3",
                    "/tmp/doc3.pdf",
                    "sha_doc3",
                ),
            ],
        )
        cur.executemany(
            """
            INSERT INTO extraction_runs(run_id, document_id, status, error, structured_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "run-21",
                    "doc-2",
                    "failed",
                    "connection reset by peer",
                    "{}",
                    "2026-02-20T10:00:00Z",
                ),
                (
                    "run-31",
                    "doc-3",
                    "ok",
                    "",
                    "{}",
                    "2026-02-20T11:00:00Z",
                ),
            ],
        )
        conn.commit()
    finally:
        conn.close()


class ExtractionBacklogToolingTests(unittest.TestCase):
    def test_audit_extraction_backlog_counts(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "fe_local.db"
            _build_test_db(db_path)
            out_path = Path(td) / "audit.json"
            args = SimpleNamespace(
                database_url=f"sqlite:///{db_path}",
                sample_limit=20,
                out_json=str(out_path),
            )
            with mock.patch.object(AUDIT, "parse_args", return_value=args):
                rc = AUDIT.main()
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["totals"]["downloaded_not_extracted"], 1)
            self.assertEqual(payload["totals"]["latest_failed"], 1)
            self.assertEqual(payload["breakdown"]["downloaded_not_extracted_by_ticker"]["BHP"], 1)
            self.assertEqual(payload["breakdown"]["latest_failed_by_ticker"]["CBA"], 1)

    def test_classify_extraction_failures_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "fe_local.db"
            _build_test_db(db_path)
            # Add one additional failed run with malformed JSON style failure.
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    INSERT INTO extraction_runs(run_id, document_id, status, error, structured_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "run-11",
                        "doc-1",
                        "failed",
                        "JSONDecodeError: Expecting value",
                        "{}",
                        "2026-02-20T12:00:00Z",
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            out_path = Path(td) / "taxonomy.json"
            args = SimpleNamespace(
                database_url=f"sqlite:///{db_path}",
                all_runs=False,
                limit=1000,
                sample_per_class=5,
                ticker=None,
                out_json=str(out_path),
            )
            with mock.patch.object(CLASSIFY, "parse_args", return_value=args):
                rc = CLASSIFY.main()
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["counts_by_category"]["provider_network"], 1)
            self.assertEqual(payload["counts_by_category"]["llm_invalid_json"], 1)

    def test_run_backlog_respects_retry_and_stops_on_consecutive_failures(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "fe_local.db"
            _build_test_db(db_path)
            out_path = Path(td) / "run_report.json"

            args = SimpleNamespace(
                database_url=f"sqlite:///{db_path}",
                ticker=None,
                limit=100,
                concurrency=1,
                max_retries=2,
                retry_delay_seconds=0.01,
                max_consecutive_failures=2,
                with_embeddings=False,
                dry_run=False,
                health_json=str(Path(td) / "missing_health.json"),
                allow_warning=False,
                report_json=str(out_path),
            )
            # Backlog docs are doc-1 (no runs) and doc-2 (latest failed). doc-3 latest ok is excluded.
            side_effect = [
                Exception("connection reset by peer"),  # doc-1 attempt 1
                {"extraction_status": "ok"},  # doc-1 attempt 2
                {"extraction_status": "failed"},  # doc-2 final status
            ]
            with (
                mock.patch.object(RUN, "parse_args", return_value=args),
                mock.patch.object(RUN, "process_document", side_effect=side_effect) as process_mock,
                mock.patch.object(RUN.time, "sleep") as sleep_mock,
            ):
                rc = RUN.main()
            self.assertEqual(rc, 1)
            self.assertGreaterEqual(process_mock.call_count, 3)
            self.assertGreaterEqual(sleep_mock.call_count, 1)

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["totals"]["backlog_selected"], 2)
            self.assertEqual(payload["totals"]["processed_ok"], 1)
            self.assertEqual(payload["totals"]["failed"], 1)
            self.assertFalse(payload["totals"]["stopped_early"])

            # Run again with all failures to trigger early stop.
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    """
                    INSERT INTO documents(
                        document_id, ticker, doc_class, doc_subtype, published_at, ingested_at, title, pdf_path, pdf_sha256
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "doc-4",
                        "ANZ",
                        "announcement",
                        "update",
                        "2026-02-17T00:00:00Z",
                        "2026-02-17T01:00:00Z",
                        "Doc 4",
                        "/tmp/doc4.pdf",
                        "sha_doc4",
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            out_path2 = Path(td) / "run_report_stop.json"
            args.report_json = str(out_path2)
            args.max_retries = 1
            with (
                mock.patch.object(RUN, "parse_args", return_value=args),
                mock.patch.object(RUN, "process_document", return_value={"extraction_status": "failed"}),
                mock.patch.object(RUN.time, "sleep"),
            ):
                rc2 = RUN.main()
            self.assertEqual(rc2, 1)
            payload2 = json.loads(out_path2.read_text(encoding="utf-8"))
            self.assertTrue(payload2["totals"]["stopped_early"])
            self.assertGreater(payload2["totals"]["remaining_unprocessed"], 0)


if __name__ == "__main__":
    unittest.main()
