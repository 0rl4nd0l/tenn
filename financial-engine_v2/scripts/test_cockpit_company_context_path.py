#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.config import RuntimeFlags, apply_runtime_flags  # noqa: E402
from cockpit.integrations import qual_context_bootstrap as bootstrap  # noqa: E402


class _Env:
    def __init__(self, **values: str | None) -> None:
        self.values = values
        self.previous: dict[str, str | None] = {}

    def __enter__(self) -> None:
        for key, value in self.values.items():
            self.previous[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def __exit__(self, *_exc: object) -> None:
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _flags() -> RuntimeFlags:
    return RuntimeFlags(
        config_path="config/cockpit.yaml",
        profile="default",
        read_only=True,
        no_web=True,
    )


def _base_config() -> dict:
    return {
        "llm": {"ollama_url": "http://localhost:11434", "model": "llama3"},
        "db": {},
        "backend": {},
        "web": {"enabled_default": True},
        "rag": {
            "enabled": True,
            "qualitative_context": {
                "db_path": "reports/qual_context/company.sqlite",
            },
        },
    }


def _touch(path: Path, mtime: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("placeholder\n", encoding="utf-8")
    os.utime(path, (mtime, mtime))


class CockpitCompanyContextPathTests(unittest.TestCase):
    def test_cockpit_company_db_path_has_highest_env_priority(self):
        with _Env(
            COCKPIT_COMPANY_DB_PATH="/tmp/cockpit-company.sqlite",
            TENN_COMPANY_CONTEXT_DB="/tmp/tenn-company.sqlite",
            TENN_QUAL_CONTEXT_ARTIFACT_ROOT="/tmp/tenn-qual-root",
        ):
            cfg = apply_runtime_flags(_base_config(), _flags())
        self.assertEqual(
            cfg["rag"]["qualitative_context"]["db_path"],
            "/tmp/cockpit-company.sqlite",
        )

    def test_tenn_company_context_db_feeds_cockpit_when_cockpit_override_absent(self):
        with _Env(
            COCKPIT_COMPANY_DB_PATH=None,
            TENN_COMPANY_CONTEXT_DB="/tmp/tenn-company.sqlite",
            TENN_QUAL_CONTEXT_ARTIFACT_ROOT="/tmp/tenn-qual-root",
        ):
            cfg = apply_runtime_flags(_base_config(), _flags())
        self.assertEqual(
            cfg["rag"]["qualitative_context"]["db_path"],
            "/tmp/tenn-company.sqlite",
        )

    def test_tenn_qual_artifact_root_maps_to_company_sqlite(self):
        with _Env(
            COCKPIT_COMPANY_DB_PATH=None,
            TENN_COMPANY_CONTEXT_DB=None,
            TENN_QUAL_CONTEXT_ARTIFACT_ROOT="/tmp/tenn-qual-root",
        ):
            cfg = apply_runtime_flags(_base_config(), _flags())
        self.assertEqual(
            cfg["rag"]["qualitative_context"]["db_path"],
            "/tmp/tenn-qual-root/company.sqlite",
        )

    def test_default_relative_company_path_prefers_fresher_artifact_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo_root = root / "financial-engine_v2"
            repo_root.mkdir()
            stale_repo_db = root / "reports" / "qual_context" / "company.sqlite"
            artifact_root = root / "qual_artifacts"
            fresh_artifact_db = artifact_root / "company.sqlite"
            _touch(stale_repo_db, 100)
            _touch(fresh_artifact_db, 200)

            original_root = bootstrap.DEFAULT_QUAL_CONTEXT_ARTIFACT_ROOT
            bootstrap.DEFAULT_QUAL_CONTEXT_ARTIFACT_ROOT = artifact_root
            try:
                resolved = bootstrap.resolve_company_context_db_path(
                    repo_root=repo_root,
                    raw_path="reports/qual_context/company.sqlite",
                )
            finally:
                bootstrap.DEFAULT_QUAL_CONTEXT_ARTIFACT_ROOT = original_root

        self.assertEqual(resolved, fresh_artifact_db.resolve())

    def test_explicit_absolute_company_path_is_not_overridden_by_default_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo_root = root / "financial-engine_v2"
            repo_root.mkdir()
            explicit_db = root / "explicit" / "company.sqlite"
            artifact_root = root / "qual_artifacts"
            fresh_artifact_db = artifact_root / "company.sqlite"
            _touch(explicit_db, 100)
            _touch(fresh_artifact_db, 200)

            original_root = bootstrap.DEFAULT_QUAL_CONTEXT_ARTIFACT_ROOT
            bootstrap.DEFAULT_QUAL_CONTEXT_ARTIFACT_ROOT = artifact_root
            try:
                resolved = bootstrap.resolve_company_context_db_path(
                    repo_root=repo_root,
                    raw_path=str(explicit_db),
                )
            finally:
                bootstrap.DEFAULT_QUAL_CONTEXT_ARTIFACT_ROOT = original_root

        self.assertEqual(resolved, explicit_db.resolve())


if __name__ == "__main__":
    unittest.main()
