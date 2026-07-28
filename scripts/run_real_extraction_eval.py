#!/usr/bin/env python3
"""Run the real ASX extraction eval through the backend-owned endpoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest


REPO_ROOT = Path(__file__).resolve().parents[1]
FINANCIAL_ENGINE_ROOT = REPO_ROOT / "financial-engine_v2"
BACKEND_ROOT = FINANCIAL_ENGINE_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.asx_holdout_confidentiality import DevelopmentAggregateResult
from app.services.method_isolated_extraction import normalize_extraction_method


DEFAULT_DATASET_DIR = FINANCIAL_ENGINE_ROOT / "data" / "extraction_gold_real"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "extraction_real_eval_summary.md"
DEFAULT_RESULTS_JSON = REPO_ROOT / "reports" / "extraction_real_eval_results.json"
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 1800.0
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
SUPPORTED_METRICS = ("revenue", "operating_cash_flow", "net_debt")
EVAL_POLICY_VERSION = "2026-04-20"
CANONICAL_METHOD = "docling"
CANONICAL_STRICT_METHOD = True
CANONICAL_LIMIT = 0
CANONICAL_TOLERANCE = 0.01


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the backend real-gold extraction eval and persist report artifacts.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Canonical real-gold dataset directory (must match backend corpus path).",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--results-json",
        type=Path,
        default=DEFAULT_RESULTS_JSON,
        help="Detailed JSON results output path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of documents to run (0 = all).",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.01,
        help="Relative numeric tolerance for metric comparisons.",
    )
    parser.add_argument("--extractor-label", default="backend_real_gold_eval")
    parser.add_argument("--provider-label", default="backend_api")
    parser.add_argument("--method-label", default="/api/extraction-eval/real-gold")
    parser.add_argument("--model-label", default=None)
    parser.add_argument("--config-label", default=None)
    parser.add_argument(
        "--parser-backend",
        default=CANONICAL_METHOD,
        choices=["docling", "pymupdf", "anthropic"],
        help="Request a specific backend extraction method (default: docling).",
    )
    parser.add_argument(
        "--strict-method",
        dest="strict_method",
        action="store_true",
        default=CANONICAL_STRICT_METHOD,
        help="Require the requested extraction method without backend fallback (default: true).",
    )
    parser.add_argument(
        "--allow-fallback",
        dest="strict_method",
        action="store_false",
        help=(
            "Allow backend fallback to other parser methods. "
            "This marks the run non-canonical for KPI reporting."
        ),
    )
    parser.add_argument(
        "--backend-url",
        default=DEFAULT_BACKEND_URL,
        help="Backend base URL hosting /api/extraction-eval/real-gold.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional backend API key override for X-API-Key.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout for the backend eval request.",
    )
    parser.add_argument(
        "--corpus-classification",
        choices=["non_holdout", "holdout"],
        required=True,
    )
    parser.add_argument(
        "--access-mode",
        choices=["development", "protected"],
        required=True,
    )
    parser.add_argument("--development-aggregate-json", type=Path, default=None)
    return parser.parse_args()


def _canonical_dataset_dir() -> Path:
    return DEFAULT_DATASET_DIR.resolve()


def _validate_dataset_dir(dataset_dir: Path) -> Path:
    requested = dataset_dir.resolve()
    canonical = _canonical_dataset_dir()
    if requested != canonical:
        raise ValueError(
            "run_real_extraction_eval.py now wraps the backend-owned real-gold "
            f"endpoint and only supports the canonical dataset dir: {canonical}"
        )
    return canonical


def _normalize_backend_url(raw_url: str) -> str:
    return str(raw_url or DEFAULT_BACKEND_URL).strip().rstrip("/")


def _compute_fixture_content_sha256(dataset_dir: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(path for path in dataset_dir.glob("*.json") if path.is_file())
    for path in files:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _resolve_fixture_git_commit(dataset_dir: Path) -> str | None:
    try:
        rel_path = dataset_dir.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None

    try:
        proc = subprocess.run(
            ["git", "log", "-n", "1", "--format=%H", "--", str(rel_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    commit = proc.stdout.strip()
    return commit or None


def _resolve_fixture_git_dirty(dataset_dir: Path) -> bool | None:
    try:
        rel_path = dataset_dir.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain", "--", str(rel_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return bool(proc.stdout.strip())


def _build_fixture_manifest(dataset_dir: Path) -> dict[str, Any]:
    files = sorted(path for path in dataset_dir.glob("*.json") if path.is_file())
    return {
        "dataset_dir": str(dataset_dir.resolve()),
        "fixture_file_count": len(files),
        "fixture_content_sha256": _compute_fixture_content_sha256(dataset_dir),
        "fixture_git_commit": _resolve_fixture_git_commit(dataset_dir),
        "fixture_git_dirty": _resolve_fixture_git_dirty(dataset_dir),
    }


def _resolve_backend_api_key(arg_value: str | None) -> str | None:
    for candidate in (
        arg_value,
        str(getattr(settings, "local_api_key", "") or "").strip(),
        os.environ.get("LOCAL_API_KEY"),
        os.environ.get("BACKEND_API_KEY"),
    ):
        value = str(candidate or "").strip()
        if value:
            return value
    return None


def _http_json(
    request: urlrequest.Request, *, per_call_timeout: float, error_label: str
) -> dict[str, Any]:
    """Issue a single HTTP call and return the decoded JSON object body."""

    try:
        with urlrequest.urlopen(request, timeout=max(per_call_timeout, 1.0)) as resp:
            response_body = resp.read().decode("utf-8")
    except urlerror.HTTPError as exc:
        detail = ""
        try:
            body_text = exc.read().decode("utf-8")
            parsed = json.loads(body_text)
            if isinstance(parsed, dict):
                detail = str(parsed.get("detail") or body_text).strip()
            else:
                detail = body_text.strip()
        except Exception:
            detail = str(exc.reason or "").strip()
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"{error_label} failed (HTTP {exc.code}){suffix}") from exc
    except (urlerror.URLError, TimeoutError) as exc:
        raise RuntimeError(f"{error_label} request failed: {exc}") from exc

    try:
        decoded = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{error_label} returned non-JSON output") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError(f"{error_label} returned a non-object payload")
    return decoded


def _build_json_request(
    url: str, *, method: str, api_key: str | None, body: dict[str, Any] | None = None
) -> urlrequest.Request:
    headers = {"Accept": "application/json"}
    data: bytes | None = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if api_key:
        headers["X-API-Key"] = api_key
    return urlrequest.Request(url, data=data, headers=headers, method=method)


def _request_real_gold_eval(
    *,
    backend_url: str,
    api_key: str | None,
    limit: int,
    tolerance: float,
    method: str,
    strict_method: bool,
    timeout_seconds: float,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    corpus_classification: str = "non_holdout",
    access_mode: str = "development",
    development_aggregate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Schedule a background real-gold job and poll until it terminates."""

    body = {
        "limit": max(int(limit), 0),
        "tolerance": max(float(tolerance), 0.0),
        "method": normalize_extraction_method(method),
        "strict_method": bool(strict_method),
    }
    if corpus_classification is not None:
        body["corpus_classification"] = corpus_classification
    if access_mode is not None:
        body["access_mode"] = access_mode
    if development_aggregate is not None:
        body["development_aggregate"] = development_aggregate
    per_call_timeout = max(min(float(timeout_seconds), 60.0), 1.0)
    poll_interval = max(float(poll_interval_seconds), 0.1)

    schedule_request = _build_json_request(
        f"{backend_url}/api/extraction-eval/real-gold?background=true",
        method="POST",
        api_key=api_key,
        body=body,
    )
    scheduled = _http_json(
        schedule_request,
        per_call_timeout=per_call_timeout,
        error_label="backend real-gold job",
    )
    task_id = scheduled.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        raise RuntimeError("backend real-gold job schedule response missing task_id")

    deadline = time.monotonic() + max(float(timeout_seconds), 1.0)
    status_url = f"{backend_url}/api/extraction-eval/real-gold/tasks/{task_id}"
    while True:
        status_request = _build_json_request(status_url, method="GET", api_key=api_key)
        status = _http_json(
            status_request,
            per_call_timeout=per_call_timeout,
            error_label="backend real-gold job status",
        )
        state = str(status.get("status") or "").strip().lower()
        if state == "completed":
            result = status.get("result")
            if not isinstance(result, dict):
                raise RuntimeError(
                    "backend real-gold job completed without result payload"
                )
            aggregate = _development_aggregate(result)
            if aggregate is not None:
                return aggregate
            if not isinstance(result.get("summary"), dict):
                raise RuntimeError("backend real-gold job payload is missing summary")
            if not isinstance(result.get("documents"), list):
                raise RuntimeError("backend real-gold job payload is missing documents")
            return result
        if state == "failed":
            error_text = str(status.get("error") or "").strip() or "unknown error"
            raise RuntimeError(f"backend real-gold job failed: {error_text}")
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"backend real-gold job timed out after {timeout_seconds:.0f}s "
                f"(task_id={task_id}, last_status={state or 'unknown'})"
            )
        time.sleep(poll_interval)


