#!/usr/bin/env python3
"""Ingest curated report JSON into an offline Evaluation Spine DuckDB file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


DUCKDB_MISSING_EXIT = 2


def repo_root_from_cwd() -> Path:
    return Path.cwd().resolve()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_db_path(db_path: Path, repo_root: Path | None = None) -> Path:
    repo_root = (repo_root or repo_root_from_cwd()).resolve()
    candidate = db_path.expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    candidate = candidate.resolve(strict=False)
    reports_eval_spine = (repo_root / "reports" / "eval_spine").resolve(strict=False)
    tmp_root = Path("/tmp").resolve(strict=False)
    if not (is_relative_to(candidate, reports_eval_spine) or is_relative_to(candidate, tmp_root)):
        raise ValueError("DuckDB output path must be under reports/eval_spine/ or /tmp")
    return candidate


def load_duckdb_module() -> Any | None:
    if os.environ.get("TENN_EVAL_SPINE_FORCE_NO_DUCKDB") == "1":
        return None
    try:
        import duckdb  # type: ignore
    except ImportError:
        return None
    return duckdb


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def schema_sql_path() -> Path:
    return Path(__file__).resolve().with_name("eval_spine_schema.sql")


def source_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(repo_root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def detect_artifact_type(payload: Any, path: Path) -> str:
    if isinstance(payload, dict) and "source_artifacts" in payload and "do_not_overclaim" in payload:
        return "manifest"
    if isinstance(payload, dict) and "changed_files" in payload and "validation" in payload:
        return "diff_check"
    if isinstance(payload, dict) and "active_record" in payload and "allowed_files" in payload:
        return "status"
    if path.name == "status.json":
        return "status"
    if path.name == "diff-check.json":
        return "diff_check"
    if "metric" in path.name:
        return "metric_inventory"
    if "a2m" in path.name or "trace" in path.name:
        return "news_trace"
    if "memory" in path.name or "schema_inventory" in path.name or "contamination" in path.name:
        return "memory_inventory"
    return "json_artifact"


def run_id_for(path: Path, payload: Any, artifact_type: str) -> str:
    if isinstance(payload, dict):
        if artifact_type == "manifest" and isinstance(payload.get("job_id"), str):
            return payload["job_id"]
        if artifact_type == "status" and isinstance(payload.get("job_id"), str):
            return payload["job_id"]
        validation = payload.get("validation")
        if isinstance(validation, dict):
            metadata = validation.get("metadata")
            if isinstance(metadata, dict) and isinstance(metadata.get("job_id"), str):
                return metadata["job_id"]
        if isinstance(payload.get("job_id"), str):
            return payload["job_id"]
    return f"artifact_{sha256_text(path.as_posix())[:16]}"


def run_record(path: Path, payload: Any, artifact_type: str, repo_root: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "run_id": run_id_for(path, payload, artifact_type),
        "job_id": None,
        "lane": None,
        "mode": None,
        "status": None,
        "branch": None,
        "head": None,
        "base_head": None,
        "worktree": None,
        "task_card_path": None,
        "output_dir": None,
        "production_data_access": None,
        "started_at": None,
        "completed_at": None,
        "save_recommendation": None,
        "source_artifact_path": source_path(path, repo_root),
        "payload_json": json.dumps(payload, sort_keys=True),
    }
    if not isinstance(payload, dict):
        return record

    if artifact_type == "manifest":
        task_card = payload.get("task_card")
        record.update(
            {
                "job_id": payload.get("job_id"),
                "lane": payload.get("lane"),
                "mode": payload.get("mode"),
                "status": payload.get("status"),
                "branch": payload.get("branch"),
                "head": payload.get("head"),
                "base_head": payload.get("base_head"),
                "worktree": payload.get("worktree"),
                "task_card_path": task_card.get("path") if isinstance(task_card, dict) else None,
                "output_dir": payload.get("output_dir"),
                "production_data_access": payload.get("production_data_access"),
                "started_at": payload.get("started_at"),
                "completed_at": payload.get("completed_at"),
                "save_recommendation": payload.get("save_recommendation"),
            }
        )
    elif artifact_type == "status":
        record.update(
            {
                "job_id": payload.get("job_id"),
                "lane": payload.get("lane"),
                "mode": payload.get("mutation_mode"),
                "status": payload.get("status"),
                "branch": payload.get("branch"),
                "worktree": payload.get("worktree"),
                "task_card_path": payload.get("task_card"),
                "output_dir": payload.get("output_dir"),
                "production_data_access": payload.get("production_data_access"),
                "started_at": payload.get("started_at") or payload.get("claimed_at"),
                "completed_at": payload.get("completed_at") or payload.get("released_at") or payload.get("updated_at"),
            }
        )
    elif artifact_type == "diff_check":
        validation = payload.get("validation")
        metadata = validation.get("metadata") if isinstance(validation, dict) else {}
        if isinstance(metadata, dict):
            record.update(
                {
                    "job_id": metadata.get("job_id"),
                    "lane": metadata.get("lane"),
                    "mode": metadata.get("mutation_mode"),
                    "output_dir": metadata.get("output_dir"),
                    "production_data_access": metadata.get("production_data_access"),
                    "status": "diff_check_ok" if payload.get("ok") else "diff_check_failed",
                }
            )
    return record


def execute_schema(con: Any, schema_path: Path) -> None:
    con.execute(schema_path.read_text(encoding="utf-8"))


def insert_artifact_run(con: Any, record: dict[str, Any]) -> None:
    con.execute("DELETE FROM artifact_runs WHERE run_id = ?", [record["run_id"]])
    con.execute(
        """
        INSERT INTO artifact_runs (
          run_id, job_id, lane, mode, status, branch, head, base_head, worktree,
          task_card_path, output_dir, production_data_access, started_at,
          completed_at, save_recommendation, source_artifact_path, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            record["run_id"],
            record["job_id"],
            record["lane"],
            record["mode"],
            record["status"],
            record["branch"],
            record["head"],
            record["base_head"],
            record["worktree"],
            record["task_card_path"],
            record["output_dir"],
            record["production_data_access"],
            record["started_at"],
            record["completed_at"],
            record["save_recommendation"],
            record["source_artifact_path"],
            record["payload_json"],
        ],
    )


