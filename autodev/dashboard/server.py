"""Read-only AutoDev dashboard API and static UI server."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
except Exception as exc:  # pragma: no cover - exercised only when deps missing
    FastAPI = None  # type: ignore[assignment]
    HTTPException = RuntimeError  # type: ignore[assignment]

    def Query(default: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        _ = kwargs
        return default

    FileResponse = object  # type: ignore[assignment]
    HTMLResponse = object  # type: ignore[assignment]
    StaticFiles = object  # type: ignore[assignment]
    _FASTAPI_IMPORT_ERROR: Exception | None = exc
else:
    _FASTAPI_IMPORT_ERROR = None


RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z$")


def _repo_root(explicit_repo_root: Path | None = None) -> Path:
    if explicit_repo_root is not None:
        return explicit_repo_root.resolve()
    env_repo = os.getenv("AUTODEV_REPO_PATH", "").strip()
    if env_repo:
        return Path(env_repo).resolve()
    return Path(__file__).resolve().parents[2]


def _safe_under(base_dir: Path, requested_path: Path) -> Path:
    base = base_dir.resolve()
    candidate = requested_path.resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path is outside allowed directory.")
    return candidate


def _parse_kv_lines(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _load_json_safe(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _parse_report_task(report_path: Path) -> tuple[str | None, str | None]:
    if not report_path.exists():
        return None, None
    task_id: str | None = None
    task_title: str | None = None
    for line in report_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- task id:"):
            task_id = stripped.split("`")[1] if "`" in stripped else stripped.removeprefix("- task id:").strip()
        if stripped.startswith("- task title:"):
            task_title = stripped.removeprefix("- task title:").strip()
    return task_id, task_title


def _bool_or_none(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes", "on"}:
        return True
    if lowered in {"false", "0", "no", "off"}:
        return False
    return None


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    if value.strip().lower() in {"none", ""}:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _list_run_ids_desc(runs_root: Path) -> list[str]:
    if not runs_root.exists():
        return []
    run_ids: list[str] = []
    for entry in runs_root.iterdir():
        if entry.is_dir() and RUN_ID_RE.match(entry.name):
            run_ids.append(entry.name)
    return sorted(run_ids, reverse=True)


def _gate_logs(run_dir: Path) -> dict[str, dict[str, Any] | str]:
    logs_dir = run_dir / "logs"
    if not logs_dir.exists():
        return {}
    out: dict[str, dict[str, Any] | str] = {}
    for log_path in sorted(logs_dir.glob("gate_*.json")):
        raw = log_path.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            out[log_path.name] = raw
            continue
        out[log_path.name] = parsed if isinstance(parsed, dict) else raw
    return out


def _compute_run_duration(run_dir: Path) -> tuple[float, str | None]:
    total = 0.0
    started_values: list[str] = []
    for payload in _gate_logs(run_dir).values():
        if not isinstance(payload, dict):
            continue
        try:
            total += float(payload.get("duration_seconds", 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
        started = payload.get("started_at")
        if isinstance(started, str) and started.strip():
            started_values.append(started)
    started_at = min(started_values) if started_values else None
    return total, started_at


def _run_control_status(repo_root: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "autodev.runtime.control", "status"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    return proc.returncode, proc.stdout, proc.stderr


def create_app(repo_root: Path | None = None) -> "FastAPI":
    if _FASTAPI_IMPORT_ERROR is not None:
        raise RuntimeError(
            "FastAPI/uvicorn dependencies are missing. Install dashboard dependencies first."
        ) from _FASTAPI_IMPORT_ERROR

    root = _repo_root(repo_root)
    reports_root = root / "autodev" / "reports"
    runs_root = reports_root / "runs"
    experiments_root = reports_root / "experiments"
    static_root = root / "autodev" / "dashboard" / "static"

    app = FastAPI(title="AutoDev Dashboard", version="0.1.0")
    app.mount("/static", StaticFiles(directory=static_root), name="static")

    @app.get("/healthz")
    async def healthz() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/")
    async def root_page() -> HTMLResponse:
        index_path = _safe_under(static_root, static_root / "index.html")
        if not index_path.exists():
            raise HTTPException(status_code=500, detail="Dashboard index.html is missing.")
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    @app.get("/status")
    async def get_status() -> dict[str, Any]:
        code, stdout, stderr = _run_control_status(root)
        raw = _parse_kv_lines(stdout)
        daemon_running = _bool_or_none(raw.get("daemon_running"))
        pid = _int_or_none(raw.get("pid"))
        last_run_id = raw.get("last_run_id")
        if last_run_id and last_run_id.lower() == "none":
            last_run_id = None

        latest_task_id = raw.get("task_id")
        latest_task_title: str | None = None
        if last_run_id and RUN_ID_RE.match(last_run_id):
            run_dir = _safe_under(runs_root, runs_root / last_run_id)
            _, latest_task_title = _parse_report_task(run_dir / "report.md")

        return {
            "daemon_running": daemon_running,
            "pid": pid,
            "last_run_id": last_run_id,
            "last_result": raw.get("last_result"),
            "latest_task_id": latest_task_id,
            "latest_task_title": latest_task_title,
            "regression": raw.get("regression"),
            "debate_veto": raw.get("debate_veto"),
            "failure_reason": raw.get("failure_reason"),
            "control_exit_code": code,
            "control_stderr": stderr.strip() or None,
            "raw": raw,
        }

    @app.get("/runs")
    async def get_runs(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, list[dict[str, Any]]]:
        runs: list[dict[str, Any]] = []
        for run_id in _list_run_ids_desc(runs_root)[:limit]:
            run_dir = _safe_under(runs_root, runs_root / run_id)
            _, task_title = _parse_report_task(run_dir / "report.md")

            commands = _load_json_safe(run_dir / "commands.json") or {}
            gate_commands = commands.get("gate_commands", [])
            gates = "not_run"
            if isinstance(gate_commands, list) and gate_commands:
                passed_values = [bool(item.get("passed", False)) for item in gate_commands if isinstance(item, dict)]
                if passed_values:
                    gates = "pass" if all(passed_values) else "fail"

            worker_payload = _load_json_safe(run_dir / "worker.json") or {}
            worker = str(worker_payload.get("selected_worker", "")).strip() or "unknown"
            if worker == "unknown":
                worker_entries = commands.get("worker", [])
                if isinstance(worker_entries, list) and worker_entries and isinstance(worker_entries[0], dict):
                    worker = str(worker_entries[0].get("worker_name", "unknown"))

            duration_seconds, started_at = _compute_run_duration(run_dir)
            runs.append(
                {
                    "run_id": run_id,
                    "task": task_title,
                    "gates": gates,
                    "worker": worker,
                    "duration_seconds": duration_seconds,
                    "started_at": started_at,
                }
            )
        return {"runs": runs}

    @app.get("/run/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        if not RUN_ID_RE.match(run_id):
            raise HTTPException(status_code=400, detail="Invalid run_id format.")
        run_dir = _safe_under(runs_root, runs_root / run_id)
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail="Run not found.")

        report_path = _safe_under(run_dir, run_dir / "report.md")
        report_markdown = report_path.read_text(encoding="utf-8") if report_path.exists() else None
        commands = _load_json_safe(run_dir / "commands.json")
        worker = _load_json_safe(run_dir / "worker.json")
        gate_logs = _gate_logs(run_dir)

        return {
            "run_id": run_id,
            "report_markdown": report_markdown,
            "commands": commands,
            "worker": worker,
            "gate_logs": gate_logs,
        }

    @app.get("/experiments")
    async def get_experiments(limit: int = Query(default=20, ge=1, le=100)) -> dict[str, list[dict[str, Any]]]:
        if not experiments_root.exists():
            return {"experiments": []}

        results: list[dict[str, Any]] = []
        files = sorted([p for p in experiments_root.glob("*.json") if p.is_file()], reverse=True)
        for file_path in files[:limit]:
            payload = _load_json_safe(file_path) or {}
            raw_variants = payload.get("variants")
            if isinstance(raw_variants, list):
                variants: Any = len(raw_variants)
            else:
                variants = raw_variants
            generated_at = payload.get("generated_at")
            if not isinstance(generated_at, str) or not generated_at:
                generated_at = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc).isoformat()
            results.append(
                {
                    "file": file_path.name,
                    "task": payload.get("task"),
                    "variants": variants,
                    "winner": payload.get("winner"),
                    "benchmark_score": payload.get("benchmark_score"),
                    "generated_at": generated_at,
                }
            )
        return {"experiments": results}

    @app.get("/diff/{run_id}")
    async def get_diff(run_id: str) -> dict[str, str]:
        if not RUN_ID_RE.match(run_id):
            raise HTTPException(status_code=400, detail="Invalid run_id format.")

        run_patch = _safe_under(runs_root, runs_root / run_id / "pr_patch.diff")
        global_patch = _safe_under(root, root / "autodev_work" / "llm_patch.diff")

        chosen: Path | None = None
        if run_patch.exists():
            chosen = run_patch
        elif global_patch.exists():
            chosen = global_patch

        if chosen is None:
            raise HTTPException(status_code=404, detail="No diff artifact found.")

        return {
            "run_id": run_id,
            "source": str(chosen.relative_to(root)),
            "diff": chosen.read_text(encoding="utf-8", errors="replace"),
        }

    return app


if _FASTAPI_IMPORT_ERROR is None:
    app = create_app()
else:  # pragma: no cover - import-time fallback
    app = None


def main() -> int:
    if _FASTAPI_IMPORT_ERROR is not None:
        print("FastAPI/uvicorn dependencies are missing. Install requirements before running dashboard.")
        return 1

    try:
        import uvicorn
    except Exception:
        print("uvicorn is not installed. Install requirements before running dashboard.")
        return 1

    uvicorn.run("autodev.dashboard.server:app", host="127.0.0.1", port=8000, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