def _canonical_contract(dataset_dir: Path) -> dict[str, Any]:
    return {
        "dataset_dir": str(dataset_dir.resolve()),
        "method": CANONICAL_METHOD,
        "strict_method": CANONICAL_STRICT_METHOD,
        "limit": CANONICAL_LIMIT,
        "tolerance": CANONICAL_TOLERANCE,
        "prompt_variant_id": None,
        "model_override": None,
    }


def _resolve_eval_policy(
    response_payload: dict[str, Any],
    *,
    dataset_dir: Path,
    requested_method: str,
    strict_method: bool,
    limit: int,
    tolerance: float,
) -> dict[str, Any]:
    policy = response_payload.get("eval_policy")
    if isinstance(policy, dict):
        return policy

    canonical_contract = _canonical_contract(dataset_dir)
    actual_run = {
        "dataset_dir": str(dataset_dir.resolve()),
        "method": requested_method,
        "strict_method": bool(strict_method),
        "limit": max(int(limit), 0),
        "tolerance": round(max(float(tolerance), 0.0), 8),
        "prompt_variant_id": None,
        "model_override": None,
    }
    non_canonical_reasons: list[str] = []
    for key, expected in canonical_contract.items():
        if actual_run.get(key) != expected:
            non_canonical_reasons.append(
                f"{key}:expected={expected!r},actual={actual_run.get(key)!r}"
            )

    mode = "canonical" if not non_canonical_reasons else "non_canonical"
    return {
        "policy_version": EVAL_POLICY_VERSION,
        "mode": mode,
        "kpi_eligible": mode == "canonical",
        "non_canonical_reasons": non_canonical_reasons,
        "canonical_contract": canonical_contract,
        "actual_run": actual_run,
    }


