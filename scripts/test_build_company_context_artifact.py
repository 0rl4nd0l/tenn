import contextlib
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import textwrap
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
MOD = load_module(ROOT / "scripts" / "build_company_context_artifact.py", "build_company_context_artifact")


def _make_fake_builder(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import argparse
            import json
            import sqlite3
            from pathlib import Path

            ap = argparse.ArgumentParser()
            ap.add_argument("--out", required=True)
            ap.add_argument("--manifest-json", required=True)
            ap.add_argument("--query", default="")
            args, _unknown = ap.parse_known_args()

            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(out))
            try:
                conn.execute(
                    "CREATE TABLE context_chunks ("
                    "chunk_id TEXT PRIMARY KEY, corpus TEXT, company TEXT, "
                    "text TEXT, embedding_json TEXT)"
                )
                conn.execute(
                    "INSERT INTO context_chunks(chunk_id, corpus, company, text, embedding_json) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("company:BHP:1", "company", "BHP", "Revenue and risk context", "[0.1, 0.2]"),
                )
                conn.commit()
            finally:
                conn.close()
            out.with_suffix(".jsonl").write_text("{}\\n", encoding="utf-8")
            manifest = {
                "status": "success",
                "output": {
                    "chunks_written": 1,
                    "query_result_count": 1 if args.query else 0,
                },
            }
            Path(args.manifest_json).write_text(json.dumps(manifest), encoding="utf-8")
            """
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o755)


def _run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = MOD.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _build_args(root: Path, *, run_id: str = "validate"):
    pdf_dir = root / "pdfs"
    pdf_dir.mkdir(exist_ok=True)
    fake_builder = root / "fake_builder.py"
    _make_fake_builder(fake_builder)
    return MOD.parse_args(
        [
            "--stage-only",
            "--repo-root",
            str(root),
            "--pdf-dir",
            str(pdf_dir),
            "--artifact-root",
            str(root / "artifact"),
            "--staging-root",
            str(root / "staging"),
            "--builder-script",
            str(fake_builder),
            "--run-id",
            run_id,
        ]
    )


def _write_staged_db(plan, *, embedding_json: str = "[0.1, 0.2]", include_embedding_column: bool = True) -> None:
    plan.staged_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(plan.staged_db))
    try:
        if include_embedding_column:
            conn.execute(
                "CREATE TABLE context_chunks ("
                "chunk_id TEXT PRIMARY KEY, corpus TEXT, company TEXT, text TEXT, embedding_json TEXT)"
            )
            conn.execute(
                "INSERT INTO context_chunks(chunk_id, corpus, company, text, embedding_json) VALUES (?, ?, ?, ?, ?)",
                ("company:BHP:1", "company", "BHP", "Revenue and risk context", embedding_json),
            )
        else:
            conn.execute("CREATE TABLE context_chunks (chunk_id TEXT PRIMARY KEY, corpus TEXT)")
            conn.execute(
                "INSERT INTO context_chunks(chunk_id, corpus) VALUES (?, ?)",
                ("company:BHP:1", "company"),
            )
        conn.commit()
    finally:
        conn.close()
    plan.staged_manifest.write_text(
        json.dumps({"status": "success", "output": {"chunks_written": 1, "query_result_count": 1}}),
        encoding="utf-8",
    )


class BuildCompanyContextArtifactTests(unittest.TestCase):
    def test_default_plan_mode_does_not_require_or_create_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact_root = root / "artifact"
            staging_root = root / "staging"

            code, stdout, stderr = _run_main(
                [
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(root / "missing-pdfs"),
                    "--artifact-root",
                    str(artifact_root),
                    "--staging-root",
                    str(staging_root),
                    "--run-id",
                    "plan-test",
                ]
            )

            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["mode"], "plan")
            self.assertFalse(artifact_root.exists())
            self.assertFalse(staging_root.exists())

    def test_hash_backend_requires_explicit_test_flag(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()

            code, _stdout, stderr = _run_main(
                [
                    "--stage-only",
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(pdf_dir),
                    "--artifact-root",
                    str(root / "artifact"),
                    "--staging-root",
                    str(root / "staging"),
                    "--builder-script",
                    str(root / "fake_builder.py"),
                    "--embed-backend",
                    "hash",
                    "--run-id",
                    "hash-reject",
                ]
            )

            self.assertEqual(code, 2)
            self.assertIn("hash is not allowed", stderr)

    def test_plan_mode_hash_backend_still_requires_explicit_test_flag(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            code, _stdout, stderr = _run_main(
                [
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(root / "missing-pdfs"),
                    "--artifact-root",
                    str(root / "artifact"),
                    "--staging-root",
                    str(root / "staging"),
                    "--embed-backend",
                    "hash",
                    "--run-id",
                    "hash-plan-reject",
                ]
            )

            self.assertEqual(code, 2)
            self.assertIn("hash is not allowed", stderr)

    def test_run_id_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()
            fake_builder = root / "fake_builder.py"
            _make_fake_builder(fake_builder)

            code, _stdout, stderr = _run_main(
                [
                    "--allow-production-write",
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(pdf_dir),
                    "--artifact-root",
                    str(root / "artifact"),
                    "--builder-script",
                    str(fake_builder),
                    "--run-id",
                    "../../outside",
                ]
            )

            self.assertEqual(code, 2)
            self.assertIn("--run-id must be a single safe path segment", stderr)

    def test_existing_lock_fails_closed_before_build(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()
            fake_builder = root / "fake_builder.py"
            _make_fake_builder(fake_builder)
            lock_path = root / "build.lock"
            lock_path.write_text("busy\n", encoding="utf-8")

            code, _stdout, stderr = _run_main(
                [
                    "--stage-only",
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(pdf_dir),
                    "--artifact-root",
                    str(root / "artifact"),
                    "--staging-root",
                    str(root / "staging"),
                    "--builder-script",
                    str(fake_builder),
                    "--lock-path",
                    str(lock_path),
                    "--run-id",
                    "locked",
                ]
            )

            self.assertEqual(code, 3)
            self.assertIn("Build lock already exists", stderr)
            self.assertFalse((root / "staging" / "locked" / "company.sqlite").exists())

    def test_stage_only_builds_and_validates_without_promoting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()
            fake_builder = root / "fake_builder.py"
            _make_fake_builder(fake_builder)

            code, stdout, stderr = _run_main(
                [
                    "--stage-only",
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(pdf_dir),
                    "--artifact-root",
                    str(root / "artifact"),
                    "--staging-root",
                    str(root / "staging"),
                    "--builder-script",
                    str(fake_builder),
                    "--embed-backend",
                    "hash",
                    "--allow-test-hash-backend",
                    "--run-id",
                    "stage",
                ]
            )

            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertFalse(payload["promoted"])
            self.assertEqual(payload["chunk_count"], 1)
            self.assertTrue((root / "staging" / "stage" / "company.sqlite").exists())
            self.assertFalse((root / "artifact" / "company.sqlite").exists())

    def test_existing_staging_artifact_fails_closed_before_build(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()
            fake_builder = root / "fake_builder.py"
            _make_fake_builder(fake_builder)
            stale_db = root / "staging" / "stale" / "company.sqlite"
            stale_db.parent.mkdir(parents=True)
            stale_db.write_text("stale\n", encoding="utf-8")

            code, _stdout, stderr = _run_main(
                [
                    "--stage-only",
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(pdf_dir),
                    "--artifact-root",
                    str(root / "artifact"),
                    "--staging-root",
                    str(root / "staging"),
                    "--builder-script",
                    str(fake_builder),
                    "--run-id",
                    "stale",
                ]
            )

            self.assertEqual(code, 2)
            self.assertIn("Staging artifacts already exist", stderr)

    def test_staged_validation_rejects_malformed_embedding_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = MOD.build_plan(_build_args(root, run_id="bad-embedding"))
            _write_staged_db(plan, embedding_json="not-json")

            with self.assertRaisesRegex(MOD.RunnerError, "Invalid embedding_json"):
                MOD.validate_staged_artifacts(plan)

    def test_staged_validation_rejects_missing_embedding_column(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = MOD.build_plan(_build_args(root, run_id="missing-column"))
            _write_staged_db(plan, include_embedding_column=False)

            with self.assertRaisesRegex(MOD.RunnerError, "missing required columns"):
                MOD.validate_staged_artifacts(plan)

    def test_staged_validation_rejects_corrupt_sqlite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = MOD.build_plan(_build_args(root, run_id="corrupt"))
            plan.staged_db.parent.mkdir(parents=True, exist_ok=True)
            plan.staged_db.write_text("not sqlite", encoding="utf-8")
            plan.staged_manifest.write_text(
                json.dumps({"status": "success", "output": {"chunks_written": 1, "query_result_count": 1}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(MOD.RunnerError, "SQLite integrity check"):
                MOD.validate_staged_artifacts(plan)

    def test_production_write_requires_staging_inside_artifact_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()
            fake_builder = root / "fake_builder.py"
            _make_fake_builder(fake_builder)

            code, _stdout, stderr = _run_main(
                [
                    "--allow-production-write",
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(pdf_dir),
                    "--artifact-root",
                    str(root / "artifact"),
                    "--staging-root",
                    str(root / "outside-staging"),
                    "--builder-script",
                    str(fake_builder),
                    "--run-id",
                    "outside",
                ]
            )

            self.assertEqual(code, 2)
            self.assertIn("Production staging must be inside the artifact root", stderr)

    def test_production_write_promotes_validated_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_dir = root / "pdfs"
            pdf_dir.mkdir()
            fake_builder = root / "fake_builder.py"
            _make_fake_builder(fake_builder)

            code, stdout, stderr = _run_main(
                [
                    "--allow-production-write",
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(pdf_dir),
                    "--artifact-root",
                    str(root / "artifact"),
                    "--staging-root",
                    str(root / "artifact" / "company_build_runs"),
                    "--builder-script",
                    str(fake_builder),
                    "--run-id",
                    "promote",
                ]
            )

            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertTrue(payload["promoted"])
            self.assertEqual(payload["embedding_dim"], 2)
            self.assertTrue((root / "artifact" / "company.sqlite").exists())
            self.assertTrue((root / "artifact" / "company_manifest.json").exists())
            self.assertTrue((root / "artifact" / "company.jsonl").exists())
            self.assertFalse((root / "artifact" / "company_build_runs" / "promote" / "company.sqlite").exists())
            self.assertFalse((root / "artifact" / "company.sqlite.lock").exists())

    def test_existing_production_db_requires_replace_flag(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf_dir = root / "pdfs"
            artifact_root = root / "artifact"
            pdf_dir.mkdir()
            artifact_root.mkdir()
            (artifact_root / "company.sqlite").write_text("existing\n", encoding="utf-8")
            fake_builder = root / "fake_builder.py"
            _make_fake_builder(fake_builder)

            code, _stdout, stderr = _run_main(
                [
                    "--allow-production-write",
                    "--repo-root",
                    str(root),
                    "--pdf-dir",
                    str(pdf_dir),
                    "--artifact-root",
                    str(artifact_root),
                    "--staging-root",
                    str(artifact_root / "company_build_runs"),
                    "--builder-script",
                    str(fake_builder),
                    "--run-id",
                    "exists",
                ]
            )

            self.assertEqual(code, 2)
            self.assertIn("Production DB already exists", stderr)


if __name__ == "__main__":
    unittest.main()