def delete_child_rows(con: Any, run_id: str) -> None:
    for table in (
        "task_cards",
        "validation_commands",
        "artifact_files",
        "scorecard_results",
        "metric_expectations",
        "metric_results",
        "runtime_smokes",
        "route_smokes",
        "source_label_checks",
        "memory_audit_results",
        "news_trace_results",
        "dirty_worktree_events",
        "registry_events",
        "data_missing_items",
        "decisions_and_verdicts",
    ):
        con.execute(f"DELETE FROM {table} WHERE run_id = ?", [run_id])


def insert_manifest_children(con: Any, run_id: str, payload: dict[str, Any], source_artifact_path: str) -> None:
    task_card = payload.get("task_card")
    if isinstance(task_card, dict):
        pk = sha256_text(f"{run_id}:task_card:{task_card.get('path')}")
        con.execute(
            "INSERT INTO task_cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            [
                pk,
                run_id,
                payload.get("job_id"),
                task_card.get("path"),
                task_card.get("sha256"),
                task_card.get("validation_ok"),
                json.dumps(task_card.get("validation_issues", []), sort_keys=True),
                source_artifact_path,
            ],
        )
    for idx, item in enumerate(payload.get("source_artifacts", [])):
        if not isinstance(item, dict):
            continue
        pk = sha256_text(f"{run_id}:artifact:{idx}:{item.get('path')}")
        con.execute(
            "INSERT INTO artifact_files VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            [
                pk,
                run_id,
                item.get("path"),
                item.get("artifact_type"),
                item.get("sha256"),
                item.get("schema"),
                item.get("notes"),
                source_artifact_path,
            ],
        )
    for idx, item in enumerate(payload.get("validation_commands", [])):
        if not isinstance(item, dict):
            continue
        pk = sha256_text(f"{run_id}:validation:{idx}:{item.get('command')}")
        con.execute(
            "INSERT INTO validation_commands VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            [
                pk,
                run_id,
                item.get("command"),
                item.get("cwd"),
                item.get("result"),
                item.get("exit_code"),
                item.get("notes"),
                source_artifact_path,
            ],
        )
    for idx, item in enumerate(payload.get("scorecards", [])):
        if not isinstance(item, dict):
            continue
        pk = sha256_text(f"{run_id}:scorecard:{idx}:{item.get('scorecard_profile')}")
        con.execute(
            "INSERT INTO scorecard_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            [
                pk,
                run_id,
                item.get("scorecard_profile"),
                item.get("status") or item.get("pass_fail_status"),
                item.get("document_count"),
                item.get("metric_check_count"),
                item.get("eligible_metric_count"),
                item.get("candidate_count"),
                item.get("ambiguous_count"),
                item.get("unsupported_count"),
                item.get("data_missing_count"),
                item.get("overclaim_guard"),
                json.dumps(item, sort_keys=True),
                source_artifact_path,
            ],
        )
    for idx, item in enumerate(payload.get("data_missing", [])):
        if not isinstance(item, dict):
            continue
        pk = sha256_text(f"{run_id}:data_missing:{idx}:{item.get('code')}")
        con.execute(
            "INSERT INTO data_missing_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            [
                pk,
                run_id,
                item.get("field"),
                item.get("code"),
                item.get("class"),
                item.get("description"),
                item.get("blocked_by_policy"),
                item.get("blocked_by_environment"),
                item.get("expected_empty_state"),
                item.get("source_artifact") or source_artifact_path,
            ],
        )
    for idx, item in enumerate(payload.get("verdicts", [])):
        if not isinstance(item, dict):
            continue
        pk = sha256_text(f"{run_id}:verdict:{idx}:{item.get('verdict')}")
        con.execute(
            "INSERT INTO decisions_and_verdicts VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            [
                pk,
                run_id,
                item.get("verdict"),
                item.get("truth_status"),
                item.get("confidence"),
                item.get("notes"),
                item.get("source_artifact") or source_artifact_path,
            ],
        )