def _fixture_provenance_non_canonical_reasons(
    fixture_manifest: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    fixture_commit = str(fixture_manifest.get("fixture_git_commit") or "").strip()
    if not fixture_commit:
        reasons.append("fixture_provenance:fixture_git_commit_missing")
    fixture_dirty = fixture_manifest.get("fixture_git_dirty")
    if fixture_dirty is not False:
        reasons.append(
            f"fixture_provenance:fixture_git_dirty_not_false:{fixture_dirty!r}"
        )
    return reasons


def _apply_fixture_provenance_guard(
    eval_policy: dict[str, Any],
    fixture_manifest: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(eval_policy)
    reasons = list(merged.get("non_canonical_reasons") or [])
    for reason in _fixture_provenance_non_canonical_reasons(fixture_manifest):
        if reason not in reasons:
            reasons.append(reason)
    if reasons:
        merged["mode"] = "non_canonical"
        merged["kpi_eligible"] = False
    merged["non_canonical_reasons"] = reasons
    return merged


def _build_canonical_scorecard(
    *,
    summary: dict[str, Any],
    eval_policy: dict[str, Any],
    fixture_manifest: dict[str, Any],
) -> dict[str, Any]:
    kpi_eligible = bool(eval_policy.get("kpi_eligible"))
    canonical_summary = summary if kpi_eligible else None
    exploratory_summary = summary if not kpi_eligible else None
    return {
        "generated_at": summary.get("generated_at"),
        "policy_version": eval_policy.get("policy_version"),
        "evaluation_mode": eval_policy.get("mode"),
        "kpi_eligible": kpi_eligible,
        "non_canonical_reasons": list(eval_policy.get("non_canonical_reasons") or []),
        "canonical_contract": dict(eval_policy.get("canonical_contract") or {}),
        "actual_run": dict(eval_policy.get("actual_run") or {}),
        "fixture_manifest": fixture_manifest,
        "canonical_kpi_summary": canonical_summary,
        "exploratory_summary": exploratory_summary,
    }


def _build_report_markdown(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    dataset_dir: str,
    eval_policy: dict[str, Any],
    fixture_manifest: dict[str, Any],
    artifact_paths: dict[str, str],
) -> str:
    lines: list[str] = []
    lines.append("# Extraction Real Eval Summary")
    lines.append("")
    lines.append(f"- Generated: {summary['generated_at']}")
    lines.append(f"- Dataset: `{dataset_dir}`")
    lines.append(f"- Documents: {summary['total_documents']}")
    lines.append(f"- Eval mode: `{eval_policy.get('mode')}`")
    lines.append(
        f"- KPI eligible: {'yes' if eval_policy.get('kpi_eligible') else 'no'}"
    )
    lines.append("")
    if not eval_policy.get("kpi_eligible"):
        lines.append(
            "> This run is marked non-canonical and excluded from canonical KPI reporting."
        )
        lines.append("")
    lines.append("## Eval Policy")
    lines.append("")
    lines.append(f"- Policy version: `{eval_policy.get('policy_version')}`")
    lines.append(f"- Dataset commit: `{fixture_manifest.get('fixture_git_commit')}`")
    lines.append(
        f"- Dataset content hash: `{fixture_manifest.get('fixture_content_sha256')}`"
    )
    lines.append(f"- Dataset dirty: `{fixture_manifest.get('fixture_git_dirty')}`")
    non_canonical_reasons = eval_policy.get("non_canonical_reasons") or []
    if non_canonical_reasons:
        lines.append("- Non-canonical reasons:")
        for reason in non_canonical_reasons:
            lines.append(f"  - `{reason}`")
    lines.append("")
    lines.append("## Total Accuracy")
    lines.append("")
    lines.append(
        "- Metric accuracy: "
        f"{summary['total_accuracy'] * 100:.2f}% "
        f"({summary['metric_status_counts'].get('correct', 0)}/"
        f"{summary['total_metric_checks']})"
    )
    lines.append(
        "- Context accuracy: "
        f"{summary['context_accuracy'] * 100:.2f}% "
        f"({summary['context_correct_documents']}/{summary['total_documents']})"
    )
    lines.append(
        "- Trust matches expected: "
        f"{summary['trust_matches_expected']}/{summary['total_documents']}"
    )
    lines.append("")
    lines.append("## Artifact Outputs")
    lines.append("")
    lines.append("| Artifact | Path |")
    lines.append("| --- | --- |")
    for artifact_name, artifact_path in sorted(artifact_paths.items()):
        lines.append(f"| {artifact_name} | `{artifact_path}` |")
    lines.append("")
    lines.append("## Trust Distribution")
    lines.append("")
    lines.append("| Trust outcome | Count |")
    lines.append("| --- | ---: |")
    for trust in ("trusted", "abstain", "quarantine"):
        lines.append(f"| {trust} | {summary['trust_distribution'].get(trust, 0)} |")
    lines.append("")
    lines.append("## Trust Trigger Summary")
    lines.append("")
    lines.append("| Trigger | Count |")
    lines.append("| --- | ---: |")
    trust_trigger_counts = summary.get("trust_trigger_counts", {})
    if trust_trigger_counts:
        for trigger, count in trust_trigger_counts.items():
            lines.append(f"| {trigger} | {count} |")
    else:
        lines.append("| - | 0 |")
    lines.append("")
    lines.append("## Per-Metric Failure Counts")
    lines.append("")
    lines.append("| Metric | Wrong | Missing | Abstain |")
    lines.append("| --- | ---: | ---: | ---: |")
    for metric in SUPPORTED_METRICS:
        counts = summary["per_metric_failure_counts"].get(
            metric,
            {"wrong": 0, "missing": 0, "abstain": 0},
        )
        lines.append(
            f"| {metric} | {counts['wrong']} | {counts['missing']} | {counts['abstain']} |"
        )
    lines.append("")
    lines.append("## Most Failed Documents")
    lines.append("")
    lines.append(
        "| Document | Ticker | Period | Trust | Failed metrics | Context mismatches |"
    )
    lines.append("| --- | --- | --- | --- | ---: | ---: |")
    ranked_results = sorted(
        results,
        key=lambda item: (
            -int(item.get("failed_metric_count", 0)),
            -len(item.get("context_mismatches", [])),
            str(item.get("document_id") or ""),
        ),
    )
    for result in ranked_results:
        lines.append(
            f"| {result['document_id']} | {result.get('ticker') or '-'} | "
            f"{result['period_type']} {result['period_end']} | {result['trust_outcome']} | "
            f"{result.get('failed_metric_count', 0)} | {len(result.get('context_mismatches', []))} |"
        )
    lines.append("")
    lines.append("## Per-Document Breakdown")
    lines.append("")
    lines.append(
        "| Document | Ticker | Period | Context | Trust (actual / expected) | Metric statuses | Mismatch reasons |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for result in results:
        period = f"{result['period_type']} {result['period_end']}"
        context = "ok" if result["context_correct"] else "mismatch"
        trust = f"{result['trust_outcome']} / {result['expected_trust']}"
        metric_statuses = ", ".join(
            f"{name}:{item['status']}"
            for name, item in result["metric_results"].items()
        )
        mismatch = (
            "; ".join(result["mismatch_reasons"]) if result["mismatch_reasons"] else "-"
        )
        lines.append(
            f"| {result['document_id']} | {result.get('ticker') or '-'} | {period} | "
            f"{context} | {trust} | "
            f"{metric_statuses} | {mismatch} |"
        )

    return "\n".join(lines).rstrip() + "\n"


def _artifact_paths(results_json: Path, report_path: Path) -> dict[str, Path]:
    base_name = results_json.stem
    return {
        "results_json": results_json,
        "summary_markdown": report_path,
        "summary_json": results_json.with_name(f"{base_name}_summary.json"),
        "canonical_scorecard_json": results_json.with_name(
            f"{base_name}_canonical_scorecard.json"
        ),
        "documents_csv": results_json.with_name(f"{base_name}_documents.csv"),
        "metrics_csv": results_json.with_name(f"{base_name}_metrics.csv"),
        "trust_triggers_csv": results_json.with_name(f"{base_name}_trust_triggers.csv"),
    }


def _document_rollup_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda item: str(item.get("document_id") or "")):
        rows.append(
            {
                "document_id": result.get("document_id"),
                "ticker": result.get("ticker"),
                "period_type": result.get("period_type"),
                "period_end": result.get("period_end"),
                "trust_outcome": result.get("trust_outcome"),
                "expected_trust": result.get("expected_trust"),
                "trust_matches_expected": result.get("trust_matches_expected"),
                "context_correct": result.get("context_correct"),
                "context_mismatch_count": len(result.get("context_mismatches", [])),
                "correct_metric_count": result.get("correct_metric_count", 0),
                "wrong_metric_count": result.get("wrong_metric_count", 0),
                "missing_metric_count": result.get("missing_metric_count", 0),
                "abstained_metric_count": result.get("abstained_metric_count", 0),
                "failed_metric_count": result.get("failed_metric_count", 0),
                "extraction_status": result.get("extraction_status"),
                "extraction_error": result.get("extraction_error"),
                "source_file": result.get("source_file"),
                "source_path": result.get("source_path"),
            }
        )
    return rows


def _metric_rollup_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda item: str(item.get("document_id") or "")):
        for metric_name in sorted(result.get("metric_results", {})):
            metric_result = result["metric_results"][metric_name]
            rows.append(
                {
                    "document_id": result.get("document_id"),
                    "ticker": result.get("ticker"),
                    "period_type": result.get("period_type"),
                    "period_end": result.get("period_end"),
                    "trust_outcome": result.get("trust_outcome"),
                    "expected_trust": result.get("expected_trust"),
                    "metric_name": metric_name,
                    "status": metric_result.get("status"),
                    "expected": metric_result.get("expected"),
                    "actual": metric_result.get("actual"),
                    "reason": metric_result.get("reason"),
                    "source_metric_key": metric_result.get("source_metric_key"),
                }
            )
    return rows


def _trust_trigger_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda item: str(item.get("document_id") or "")):
        triggers = result.get("trust_triggers") or []
        if not triggers:
            rows.append(
                {
                    "document_id": result.get("document_id"),
                    "ticker": result.get("ticker"),
                    "period_type": result.get("period_type"),
                    "period_end": result.get("period_end"),
                    "trust_outcome": result.get("trust_outcome"),
                    "trigger": "",
                }
            )
            continue
        for trigger in sorted(str(item) for item in triggers):
            rows.append(
                {
                    "document_id": result.get("document_id"),
                    "ticker": result.get("ticker"),
                    "period_type": result.get("period_type"),
                    "period_end": result.get("period_end"),
                    "trust_outcome": result.get("trust_outcome"),
                    "trigger": trigger,
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _development_aggregate(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        aggregate = DevelopmentAggregateResult.from_mapping(payload)
    except (TypeError, ValueError):
        return None
    return aggregate.to_dict()


def _write_development_artifacts(
    aggregate: dict[str, Any],
    *,
    results_json: Path,
    report_path: Path,
) -> None:
    """Write each output format using aggregate allowlisted fields only."""

    artifacts = _artifact_paths(results_json, report_path)
    encoded = json.dumps(aggregate, indent=2, sort_keys=True)
    for key in ("results_json", "summary_json", "canonical_scorecard_json"):
        path = artifacts[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
    fields = sorted(DevelopmentAggregateResult.ALLOWED_FIELDS)
    row = {
        field: (
            json.dumps(aggregate[field], sort_keys=True)
            if isinstance(aggregate[field], dict)
            else aggregate[field]
        )
        for field in fields
    }
    for key in ("documents_csv", "metrics_csv", "trust_triggers_csv"):
        _write_csv(artifacts[key], [row])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# Development Aggregate Result\n\n"
        + "\n".join(
            f"- {field}: {json.dumps(aggregate[field], sort_keys=True)}"
            for field in fields
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    canonical_dataset_dir = _validate_dataset_dir(args.dataset_dir)
    backend_url = _normalize_backend_url(args.backend_url)
    api_key = _resolve_backend_api_key(args.api_key)
    requested_method = normalize_extraction_method(args.parser_backend or "auto")
    development_aggregate = None
    aggregate_path = getattr(args, "development_aggregate_json", None)
    if aggregate_path is not None:
        development_aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))

    if not (
        getattr(args, "corpus_classification", None) == "holdout"
        and getattr(args, "access_mode", None) != "protected"
    ):
        print(
            "Requesting backend real-gold eval from "
            f"{backend_url}/api/extraction-eval/real-gold"
        )
    response_payload = _request_real_gold_eval(
        backend_url=backend_url,
        api_key=api_key,
        limit=args.limit,
        tolerance=args.tolerance,
        method=requested_method,
        strict_method=args.strict_method,
        timeout_seconds=args.timeout_seconds,
        corpus_classification=getattr(args, "corpus_classification", None),
        access_mode=getattr(args, "access_mode", None),
        development_aggregate=development_aggregate,
    )
    aggregate = _development_aggregate(response_payload)
    if aggregate is not None:
        _write_development_artifacts(
            aggregate,
            results_json=args.results_json,
            report_path=args.report_path,
        )
        print(json.dumps(aggregate, sort_keys=True))
        return 0

    summary = response_payload["summary"]
    results = response_payload["documents"]
    eval_policy = _resolve_eval_policy(
        response_payload,
        dataset_dir=canonical_dataset_dir,
        requested_method=str(
            response_payload.get("requested_method", requested_method)
        ),
        strict_method=bool(response_payload.get("strict_method", args.strict_method)),
        limit=args.limit,
        tolerance=max(float(args.tolerance), 0.0),
    )
    fixture_manifest = response_payload.get("fixture_manifest")
    if not isinstance(fixture_manifest, dict):
        fixture_manifest = _build_fixture_manifest(canonical_dataset_dir)
    eval_policy = _apply_fixture_provenance_guard(eval_policy, fixture_manifest)

    report_path = args.report_path
    results_json = args.results_json
    artifact_paths = _artifact_paths(results_json, report_path)
    output_artifact_paths = {key: str(path) for key, path in artifact_paths.items()}
    dataset_dir = str(response_payload.get("dataset_dir") or canonical_dataset_dir)
    run_metadata = {
        "dataset_dir": dataset_dir,
        "extractor_label": args.extractor_label,
        "provider_label": args.provider_label,
        "method_label": args.method_label,
        "model_label": args.model_label,
        "config_label": args.config_label,
        "parser_backend": args.parser_backend,
        "requested_method": response_payload.get("requested_method", requested_method),
        "strict_method": response_payload.get("strict_method", args.strict_method),
        "tolerance": max(float(args.tolerance), 0.0),
        "limit": args.limit,
        "backend_url": backend_url,
        "eval_policy_version": eval_policy.get("policy_version"),
        "eval_mode": eval_policy.get("mode"),
        "kpi_eligible": bool(eval_policy.get("kpi_eligible")),
    }
    output_payload = {
        "dataset_dir": dataset_dir,
        "requested_method": response_payload.get("requested_method", requested_method),
        "strict_method": response_payload.get("strict_method", args.strict_method),
        "run_metadata": run_metadata,
        "eval_policy": eval_policy,
        "fixture_manifest": fixture_manifest,
        "summary": summary,
        "artifact_paths": output_artifact_paths,
        "documents": results,
    }

    results_json.parent.mkdir(parents=True, exist_ok=True)
    results_json.write_text(
        json.dumps(output_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    summary_json = artifact_paths["summary_json"]
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(
        json.dumps(
            {
                "dataset_dir": dataset_dir,
                "requested_method": response_payload.get(
                    "requested_method", requested_method
                ),
                "strict_method": response_payload.get(
                    "strict_method", args.strict_method
                ),
                "run_metadata": run_metadata,
                "eval_policy": eval_policy,
                "fixture_manifest": fixture_manifest,
                "summary": summary,
                "artifact_paths": output_artifact_paths,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    canonical_scorecard_json = artifact_paths["canonical_scorecard_json"]
    canonical_scorecard_json.parent.mkdir(parents=True, exist_ok=True)
    canonical_scorecard_json.write_text(
        json.dumps(
            _build_canonical_scorecard(
                summary=summary,
                eval_policy=eval_policy,
                fixture_manifest=fixture_manifest,
            ),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _write_csv(artifact_paths["documents_csv"], _document_rollup_rows(results))
    _write_csv(artifact_paths["metrics_csv"], _metric_rollup_rows(results))
    _write_csv(artifact_paths["trust_triggers_csv"], _trust_trigger_rows(results))

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _build_report_markdown(
            summary,
            results,
            dataset_dir=dataset_dir,
            eval_policy=eval_policy,
            fixture_manifest=fixture_manifest,
            artifact_paths=output_artifact_paths,
        ),
        encoding="utf-8",
    )

    print("\nPer-document results:")
    for result in results:
        metric_summary = ", ".join(
            f"{name}:{entry['status']}"
            for name, entry in result["metric_results"].items()
        )
        print(
            f"- {result['document_id']}: "
            f"context={'ok' if result['context_correct'] else 'mismatch'}, "
            f"trust={result['trust_outcome']} (expected={result['expected_trust']}), "
            f"metrics=[{metric_summary}]"
        )
        for reason in result["mismatch_reasons"]:
            print(f"  reason: {reason}")

    print("\nSummary:")
    print(
        f"- Metric accuracy: {summary['total_accuracy'] * 100:.2f}% "
        f"({summary['metric_status_counts'].get('correct', 0)}/"
        f"{summary['total_metric_checks']})"
    )
    print(
        f"- Trust distribution: trusted={summary['trust_distribution'].get('trusted', 0)}, "
        f"abstain={summary['trust_distribution'].get('abstain', 0)}, "
        f"quarantine={summary['trust_distribution'].get('quarantine', 0)}"
    )
    print(
        f"- Eval mode: {eval_policy.get('mode')} (kpi_eligible={bool(eval_policy.get('kpi_eligible'))})"
    )
    if not eval_policy.get("kpi_eligible"):
        reasons = list(eval_policy.get("non_canonical_reasons") or [])
        if reasons:
            print("- Non-canonical reasons:")
            for reason in reasons:
                print(f"  - {reason}")
    print(f"- Wrote detailed JSON: {results_json}")
    print(f"- Wrote summary JSON: {summary_json}")
    print(f"- Wrote canonical scorecard JSON: {canonical_scorecard_json}")
    print(f"- Wrote markdown report: {report_path}")
    print(f"- Wrote per-document CSV: {artifact_paths['documents_csv']}")
    print(f"- Wrote per-metric CSV: {artifact_paths['metrics_csv']}")
    print(f"- Wrote trust-trigger CSV: {artifact_paths['trust_triggers_csv']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
