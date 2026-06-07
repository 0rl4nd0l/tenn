#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF_DIR = Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs")
DEFAULT_ARTIFACT_ROOT = Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context")
DEFAULT_STAGING_ROOT = Path("/tmp/tenn_company_context_builds")
DEFAULT_QUERY = "management discussion revenue cash flow risk"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class RunnerError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = int(exit_code)


@dataclass(frozen=True)
class BuildPlan:
    repo_root: Path
    pdf_dir: Path
    artifact_root: Path
    staging_root: Path
    builder_script: Path
    python_bin: str
    run_id: str
    final_db: Path
    staged_db: Path
    staged_manifest: Path
    staged_jsonl: Path
    final_manifest: Path
    final_jsonl: Path
    lock_path: Path
    embed_backend: str
    embed_model: str
    st_device: str
    st_batch_size: int
    content_scope: str
    fallback_fulltext: bool
    max_chars: int
    overlap_words: int
    health_json: Path
    allow_warning: bool
    query: str
    top_k: int
    company_allowlist_path: str
    invalid_company_fail_threshold_pct: float
    invalid_company_fail_min_count: int
    allow_production_write: bool
    stage_only: bool
    replace_existing: bool
    allow_test_hash_backend: bool


def _utc_run_id() -> str:
    return dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def normalize_run_id(raw: str) -> str:
    run_id = str(raw or "").strip()
    if not run_id:
        raise RunnerError("--run-id cannot be blank")
    if "/" in run_id or "\\" in run_id or run_id in {".", ".."} or ".." in run_id.split("."):
        raise RunnerError("--run-id must be a single safe path segment")
    if not RUN_ID_RE.match(run_id):
        raise RunnerError("--run-id must start with an alphanumeric character and contain only A-Z, a-z, 0-9, '_', '.', '-'")
    return run_id


def _resolve_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def default_python_bin() -> str:
    venv_python = REPO_ROOT / "financial-engine_v2" / ".venv" / "bin" / "python"
    if venv_python.exists() and os.access(venv_python, os.X_OK):
        return str(venv_python)
    return sys.executable


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Fail-closed runner for the production company qualitative-context SQLite artifact."
    )
    ap.add_argument("--repo-root", default=str(REPO_ROOT))
    ap.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR))
    ap.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    ap.add_argument(
        "--staging-root",
        default="",
        help=(
            "Staging root. Defaults to /tmp for plan/stage-only runs and "
            "<artifact-root>/company_build_runs for production promotion."
        ),
    )
    ap.add_argument("--builder-script", default=str(REPO_ROOT / "scripts" / "build_qualitative_context_db.py"))
    ap.add_argument("--python-bin", default=default_python_bin())
    ap.add_argument("--run-id", default="")
    ap.add_argument("--lock-path", default="")
    ap.add_argument("--stage-only", action="store_true", help="Build and validate staging output, but do not promote.")
    ap.add_argument(
        "--allow-production-write",
        action="store_true",
        help="Promote validated staging output to the production artifact root.",
    )
    ap.add_argument(
        "--replace-existing",
        action="store_true",
        help="Allow replacing an existing production company.sqlite during promotion.",
    )
    ap.add_argument("--embed-backend", default="sentence-transformers", choices=["sentence-transformers", "ollama", "hash"])
    ap.add_argument(
        "--allow-test-hash-backend",
        action="store_true",
        help="Permit --embed-backend hash for temporary tests only. Never use for production semantic artifact.",
    )
    ap.add_argument("--embed-model", default="BAAI/bge-large-en-v1.5")
    ap.add_argument("--st-device", default="auto", choices=["auto", "cpu", "cuda", "cuda_strict"])
    ap.add_argument("--st-batch-size", type=int, default=16)
    ap.add_argument("--content-scope", default="targeted", choices=["targeted", "fulltext"])
    ap.add_argument("--fallback-fulltext", action="store_true")
    ap.add_argument("--max-chars", type=int, default=1200)
    ap.add_argument("--overlap-words", type=int, default=60)
    ap.add_argument("--health-json", default=str(REPO_ROOT / "reports" / "research_engine_health.json"))
    ap.add_argument("--allow-warning", action="store_true")
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--company-allowlist-path", default="")
    ap.add_argument("--invalid-company-fail-threshold-pct", type=float, default=1.0)
    ap.add_argument("--invalid-company-fail-min-count", type=int, default=20)
    return ap.parse_args(argv)