def insert_diff_children(con: Any, run_id: str, payload: dict[str, Any], source_artifact_path: str) -> None:
    for idx, item in enumerate(payload.get("changed_files", [])):
        if not isinstance(item, dict):
            continue
        pk = sha256_text(f"{run_id}:changed:{idx}:{item.get('path')}")
        con.execute(
            "INSERT INTO dirty_worktree_events VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            [
                pk,
                run_id,
                item.get("path"),
                item.get("status"),
                item.get("path") not in payload.get("disallowed_files", []),
                source_artifact_path,
            ],
        )


def insert_status_child(con: Any, run_id: str, payload: dict[str, Any], source_artifact_path: str) -> None:
    pk = sha256_text(f"{run_id}:registry:{payload.get('status')}:{payload.get('claimed_at')}")
    con.execute(
        "INSERT INTO registry_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        [
            pk,
            run_id,
            payload.get("job_id"),
            payload.get("lane"),
            payload.get("status"),
            payload.get("branch"),
            payload.get("worktree"),
            payload.get("claimed_at"),
            payload.get("released_at"),
            source_artifact_path,
        ],
    )


def ingest_files(db_path: Path, input_paths: list[Path], duckdb_module: Any, repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = (repo_root or repo_root_from_cwd()).resolve()
    db_path = validate_db_path(db_path, repo_root=repo_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb_module.connect(str(db_path))
    try:
        execute_schema(con, schema_sql_path())
        inserted: list[str] = []
        for raw_path in input_paths:
            path = raw_path.resolve(strict=False)
            payload = load_json(path)
            artifact_type = detect_artifact_type(payload, path)
            record = run_record(path, payload, artifact_type, repo_root)
            insert_artifact_run(con, record)
            delete_child_rows(con, record["run_id"])
            if isinstance(payload, dict) and artifact_type == "manifest":
                insert_manifest_children(con, record["run_id"], payload, record["source_artifact_path"])
            elif isinstance(payload, dict) and artifact_type == "diff_check":
                insert_diff_children(con, record["run_id"], payload, record["source_artifact_path"])
            elif isinstance(payload, dict) and artifact_type == "status":
                insert_status_child(con, record["run_id"], payload, record["source_artifact_path"])
            inserted.append(record["run_id"])
        return {"ok": True, "db": str(db_path), "inserted_run_ids": inserted}
    finally:
        con.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest curated report JSON into an offline DuckDB file.")
    parser.add_argument("--db", required=True, help="DuckDB output path under reports/eval_spine/ or /tmp")
    parser.add_argument("json_files", nargs="+", help="manifest/report JSON files to ingest")
    return parser


def main(argv: list[str] | None = None, duckdb_module: Any | str | None = "auto", repo_root: Path | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        db_path = validate_db_path(Path(args.db), repo_root=repo_root)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if duckdb_module == "auto":
        duckdb_module = load_duckdb_module()
    if duckdb_module is None:
        print(
            "DuckDB Python package is unavailable. Install duckdb in the reporting/dev environment to run ingestion.",
            file=sys.stderr,
        )
        return DUCKDB_MISSING_EXIT

    try:
        result = ingest_files(db_path, [Path(item) for item in args.json_files], duckdb_module, repo_root=repo_root)
    except Exception as exc:
        print(f"ingest failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
