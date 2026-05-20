from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from scripts.reporting import eval_spine_ingest as ingest


def tiny_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "job_id": "tiny_eval_job",
                "lane": "Evaluation",
                "supporting_lanes": [],
                "mode": "safe_extension",
                "production_data_access": False,
                "branch": "safe/tiny",
                "head": "abc123def456",
                "base_head": None,
                "worktree": "/tmp/tiny",
                "task_card": {"path": "docs/agent_tasks/tiny.md", "sha256": "abc", "validation_ok": True},
                "output_dir": "reports/agent_jobs/tiny_eval_job",
                "started_at": "2026-05-20T00:00:00Z",
                "completed_at": "2026-05-20T00:01:00Z",
                "status": "complete",
                "verdicts": [{"verdict": "DUCKDB_SAFE_OFFLINE", "truth_status": "reported", "confidence": "high"}],
                "scorecards": [
                    {
                        "scorecard_profile": "canonical_core",
                        "status": "passed",
                        "document_count": 10,
                        "metric_check_count": 24,
                        "overclaim_guard": "canonical_core is not broad production extraction coverage",
                    }
                ],
                "validation_commands": [{"command": "pytest", "result": "passed", "exit_code": 0}],
                "changed_files": [],
                "data_missing": [
                    {
                        "field": "base_head",
                        "code": "missing_base_head",
                        "description": "No base head.",
                        "source_artifact": "test",
                    }
                ],
                "degraded_states": [
                    {"classification": "expected_404", "route_path": "/api/missing", "is_failure": False}
                ],
                "source_artifacts": [{"path": "reports/agent_jobs/tiny/README.md", "artifact_type": "readme"}],
                "save_recommendation": "SAVE_DEFERRED",
                "do_not_overclaim": [
                    "canonical_core must not be presented as broad production extraction coverage"
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_ingest_refuses_unsafe_db_path_outside_tmp_or_reports_eval_spine() -> None:
    with pytest.raises(ValueError, match="reports/eval_spine"):
        ingest.validate_db_path(Path("/unsafe_eval_spine_test.duckdb"), repo_root=Path("/repo"))


def test_ingest_handles_missing_duckdb_gracefully(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    tiny_manifest(manifest_path)
    db_path = tmp_path / "reports" / "eval_spine" / "tiny.duckdb"

    result = ingest.main(["--db", str(db_path), str(manifest_path)], duckdb_module=None, repo_root=tmp_path)

    assert result == ingest.DUCKDB_MISSING_EXIT


def test_ingest_inserts_tiny_manifest_when_duckdb_is_available(tmp_path: Path) -> None:
    duckdb = pytest.importorskip("duckdb")
    manifest_path = tmp_path / "manifest.json"
    tiny_manifest(manifest_path)
    db_path = tmp_path / "reports" / "eval_spine" / "tiny.duckdb"

    result = ingest.main(["--db", str(db_path), str(manifest_path)], duckdb_module=duckdb, repo_root=tmp_path)

    assert result == 0
    con = duckdb.connect(str(db_path))
    try:
        rows = con.execute("SELECT job_id, lane, production_data_access FROM artifact_runs").fetchall()
        scorecards = con.execute("SELECT scorecard_profile FROM scorecard_results").fetchall()
    finally:
        con.close()
    assert rows == [("tiny_eval_job", "Evaluation", False)]
    assert scorecards == [("canonical_core",)]


def test_ingest_script_does_not_import_backend_modules() -> None:
    tree = ast.parse(Path(ingest.__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    assert not any(name == "app" or name.startswith("app.") for name in imported)
    assert not any("financial_engine" in name or "financial-engine" in name for name in imported)
