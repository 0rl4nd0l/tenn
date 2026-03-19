"""Safe control CLI for autodev orchestration."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
from typing import Any

from autodev.runtime import autodev_loop
from autodev.runtime.config import AutoDevConfig, load_config
from autodev.runtime.repo_rag import index_repository
from autodev.runtime.task_discovery import append_tasks_to_queue, mark_discovery_run, scan_repo


RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z$")


def _reports_root(config: AutoDevConfig) -> Path:
    return config.repo_path / "autodev" / "reports"


def _runs_root(config: AutoDevConfig) -> Path:
    return _reports_root(config) / "runs"


def _pid_file(config: AutoDevConfig) -> Path:
    return _reports_root(config) / "autodev.pid"


def _daemon_log_file(config: AutoDevConfig) -> Path:
    return _reports_root(config) / "daemon.log"


def safe_path_under(base_dir: Path, requested_path: Path) -> Path:
    base = base_dir.resolve()
    candidate = requested_path.resolve()
    if not str(candidate).startswith(str(base)):
        raise ValueError(f"Path '{requested_path}' is outside allowed directory '{base_dir}'.")
    return candidate


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _discover_run_dirs(config: AutoDevConfig) -> list[Path]:
    root = _runs_root(config)
    if not root.exists():
        return []
    runs: list[Path] = []
    for entry in root.iterdir():
        if entry.is_dir() and RUN_ID_RE.match(entry.name):
            runs.append(entry)
    return sorted(runs, key=lambda p: p.name, reverse=True)


def _latest_run_dir(config: AutoDevConfig) -> Path | None:
    runs = _discover_run_dirs(config)
    return runs[0] if runs else None


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _parse_report_task(report_path: Path) -> tuple[str, str]:
    if not report_path.exists():
        return ("unknown", "unknown")
    task_id = "unknown"
    task_title = "unknown"
    for line in report_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- task id:"):
            task_id = stripped.split("`")[1] if "`" in stripped else stripped.removeprefix("- task id:").strip()
        if stripped.startswith("- task title:"):
            task_title = stripped.removeprefix("- task title:").strip()
    return task_id, task_title


def summarize_run(run_dir: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "run_id": run_dir.name,
        "task_id": "unknown",
        "task_title": "unknown",
        "gate_outcome": "not_run",
        "worker_status": "unknown",
        "regression_decision": "unknown",
        "debate_veto": "none",
        "primary_failure_reason": "unknown",
    }
    report = run_dir / "report.md"
    task_id, task_title = _parse_report_task(report)
    summary["task_id"] = task_id
    summary["task_title"] = task_title

    commands = _load_json(run_dir / "commands.json") or {}
    gate_commands = commands.get("gate_commands", [])
    if isinstance(gate_commands, list) and gate_commands:
        if all(bool(item.get("passed", False)) for item in gate_commands if isinstance(item, dict)):
            summary["gate_outcome"] = "pass"
        else:
            summary["gate_outcome"] = "fail"
        first_fail = next(
            (item for item in gate_commands if isinstance(item, dict) and not bool(item.get("passed", False))),
            None,
        )
        if isinstance(first_fail, dict):
            summary["primary_failure_reason"] = str(first_fail.get("failure_reason", "gate_failed"))

    worker_json = _load_json(run_dir / "worker.json") or {}
    worker_result = worker_json.get("result", {})
    if isinstance(worker_result, dict):
        summary["worker_status"] = str(worker_result.get("status", "unknown"))

    regression = _load_json(run_dir / "regression.json") or {}
    if regression:
        summary["regression_decision"] = str(regression.get("decision", "unknown"))
        if summary["primary_failure_reason"] == "unknown" and not bool(regression.get("passed", False)):
            summary["primary_failure_reason"] = f"regression:{summary['regression_decision']}"

    debate_pre = _load_json(run_dir / "debate_pre.json") or {}
    debate_post = _load_json(run_dir / "debate_post.json") or {}
    pre_veto = bool((debate_pre.get("meta") or {}).get("veto", False))
    post_veto = bool((debate_post.get("meta") or {}).get("veto", False))
    if pre_veto:
        summary["debate_veto"] = f"pre:{(debate_pre.get('meta') or {}).get('veto_role', 'unknown')}"
    elif post_veto:
        summary["debate_veto"] = f"post:{(debate_post.get('meta') or {}).get('veto_role', 'unknown')}"

    return summary


def _read_pid(config: AutoDevConfig) -> int | None:
    path = _pid_file(config)
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _write_pid(config: AutoDevConfig, pid: int) -> None:
    path = _pid_file(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid) + "\n", encoding="utf-8")


def _remove_pid(config: AutoDevConfig) -> None:
    path = _pid_file(config)
    if path.exists():
        path.unlink()


def cmd_status(config: AutoDevConfig) -> int:
    pid = _read_pid(config)
    stale_pid_removed = False
    if pid is not None and not _process_alive(pid):
        _remove_pid(config)
        pid = None
        stale_pid_removed = True
    running = pid is not None
    latest = _latest_run_dir(config)
    print(f"daemon_running={running}")
    print(f"pid={pid if pid is not None else 'none'}")
    if stale_pid_removed:
        print("stale_pid_removed=true")
    if latest:
        summary = summarize_run(latest)
        print(f"last_run_id={summary['run_id']}")
        print(f"last_result={summary['gate_outcome']}")
        print(f"task_id={summary['task_id']}")
        print(f"regression={summary['regression_decision']}")
        print(f"debate_veto={summary['debate_veto']}")
        print(f"failure_reason={summary['primary_failure_reason']}")
    else:
        print("last_run_id=none")
        print("last_result=unknown")
    return 0


def cmd_run_once(config: AutoDevConfig) -> int:
    return autodev_loop.run_once(config)


def cmd_discover(config: AutoDevConfig) -> int:
    tasks = scan_repo(config.repo_path)
    added = append_tasks_to_queue(config.repo_path, tasks)
    mark_discovery_run(repo_path=config.repo_path)
    print(f"Discovered {added} new tasks")
    print("Added to TASKS.md")
    return 0


def cmd_rag_index(config: AutoDevConfig) -> int:
    payload = index_repository(config.repo_path)
    index_path = config.repo_path / "autodev" / "cache" / "repo_index.json"
    count = int(payload.get("indexed_file_count", 0))
    print(f"Indexed {count} files")
    print(f"index={index_path}")
    return 0


def cmd_start(config: AutoDevConfig) -> int:
    existing = _read_pid(config)
    if existing is not None and _process_alive(existing):
        print(f"daemon already running (pid={existing})")
        return 0
    reports_dir = _reports_root(config)
    reports_dir.mkdir(parents=True, exist_ok=True)
    log_path = _daemon_log_file(config)
    log_path.touch(exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("Starting AutoDev daemon\n")
    log_file = open(log_path, "a", buffering=1, encoding="utf-8")
    try:
        daemon_env = dict(os.environ)
        daemon_env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            [config.python_bin, "-m", "autodev.runtime.autodev_loop", "--daemon"],
            cwd=config.repo_path,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
            env=daemon_env,
        )
    finally:
        log_file.close()
    _write_pid(config, proc.pid)
    print(f"daemon started pid={proc.pid}")
    print(f"log={log_path}")
    return 0


def cmd_stop(config: AutoDevConfig) -> int:
    pid_path = _pid_file(config)
    if not pid_path.exists():
        print("daemon not running (no pid file)")
        return 0
    pid = _read_pid(config)
    if pid is None:
        _remove_pid(config)
        print("daemon not running (invalid pid file removed)")
        return 0
    if not _process_alive(pid):
        _remove_pid(config)
        print("daemon not running (stale pid removed)")
        return 0
    os.kill(pid, signal.SIGTERM)
    _remove_pid(config)
    print(f"daemon stop signal sent pid={pid}")
    return 0


def cmd_latest_report(config: AutoDevConfig) -> int:
    latest = _latest_run_dir(config)
    if not latest:
        print("no runs found")
        return 0
    summary = summarize_run(latest)
    print(f"run_dir={latest}")
    print(f"run_id={summary['run_id']}")
    print(f"task={summary['task_id']} {summary['task_title']}")
    print(f"gates={summary['gate_outcome']}")
    print(f"worker={summary['worker_status']}")
    print(f"regression={summary['regression_decision']}")
    print(f"debate_veto={summary['debate_veto']}")
    print(f"failure_reason={summary['primary_failure_reason']}")
    return 0


def cmd_list_runs(config: AutoDevConfig, n: int) -> int:
    runs = _discover_run_dirs(config)[: max(0, n)]
    for run_dir in runs:
        summary = summarize_run(run_dir)
        print(
            f"{summary['run_id']} task={summary['task_id']} "
            f"gates={summary['gate_outcome']} "
            f"regression={summary['regression_decision']} "
            f"debate={summary['debate_veto']}"
        )
    return 0


def _tail_lines(path: Path, count: int = 200) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-count:]


def _resolve_tail_path(config: AutoDevConfig, run_dir: Path, file_key: str) -> Path:
    if file_key == "report":
        return run_dir / "report.md"
    if file_key == "worker":
        worker_log = run_dir / "worker.log"
        return worker_log if worker_log.exists() else (run_dir / "worker.json")
    if file_key == "commands":
        return run_dir / "commands.json"
    if file_key == "gates":
        logs_dir = run_dir / "logs"
        if not logs_dir.exists():
            raise FileNotFoundError("No gate logs directory for selected run.")
        candidates = [p for p in logs_dir.iterdir() if p.is_file() and p.suffix == ".json"]
        if not candidates:
            raise FileNotFoundError("No gate log files for selected run.")
        return sorted(candidates, key=lambda p: p.name)[-1]
    raise ValueError(f"Unsupported --file value: {file_key}")


def cmd_tail(config: AutoDevConfig, run_id: str | None, file_key: str) -> int:
    runs_root = _runs_root(config)
    if run_id:
        if not RUN_ID_RE.match(run_id):
            raise ValueError("Invalid run id format.")
        run_dir = safe_path_under(runs_root, runs_root / run_id)
    else:
        latest = _latest_run_dir(config)
        if latest is None:
            print("no runs found")
            return 0
        run_dir = latest
    path = _resolve_tail_path(config, run_dir, file_key)
    safe = safe_path_under(config.repo_path / "autodev" / "reports", path)
    if not safe.exists():
        raise FileNotFoundError(f"Artifact not found: {safe}")
    print(f"file={safe}")
    for line in _tail_lines(safe, count=200):
        print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe control adapter for autodev.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("run-once")
    sub.add_parser("discover")
    sub.add_parser("rag-index")
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("latest-report")
    list_runs = sub.add_parser("list-runs")
    list_runs.add_argument("--n", type=int, default=10)
    tail = sub.add_parser("tail")
    tail.add_argument("--run", dest="run_id", default=None)
    tail.add_argument("--file", choices=["report", "worker", "gates", "commands"], default="report")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()
    if args.command == "status":
        return cmd_status(config)
    if args.command == "run-once":
        return cmd_run_once(config)
    if args.command == "discover":
        return cmd_discover(config)
    if args.command == "rag-index":
        return cmd_rag_index(config)
    if args.command == "start":
        return cmd_start(config)
    if args.command == "stop":
        return cmd_stop(config)
    if args.command == "latest-report":
        return cmd_latest_report(config)
    if args.command == "list-runs":
        return cmd_list_runs(config, n=args.n)
    if args.command == "tail":
        return cmd_tail(config, run_id=args.run_id, file_key=args.file)
    raise RuntimeError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
