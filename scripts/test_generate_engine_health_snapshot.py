import datetime as dt
import importlib.util
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
MOD = load_module(ROOT / "scripts" / "generate_engine_health_snapshot.py", "generate_engine_health_snapshot")


def _init_news_db(path: Path, *, ticker_chunks: int, total_chunks: int, doc_date: str, corpus: str = "news") -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE context_chunks (
                chunk_id TEXT PRIMARY KEY,
                corpus TEXT,
                doc_type TEXT,
                doc_date TEXT,
                source TEXT,
                ticker TEXT,
                company TEXT,
                file TEXT,
                url TEXT
            )
            """
        )
        rows = []
        for idx in range(total_chunks):
            ticker = "|BHP|" if idx < ticker_chunks else ""
            rows.append(
                (
                    f"news:{idx}",
                    corpus,
                    "news_article",
                    doc_date,
                    "Reuters",
                    ticker,
                    "NEWS",
                    f"news://{idx}",
                    f"https://example.com/{idx}",
                )
            )
        conn.executemany(
            """
            INSERT INTO context_chunks(
                chunk_id, corpus, doc_type, doc_date, source, ticker, company, file, url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _init_company_db(path: Path, *, total_chunks: int, invalid_chunks: int) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE context_chunks (
                chunk_id TEXT PRIMARY KEY,
                corpus TEXT,
                company TEXT,
                bad_metadata_reason TEXT
            )
            """
        )
        rows = []
        for idx in range(total_chunks):
            invalid = idx < invalid_chunks
            rows.append(
                (
                    f"company:{idx}",
                    "company",
                    "UNKNOWN" if invalid else "BHP",
                    "invalid_company_format" if invalid else "",
                )
            )
        conn.executemany(
            "INSERT INTO context_chunks(chunk_id, corpus, company, bad_metadata_reason) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _init_core_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
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
        conn.execute(
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
        docs = []
        runs = []
        for idx in range(1, 11):
            doc_id = f"doc-{idx}"
            downloaded = "" if idx == 10 else f"sha-{idx}"
            docs.append(
                (
                    doc_id,
                    "BHP",
                    "announcement",
                    "results",
                    "2026-02-24T00:00:00Z",
                    "2026-02-24T01:00:00Z",
                    f"Doc {idx}",
                    f"/tmp/doc{idx}.pdf",
                    downloaded,
                )
            )
            if idx <= 8:
                runs.append((f"run-{idx}", doc_id, "ok", "", "{}", f"2026-02-25T0{idx}:00:00Z"))
            elif idx == 9:
                runs.append(
                    (
                        "run-9",
                        doc_id,
                        "failed",
                        "connection reset by peer",
                        "{}",
                        "2026-02-25T09:00:00Z",
                    )
                )
        conn.executemany(
            """
            INSERT INTO documents(
                document_id, ticker, doc_class, doc_subtype, published_at, ingested_at, title, pdf_path, pdf_sha256
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            docs,
        )
        conn.executemany(
            """
            INSERT INTO extraction_runs(run_id, document_id, status, error, structured_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            runs,
        )
        conn.commit()
    finally:
        conn.close()


def _healthy_gpu():
    return {
        "nvml_available": True,
        "gpu_count": 1,
        "memory_total_mb": 24576,
        "memory_used_mb": 2048,
        "driver_version": "555.10",
        "status": "healthy",
    }


def _unavailable_gpu():
    return {
        "nvml_available": False,
        "gpu_count": 0,
        "memory_total_mb": 0,
        "memory_used_mb": 0,
        "driver_version": "",
        "status": "unavailable",
    }


class _Env:
    def __init__(self, **values: str | None) -> None:
        self.values = values
        self.previous: dict[str, str | None] = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.previous[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def __exit__(self, *_exc):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class TestGenerateEngineHealthSnapshot(unittest.TestCase):
    def test_default_context_db_paths_use_production_artifact_root(self):
        with _Env(
            COCKPIT_NEWS_DB_PATH=None,
            TENN_NEWS_CONTEXT_DB=None,
            TENN_NEWS_ARTIFACT_ROOT=None,
            COCKPIT_COMPANY_DB_PATH=None,
            TENN_COMPANY_CONTEXT_DB=None,
            TENN_QUAL_CONTEXT_ARTIFACT_ROOT=None,
        ):
            args = MOD.parse_args([])

        self.assertEqual(
            Path(args.news_db_path),
            Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite"),
        )
        self.assertEqual(
            Path(args.company_db_path),
            Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite"),
        )

    def test_context_db_paths_respect_cockpit_explicit_env_priority(self):
        with _Env(
            COCKPIT_NEWS_DB_PATH="/tmp/cockpit-news.sqlite",
            TENN_NEWS_CONTEXT_DB="/tmp/tenn-news.sqlite",
            TENN_NEWS_ARTIFACT_ROOT="/tmp/news-root",
            COCKPIT_COMPANY_DB_PATH="/tmp/cockpit-company.sqlite",
            TENN_COMPANY_CONTEXT_DB="/tmp/tenn-company.sqlite",
            TENN_QUAL_CONTEXT_ARTIFACT_ROOT="/tmp/qual-root",
        ):
            args = MOD.parse_args([])

        self.assertEqual(Path(args.news_db_path), Path("/tmp/cockpit-news.sqlite"))
        self.assertEqual(Path(args.company_db_path), Path("/tmp/cockpit-company.sqlite"))

    def test_context_db_paths_respect_artifact_root_envs(self):
        with _Env(
            COCKPIT_NEWS_DB_PATH=None,
            TENN_NEWS_CONTEXT_DB=None,
            TENN_NEWS_ARTIFACT_ROOT="/tmp/news-root",
            COCKPIT_COMPANY_DB_PATH=None,
            TENN_COMPANY_CONTEXT_DB=None,
            TENN_QUAL_CONTEXT_ARTIFACT_ROOT="/tmp/qual-root",
        ):
            args = MOD.parse_args([])

        self.assertEqual(Path(args.news_db_path), Path("/tmp/news-root/news.sqlite"))
        self.assertEqual(Path(args.company_db_path), Path("/tmp/qual-root/company.sqlite"))

    def test_cli_context_db_paths_override_env_defaults(self):
        with _Env(
            COCKPIT_NEWS_DB_PATH="/tmp/cockpit-news.sqlite",
            COCKPIT_COMPANY_DB_PATH="/tmp/cockpit-company.sqlite",
        ):
            args = MOD.parse_args(
                [
                    "--news-db-path",
                    "/tmp/cli-news.sqlite",
                    "--company-db-path",
                    "/tmp/cli-company.sqlite",
                ]
            )

        self.assertEqual(Path(args.news_db_path), Path("/tmp/cli-news.sqlite"))
        self.assertEqual(Path(args.company_db_path), Path("/tmp/cli-company.sqlite"))

    def _build_snapshot(
        self,
        *,
        news_ticker_chunks: int,
        news_total_chunks: int,
        news_doc_date: str,
        company_total_chunks: int,
        company_invalid_chunks: int,
        gpu_probe,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            news_db = root / "news.sqlite"
            company_db = root / "company.sqlite"
            core_db = root / "core.sqlite"
            out_json = root / "health.json"

            _init_news_db(
                news_db,
                ticker_chunks=news_ticker_chunks,
                total_chunks=news_total_chunks,
                doc_date=news_doc_date,
            )
            _init_company_db(
                company_db,
                total_chunks=company_total_chunks,
                invalid_chunks=company_invalid_chunks,
            )
            _init_core_db(core_db)

            now_utc = dt.datetime(2026, 2, 25, 12, 0, 0, tzinfo=dt.timezone.utc)
            payload = MOD.build_health_snapshot(
                database_url=f"sqlite:///{core_db}",
                news_db_path=news_db,
                company_db_path=company_db,
                out_json=out_json,
                news_corpus="news",
                thresholds=MOD.HealthThresholds(),
                now_utc=now_utc,
                gpu_probe=gpu_probe,
            )
            return payload

    def test_healthy_scenario(self):
        payload = self._build_snapshot(
            news_ticker_chunks=8,
            news_total_chunks=10,
            news_doc_date="2026-02-25",
            company_total_chunks=50,
            company_invalid_chunks=0,
            gpu_probe=_healthy_gpu,
        )
        self.assertEqual(payload["overall_status"], "healthy")
        self.assertEqual(payload["gpu"]["status"], "healthy")
        self.assertFalse(payload["news"]["drift_flags"]["low_ticker_coverage"])
        self.assertFalse(payload["news"]["drift_flags"]["stale_news"])
        self.assertFalse(payload["company_rag"]["drift_flags"]["invalid_company_ratio_exceeded"])

    def test_low_ticker_coverage_scenario(self):
        payload = self._build_snapshot(
            news_ticker_chunks=0,
            news_total_chunks=10,
            news_doc_date="2026-02-25",
            company_total_chunks=50,
            company_invalid_chunks=0,
            gpu_probe=_healthy_gpu,
        )
        self.assertEqual(payload["overall_status"], "warning")
        self.assertTrue(payload["news"]["drift_flags"]["low_ticker_coverage"])
        self.assertFalse(payload["news"]["drift_flags"]["stale_news"])

    def test_default_news_corpus_includes_provider_specific_news_corpora(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            news_db = root / "news.sqlite"
            company_db = root / "company.sqlite"
            core_db = root / "core.sqlite"
            out_json = root / "health.json"
            _init_news_db(
                news_db,
                ticker_chunks=8,
                total_chunks=10,
                doc_date="2026-02-25",
                corpus="news_newspaper4k",
            )
            conn = sqlite3.connect(str(news_db))
            try:
                conn.executemany(
                    """
                    INSERT INTO context_chunks(
                        chunk_id, corpus, doc_type, doc_date, source, ticker, company, file, url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        ("news-extra:1", "newswire", "news_article", "2026-02-25", "Reuters", "|BHP|", "NEWS", "x1", "u1"),
                        ("news-extra:2", "newsletter", "news_article", "2026-02-25", "Reuters", "|BHP|", "NEWS", "x2", "u2"),
                        ("news-extra:3", "news-foo", "news_article", "2026-02-25", "Reuters", "|BHP|", "NEWS", "x3", "u3"),
                    ],
                )
                conn.commit()
            finally:
                conn.close()
            _init_company_db(company_db, total_chunks=50, invalid_chunks=0)
            _init_core_db(core_db)

            payload = MOD.build_health_snapshot(
                database_url=f"sqlite:///{core_db}",
                news_db_path=news_db,
                company_db_path=company_db,
                out_json=out_json,
                news_corpus="news",
                thresholds=MOD.HealthThresholds(),
                now_utc=dt.datetime(2026, 2, 25, 12, 0, 0, tzinfo=dt.timezone.utc),
                gpu_probe=_healthy_gpu,
            )

        self.assertEqual(payload["news"]["total_chunks"], 10)
        self.assertFalse(payload["news"]["drift_flags"]["low_ticker_coverage"])

    def test_explicit_non_default_news_corpus_remains_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            news_db = root / "news.sqlite"
            company_db = root / "company.sqlite"
            core_db = root / "core.sqlite"
            out_json = root / "health.json"
            _init_news_db(
                news_db,
                ticker_chunks=8,
                total_chunks=10,
                doc_date="2026-02-25",
                corpus="news_newspaper4k",
            )
            _init_company_db(company_db, total_chunks=50, invalid_chunks=0)
            _init_core_db(core_db)

            payload = MOD.build_health_snapshot(
                database_url=f"sqlite:///{core_db}",
                news_db_path=news_db,
                company_db_path=company_db,
                out_json=out_json,
                news_corpus="news_rss_v2",
                thresholds=MOD.HealthThresholds(),
                now_utc=dt.datetime(2026, 2, 25, 12, 0, 0, tzinfo=dt.timezone.utc),
                gpu_probe=_healthy_gpu,
            )

        self.assertEqual(payload["news"]["total_chunks"], 0)
        self.assertTrue(payload["news"]["drift_flags"]["low_ticker_coverage"])

    def test_missing_company_db_sets_warning_not_healthy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            news_db = root / "news.sqlite"
            company_db = root / "missing-company.sqlite"
            core_db = root / "core.sqlite"
            out_json = root / "health.json"
            _init_news_db(news_db, ticker_chunks=8, total_chunks=10, doc_date="2026-02-25")
            _init_core_db(core_db)

            payload = MOD.build_health_snapshot(
                database_url=f"sqlite:///{core_db}",
                news_db_path=news_db,
                company_db_path=company_db,
                out_json=out_json,
                news_corpus="news",
                thresholds=MOD.HealthThresholds(),
                now_utc=dt.datetime(2026, 2, 25, 12, 0, 0, tzinfo=dt.timezone.utc),
                gpu_probe=_healthy_gpu,
            )

        self.assertEqual(payload["overall_status"], "warning")
        self.assertFalse(payload["company_rag"]["db_exists"])
        self.assertTrue(payload["company_rag"]["drift_flags"]["missing_db"])
        self.assertTrue(payload["company_rag"]["drift_flags"]["zero_chunks"])

    def test_readonly_sqlite_connection_does_not_create_missing_db(self):
        with tempfile.TemporaryDirectory() as td:
            missing_db = Path(td) / "missing.sqlite"

            with self.assertRaises(sqlite3.OperationalError):
                MOD._connect_sqlite_readonly(missing_db)

            self.assertFalse(missing_db.exists())

    def test_gpu_unavailable_scenario(self):
        payload = self._build_snapshot(
            news_ticker_chunks=8,
            news_total_chunks=10,
            news_doc_date="2026-02-25",
            company_total_chunks=50,
            company_invalid_chunks=0,
            gpu_probe=_unavailable_gpu,
        )
        self.assertEqual(payload["overall_status"], "warning")
        self.assertFalse(payload["gpu"]["nvml_available"])
        self.assertEqual(payload["gpu"]["status"], "unavailable")

    def test_invalid_company_ratio_exceeded_scenario(self):
        payload = self._build_snapshot(
            news_ticker_chunks=8,
            news_total_chunks=10,
            news_doc_date="2026-02-25",
            company_total_chunks=30,
            company_invalid_chunks=25,
            gpu_probe=_healthy_gpu,
        )
        self.assertEqual(payload["overall_status"], "degraded")
        self.assertTrue(payload["company_rag"]["drift_flags"]["invalid_company_ratio_exceeded"])
        self.assertGreater(payload["company_rag"]["invalid_company_count"], 20)


if __name__ == "__main__":
    unittest.main()