def build_plan(args: argparse.Namespace) -> BuildPlan:
    repo_root = _resolve_path(args.repo_root)
    pdf_dir = _resolve_path(args.pdf_dir)
    artifact_root = _resolve_path(args.artifact_root)
    builder_script = _resolve_path(args.builder_script)
    run_id = normalize_run_id(str(args.run_id or _utc_run_id()))
    staging_root_value = str(args.staging_root or "").strip()
    if staging_root_value:
        staging_root = _resolve_path(staging_root_value)
    elif bool(args.allow_production_write):
        staging_root = (artifact_root / "company_build_runs").resolve()
    else:
        staging_root = DEFAULT_STAGING_ROOT.resolve()

    final_db = artifact_root / "company.sqlite"
    run_root = (staging_root / run_id).resolve()
    staged_db = run_root / "company.sqlite"
    lock_path = _resolve_path(args.lock_path) if str(args.lock_path or "").strip() else (
        artifact_root / "company.sqlite.lock"
        if bool(args.allow_production_write)
        else run_root / "company.sqlite.lock"
    )

    return BuildPlan(
        repo_root=repo_root,
        pdf_dir=pdf_dir,
        artifact_root=artifact_root,
        staging_root=staging_root,
        builder_script=builder_script,
        python_bin=str(args.python_bin),
        run_id=run_id,
        final_db=final_db,
        staged_db=staged_db,
        staged_manifest=run_root / "company_manifest.json",
        staged_jsonl=staged_db.with_suffix(".jsonl"),
        final_manifest=artifact_root / "company_manifest.json",
        final_jsonl=final_db.with_suffix(".jsonl"),
        lock_path=lock_path,
        embed_backend=str(args.embed_backend),
        embed_model=str(args.embed_model),
        st_device=str(args.st_device),
        st_batch_size=int(args.st_batch_size),
        content_scope=str(args.content_scope),
        fallback_fulltext=bool(args.fallback_fulltext),
        max_chars=int(args.max_chars),
        overlap_words=int(args.overlap_words),
        health_json=_resolve_path(args.health_json),
        allow_warning=bool(args.allow_warning),
        query=str(args.query or ""),
        top_k=int(args.top_k),
        company_allowlist_path=str(args.company_allowlist_path or ""),
        invalid_company_fail_threshold_pct=float(args.invalid_company_fail_threshold_pct),
        invalid_company_fail_min_count=int(args.invalid_company_fail_min_count),
        allow_production_write=bool(args.allow_production_write),
        stage_only=bool(args.stage_only),
        replace_existing=bool(args.replace_existing),
        allow_test_hash_backend=bool(args.allow_test_hash_backend),
    )


def validate_plan(plan: BuildPlan) -> None:
    if plan.allow_production_write and plan.stage_only:
        raise RunnerError("Use either --stage-only or --allow-production-write, not both.")
    if plan.embed_backend == "hash" and not plan.allow_test_hash_backend:
        raise RunnerError("--embed-backend hash is not allowed for company artifact provisioning.")
    if plan.allow_production_write and plan.embed_backend == "hash":
        raise RunnerError("--allow-production-write cannot be combined with --embed-backend hash.")
    if plan.st_batch_size < 1:
        raise RunnerError("--st-batch-size must be >= 1")
    if plan.max_chars < 1:
        raise RunnerError("--max-chars must be >= 1")
    if plan.overlap_words < 0:
        raise RunnerError("--overlap-words must be >= 0")
    if plan.top_k < 1:
        raise RunnerError("--top-k must be >= 1")
    if not plan.allow_production_write and not plan.stage_only:
        return
    if plan.allow_production_write and plan.final_db.exists() and not plan.replace_existing:
        raise RunnerError(f"Production DB already exists; pass --replace-existing to replace: {plan.final_db}")
    if plan.allow_production_write and not _is_relative_to(plan.staged_db.parent.resolve(), plan.artifact_root.resolve()):
        raise RunnerError(
            "Production staging must be inside the artifact root so promotion can stay on the artifact filesystem."
        )
    stale_paths = [path for path in (plan.staged_db, plan.staged_manifest, plan.staged_jsonl) if path.exists()]
    if stale_paths:
        joined = ", ".join(str(path) for path in stale_paths)
        raise RunnerError(f"Staging artifacts already exist for run id '{plan.run_id}': {joined}")
    if not plan.repo_root.exists() or not plan.repo_root.is_dir():
        raise RunnerError(f"Repo root not found: {plan.repo_root}")
    if not plan.pdf_dir.exists() or not plan.pdf_dir.is_dir():
        raise RunnerError(f"PDF directory not found: {plan.pdf_dir}")
    if not plan.builder_script.exists() or not plan.builder_script.is_file():
        raise RunnerError(f"Builder script not found: {plan.builder_script}")
    python_path = Path(plan.python_bin)
    if os.sep in plan.python_bin and (not python_path.exists() or not os.access(python_path, os.X_OK)):
        raise RunnerError(f"Python binary not executable: {plan.python_bin}")


