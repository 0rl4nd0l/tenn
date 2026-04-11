#!/usr/bin/env python3
"""Local file-backed MLflow wrapper for real-gold extraction eval."""

from __future__ import annotations

import argparse
import hashlib
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
    parser.add_argument("--extractor-label", default="multipass_extraction")
    parser.add_argument("--provider-label", default=None)
    parser.add_argument("--method-label", default="run_multipass_extraction")
    parser.add_argument("--config-label", default=None)
    parser.add_argument(
        "--parser-backend",
        default=None,
        choices=["docling", "pymupdf"],
        help="Override the PDF parser backend (default: auto/docling).",
    )
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
    if args.extractor_label:
        command.extend(["--extractor-label", str(args.extractor_label)])
    if args.provider_label:
        command.extend(["--provider-label", str(args.provider_label)])
    if args.method_label:
        command.extend(["--method-label", str(args.method_label)])
    if args.model_label:
        command.extend(["--model-label", str(args.model_label)])
    if args.config_label:
        command.extend(["--config-label", str(args.config_label)])
    if args.parser_backend:
        command.extend(["--parser-backend", str(args.parser_backend)])
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


def _load_results(
    results_json: Path,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(results_json.read_text(encoding="utf-8"))
    return payload, payload.get("summary", {}), payload.get("documents", [])


def _dataset_fingerprint(dataset_dir: Path | None) -> str | None:
    if dataset_dir is None or not dataset_dir.exists():
        return None
    digest = hashlib.sha256()
    files = sorted(path for path in dataset_dir.glob("*.json") if path.is_file())
    if not files:
        return None
    for path in files:
        rel = path.relative_to(dataset_dir)
        digest.update(str(rel).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


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

    payload, summary, documents = _load_results(args.results_json)
    tracking_dir = args.tracking_dir.resolve()
    tracking_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(tracking_dir.as_uri())
    mlflow.set_experiment(args.experiment_name)

    run_name = args.run_name or datetime.now(timezone.utc).strftime(
        "real-gold-%Y%m%d-%H%M%S"
    )
    payload_run_metadata = (
        payload.get("run_metadata") if isinstance(payload.get("run_metadata"), dict) else {}
    )
    results_dataset_dir = payload.get("dataset_dir")
    dataset_dir = args.dataset_dir
    if dataset_dir is None and isinstance(results_dataset_dir, str) and results_dataset_dir:
        dataset_dir = Path(results_dataset_dir)
    artifact_paths = (
        payload.get("artifact_paths") if isinstance(payload.get("artifact_paths"), dict) else {}
    )
    params = {
        "dataset_dir": str(dataset_dir) if dataset_dir is not None else "default",
        "results_json": str(args.results_json),
        "report_path": str(args.report_path),
        "limit": args.limit,
        "tolerance": args.tolerance,
        "mode": "reuse-existing" if args.reuse_existing else "execute",
        "extractor_label": args.extractor_label
        or payload_run_metadata.get("extractor_label")
        or "unknown",
        "provider_label": args.provider_label
        or payload_run_metadata.get("provider_label")
        or "unspecified",
        "method_label": args.method_label
        or payload_run_metadata.get("method_label")
        or "unknown",
        "config_label": args.config_label
        or payload_run_metadata.get("config_label")
        or "unspecified",
        "parser_backend": args.parser_backend
        or payload_run_metadata.get("parser_backend")
        or "auto",
    }
    if args.model_label:
        params["model_label"] = args.model_label
    elif payload_run_metadata.get("model_label"):
        params["model_label"] = str(payload_run_metadata["model_label"])
    if args.profile_label:
        params["profile_label"] = args.profile_label
    if summary.get("generated_at"):
        params["run_timestamp"] = str(summary["generated_at"])
    dataset_fingerprint = _dataset_fingerprint(dataset_dir)
    if dataset_fingerprint is not None:
        params["dataset_fingerprint"] = dataset_fingerprint
    commit_hash = _git_value("rev-parse", "HEAD")
    if commit_hash is not None:
        params["commit_hash"] = commit_hash
    dirty = _git_value("status", "--short")
    params["worktree_dirty"] = "true" if dirty else "false"
    for artifact_name, artifact_path in sorted(artifact_paths.items()):
        params[f"artifact_{artifact_name}_path"] = str(artifact_path)

    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params)
        mlflow.log_metric("overall_accuracy", float(summary.get("total_accuracy", 0.0)))
        mlflow.log_metric(
            "context_accuracy", float(summary.get("context_accuracy", 0.0))
        )
        mlflow.log_metric("document_count", float(summary.get("total_documents", 0)))
        mlflow.log_metric(
            "failed_document_count", float(summary.get("failed_documents", 0))
        )
        mlflow.log_metric(
            "metric_check_count", float(summary.get("total_metric_checks", 0))
        )
        mlflow.log_metric(
            "context_mismatch_document_count",
            float(summary.get("context_mismatch_documents", 0)),
        )
        mlflow.log_metric(
            "context_mismatch_field_count",
            float(summary.get("context_mismatch_fields", 0)),
        )
        mlflow.log_metric(
            "trust_matches_expected_count",
            float(summary.get("trust_matches_expected", 0)),
        )
        mlflow.log_metric(
            "trust_mismatches_expected_count",
            float(summary.get("trust_mismatches_expected", 0)),
        )
        for trust_key, count in summary.get("trust_distribution", {}).items():
            mlflow.log_metric(f"trust_{trust_key}_count", float(count))
        for metric_status, count in summary.get("metric_status_counts", {}).items():
            mlflow.log_metric(f"metric_status_{metric_status}_count", float(count))
        for metric_name, accuracy in _per_metric_accuracy(documents).items():
            mlflow.log_metric(f"metric_{metric_name}_accuracy", float(accuracy))
        for trigger, count in summary.get("trust_trigger_counts", {}).items():
            safe_trigger = trigger.replace(":", "_").replace("-", "_")
            mlflow.log_metric(f"trust_trigger_{safe_trigger}_count", float(count))
        logged_paths = {Path(args.results_json).resolve(), Path(args.report_path).resolve()}
        mlflow.log_artifact(str(args.results_json), artifact_path="eval")
        mlflow.log_artifact(str(args.report_path), artifact_path="eval")
        for artifact_path in artifact_paths.values():
            path = Path(str(artifact_path))
            if not path.exists():
                continue
            resolved = path.resolve()
            if resolved in logged_paths:
                continue
            mlflow.log_artifact(str(path), artifact_path="eval")
            logged_paths.add(resolved)
        print(f"MLflow run logged: {run.info.run_id}")
        print(f"Tracking URI: {tracking_dir.as_uri()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
