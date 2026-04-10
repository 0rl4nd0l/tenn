#!/usr/bin/env python3
"""Local file-backed MLflow wrapper for real-gold extraction eval."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
EVAL_SCRIPT = REPO_ROOT / "scripts" / "run_real_extraction_eval.py"
DEFAULT_RESULTS_JSON = REPO_ROOT / "reports" / "extraction_real_eval_results.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "extraction_real_eval_summary.md"
DEFAULT_TRACKING_DIR = REPO_ROOT / "mlruns"


def _require_mlflow() -> Any:
    try:
        import mlflow
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "mlflow is not installed. Install dev-only eval deps with "
            "`financial-engine_v2/.venv/bin/pip install -r financial-engine_v2/backend/requirements-dev.txt`."
        ) from exc
    return mlflow


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track real-gold extraction eval runs in local file-backed MLflow.",
    )
    parser.add_argument("--dataset-dir", type=Path, default=None)
    parser.add_argument("--results-json", type=Path, default=DEFAULT_RESULTS_JSON)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument("--tracking-dir", type=Path, default=DEFAULT_TRACKING_DIR)
    parser.add_argument(
        "--experiment-name",
        default="extraction-real-gold-eval",
        help="MLflow experiment name.",
    )
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--model-label", default=None)
    parser.add_argument("--profile-label", default=None)
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Log existing eval artifacts instead of running the eval command.",
    )
    return parser.parse_args()


def _run_eval(args: argparse.Namespace) -> None:
    if args.reuse_existing:
        return
    command = [
        sys.executable,
        str(EVAL_SCRIPT),
        "--results-json",
        str(args.results_json),
        "--report-path",
        str(args.report_path),
        "--limit",
        str(args.limit),
        "--tolerance",
        str(args.tolerance),
    ]
    if args.dataset_dir is not None:
        command.extend(["--dataset-dir", str(args.dataset_dir)])
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def _git_value(*command: str) -> str | None:
    proc = subprocess.run(
        ["git", *command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


def _load_results(results_json: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(results_json.read_text(encoding="utf-8"))
    return payload.get("summary", {}), payload.get("documents", [])


def _per_metric_accuracy(documents: list[dict[str, Any]]) -> dict[str, float]:
    counts: dict[str, dict[str, int]] = {}
    for document in documents:
        for metric_name, metric_result in document.get("metric_results", {}).items():
            bucket = counts.setdefault(metric_name, {"correct": 0, "total": 0})
            bucket["total"] += 1
            if metric_result.get("status") == "correct":
                bucket["correct"] += 1
    return {
        metric_name: bucket["correct"] / bucket["total"]
        for metric_name, bucket in counts.items()
        if bucket["total"]
    }


def main() -> int:
    args = _parse_args()
    mlflow = _require_mlflow()
    _run_eval(args)

    if not args.results_json.exists() or not args.report_path.exists():
        raise SystemExit("expected eval artifacts were not found after run")

    summary, documents = _load_results(args.results_json)
    tracking_dir = args.tracking_dir.resolve()
    tracking_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(tracking_dir.as_uri())
    mlflow.set_experiment(args.experiment_name)

    run_name = args.run_name or datetime.now(timezone.utc).strftime(
        "real-gold-%Y%m%d-%H%M%S"
    )
    params = {
        "dataset_dir": str(args.dataset_dir)
        if args.dataset_dir is not None
        else "default",
        "results_json": str(args.results_json),
        "report_path": str(args.report_path),
        "limit": args.limit,
        "tolerance": args.tolerance,
        "mode": "reuse-existing" if args.reuse_existing else "execute",
    }
    if args.model_label:
        params["model_label"] = args.model_label
    if args.profile_label:
        params["profile_label"] = args.profile_label
    commit_hash = _git_value("rev-parse", "HEAD")
    if commit_hash is not None:
        params["commit_hash"] = commit_hash
    dirty = _git_value("status", "--short")
    params["worktree_dirty"] = "true" if dirty else "false"

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params)
        mlflow.log_metric("overall_accuracy", float(summary.get("total_accuracy", 0.0)))
        mlflow.log_metric(
            "context_accuracy", float(summary.get("context_accuracy", 0.0))
        )
        mlflow.log_metric("document_count", float(summary.get("total_documents", 0)))
        mlflow.log_metric(
            "metric_check_count", float(summary.get("total_metric_checks", 0))
        )
        for trust_key, count in summary.get("trust_distribution", {}).items():
            mlflow.log_metric(f"trust_{trust_key}_count", float(count))
        for metric_name, accuracy in _per_metric_accuracy(documents).items():
            mlflow.log_metric(f"metric_{metric_name}_accuracy", float(accuracy))
        mlflow.log_artifact(str(args.results_json), artifact_path="eval")
        mlflow.log_artifact(str(args.report_path), artifact_path="eval")
        print(f"MLflow run logged: {run.info.run_id}")
        print(f"Tracking URI: {tracking_dir.as_uri()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