def builder_command(plan: BuildPlan) -> list[str]:
    cmd = [
        plan.python_bin,
        str(plan.builder_script),
        "--pdf-dir",
        str(plan.pdf_dir),
        "--db",
        "sqlite",
        "--out",
        str(plan.staged_db),
        "--content-scope",
        plan.content_scope,
        "--corpus",
        "company",
        "--embed-backend",
        plan.embed_backend,
        "--embed-model",
        plan.embed_model,
        "--st-device",
        plan.st_device,
        "--st-batch-size",
        str(plan.st_batch_size),
        "--max-chars",
        str(plan.max_chars),
        "--overlap-words",
        str(plan.overlap_words),
        "--health-json",
        str(plan.health_json),
        "--manifest-json",
        str(plan.staged_manifest),
        "--top-k",
        str(plan.top_k),
    ]
    if plan.fallback_fulltext:
        cmd.append("--fallback-fulltext")
    if plan.allow_warning:
        cmd.append("--allow-warning")
    if plan.company_allowlist_path:
        cmd.extend(["--company-allowlist-path", plan.company_allowlist_path])
    if plan.query:
        cmd.extend(["--query", plan.query, "--corpus-filter", "company"])
    cmd.extend(
        [
            "--invalid-company-fail-threshold-pct",
            str(plan.invalid_company_fail_threshold_pct),
            "--invalid-company-fail-min-count",
            str(plan.invalid_company_fail_min_count),
        ]
    )
    return cmd


@contextlib.contextmanager
def build_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(path), flags, 0o644)
    except FileExistsError as exc:
        raise RunnerError(f"Build lock already exists: {path}", exit_code=3) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            payload = {
                "pid": os.getpid(),
                "created_at_utc": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            }
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        yield
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def _validate_embedding_payloads(conn: sqlite3.Connection, *, expected_count: int) -> int:
    embedding_dim: int | None = None
    parsed_count = 0
    cursor = conn.execute("SELECT chunk_id, embedding_json FROM context_chunks")
    for chunk_id, raw_embedding in cursor:
        parsed_count += 1
        try:
            payload = json.loads(str(raw_embedding or ""))
        except Exception as exc:
            raise RunnerError(f"Invalid embedding_json for chunk {chunk_id}") from exc
        if not isinstance(payload, list) or not payload:
            raise RunnerError(f"embedding_json must be a non-empty JSON list for chunk {chunk_id}")
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in payload):
            raise RunnerError(f"embedding_json must contain only numeric values for chunk {chunk_id}")
        if embedding_dim is None:
            embedding_dim = len(payload)
        elif len(payload) != embedding_dim:
            raise RunnerError(
                f"embedding_json dimension mismatch for chunk {chunk_id}: got {len(payload)}, expected {embedding_dim}"
            )
    if parsed_count != expected_count:
        raise RunnerError(f"Parsed embedding count {parsed_count} does not match chunk count {expected_count}")
    if embedding_dim is None:
        raise RunnerError("No embedding payloads parsed")
    return embedding_dim


def validate_staged_artifacts(plan: BuildPlan) -> dict[str, object]:
    if not plan.staged_db.exists() or not plan.staged_db.is_file() or plan.staged_db.stat().st_size <= 0:
        raise RunnerError(f"Staged DB missing or empty: {plan.staged_db}")
    if not plan.staged_manifest.exists() or not plan.staged_manifest.is_file():
        raise RunnerError(f"Staged manifest missing: {plan.staged_manifest}")

    try:
        manifest = json.loads(plan.staged_manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RunnerError(f"Staged manifest is not valid JSON: {plan.staged_manifest}") from exc
    if not isinstance(manifest, dict):
        raise RunnerError("Staged manifest must be a JSON object")
    if str(manifest.get("status") or "").lower() != "success":
        raise RunnerError(f"Staged manifest did not report success: {manifest.get('status')}")

    try:
        conn = sqlite3.connect(str(plan.staged_db))
        try:
            quick_check_rows = conn.execute("PRAGMA quick_check").fetchall()
            if quick_check_rows != [("ok",)]:
                raise RunnerError(f"Staged DB failed PRAGMA quick_check: {quick_check_rows}")
        except sqlite3.DatabaseError as exc:
            raise RunnerError(f"Staged DB failed SQLite integrity check: {plan.staged_db}") from exc
        if not _table_exists(conn, "context_chunks"):
            raise RunnerError("Staged DB missing context_chunks table")
        columns = _table_columns(conn, "context_chunks")
        required_columns = {"chunk_id", "corpus", "embedding_json"}
        missing_columns = sorted(required_columns - columns)
        if missing_columns:
            raise RunnerError(f"Staged DB missing required columns: {', '.join(missing_columns)}")
        chunk_count = int(conn.execute("SELECT COUNT(*) FROM context_chunks").fetchone()[0])
        if chunk_count <= 0:
            raise RunnerError("Staged DB has zero context_chunks")
        non_company = int(
            conn.execute("SELECT COUNT(*) FROM context_chunks WHERE COALESCE(corpus, '') != 'company'").fetchone()[0]
        )
        if non_company:
            raise RunnerError(f"Staged DB has non-company corpus rows: {non_company}")
        missing_embeddings = int(
            conn.execute(
                "SELECT COUNT(*) FROM context_chunks WHERE COALESCE(embedding_json, '') = ''"
            ).fetchone()[0]
        )
        if missing_embeddings:
            raise RunnerError(f"Staged DB has rows without embedding_json: {missing_embeddings}")
        embedding_dim = _validate_embedding_payloads(conn, expected_count=chunk_count)
    finally:
        try:
            conn.close()
        except UnboundLocalError:
            pass

    output = manifest.get("output") if isinstance(manifest.get("output"), dict) else {}
    manifest_chunks = int(output.get("chunks_written") or 0)
    if manifest_chunks != chunk_count:
        raise RunnerError(f"Manifest chunks_written={manifest_chunks} does not match DB count={chunk_count}")
    query_result_count = int(output.get("query_result_count") or 0)
    if plan.query and query_result_count <= 0:
        raise RunnerError("Query was requested but manifest query_result_count is zero")
    return {
        "chunk_count": chunk_count,
        "query_result_count": query_result_count,
        "embedding_dim": embedding_dim,
        "staged_db": str(plan.staged_db),
        "staged_manifest": str(plan.staged_manifest),
        "staged_jsonl": str(plan.staged_jsonl),
    }


def promote_artifacts(plan: BuildPlan) -> None:
    if not plan.allow_production_write:
        raise RunnerError("Production promotion requires --allow-production-write")
    plan.artifact_root.mkdir(parents=True, exist_ok=True)
    if plan.final_db.exists() and not plan.replace_existing:
        raise RunnerError(f"Production DB already exists; pass --replace-existing to replace: {plan.final_db}")
    os.replace(str(plan.staged_db), str(plan.final_db))
    if plan.staged_manifest.exists():
        os.replace(str(plan.staged_manifest), str(plan.final_manifest))
    if plan.staged_jsonl.exists():
        os.replace(str(plan.staged_jsonl), str(plan.final_jsonl))


def plan_payload(plan: BuildPlan, *, mode: str) -> dict[str, object]:
    return {
        "mode": mode,
        "run_id": plan.run_id,
        "pdf_dir": str(plan.pdf_dir),
        "artifact_root": str(plan.artifact_root),
        "final_db": str(plan.final_db),
        "staged_db": str(plan.staged_db),
        "staged_manifest": str(plan.staged_manifest),
        "lock_path": str(plan.lock_path),
        "embed_backend": plan.embed_backend,
        "embed_model": plan.embed_model,
        "st_device": plan.st_device,
        "content_scope": plan.content_scope,
        "fallback_fulltext": plan.fallback_fulltext,
        "allow_production_write": plan.allow_production_write,
        "replace_existing": plan.replace_existing,
        "command": builder_command(plan),
    }


def run_build(plan: BuildPlan) -> dict[str, object]:
    validate_plan(plan)
    plan.staged_db.parent.mkdir(parents=True, exist_ok=True)
    with build_lock(plan.lock_path):
        cmd = builder_command(plan)
        result = subprocess.run(cmd, cwd=str(plan.repo_root), check=False)
        if result.returncode != 0:
            raise RunnerError(f"Builder failed with exit code {result.returncode}", exit_code=result.returncode)
        validation = validate_staged_artifacts(plan)
        promoted = False
        if plan.allow_production_write:
            promote_artifacts(plan)
            promoted = True
    return {
        **validation,
        "promoted": promoted,
        "final_db": str(plan.final_db),
        "final_manifest": str(plan.final_manifest),
        "final_jsonl": str(plan.final_jsonl),
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        plan = build_plan(args)
        validate_plan(plan)
        if not plan.allow_production_write and not plan.stage_only:
            print(json.dumps(plan_payload(plan, mode="plan"), indent=2, sort_keys=True))
            return 0
        result = run_build(plan)
        print(json.dumps({"mode": "build", **result}, indent=2, sort_keys=True))
        return 0
    except RunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
