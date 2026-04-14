#!/usr/bin/env python3
"""Run the real ASX extraction eval through the backend-owned endpoint."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
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
from app.services.method_isolated_extraction import normalize_extraction_method


DEFAULT_DATASET_DIR = FINANCIAL_ENGINE_ROOT / "data" / "extraction_gold_real"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports" / "extraction_real_eval_summary.md"
DEFAULT_RESULTS_JSON = REPO_ROOT / "reports" / "extraction_real_eval_results.json"
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 1800.0
SUPPORTED_METRICS = ("revenue", "operating_cash_flow", "net_debt")


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
        default=None,
        choices=["docling", "pymupdf", "anthropic"],
        help="Request a specific backend extraction method (default: auto).",
    )
    parser.add_argument(
        "--strict-method",
        action="store_true",
        help="Require the requested extraction method without backend fallback.",
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


def _request_real_gold_eval(
    *,
    backend_url: str,
    api_key: str | None,
    limit: int,
    tolerance: float,
    method: str,
    strict_method: bool,
    timeout_seconds: float,
) -> dict[str, Any]:
    body = {
        "limit": max(int(limit), 0),
        "tolerance": max(float(tolerance), 0.0),
        "method": normalize_extraction_method(method),
        "strict_method": bool(strict_method),
    }
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if api_key:
        headers["X-API-Key"] = api_key

    request = urlrequest.Request(
        f"{backend_url}/api/extraction-eval/real-gold",
        data=payload,
        headers=headers,
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=max(float(timeout_seconds), 1.0)) as resp:
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
        raise RuntimeError(
            f"backend real-gold eval failed (HTTP {exc.code}){suffix}"
        ) from exc
    except (urlerror.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"backend real-gold eval request failed: {exc}"
        ) from exc

    try:
        decoded = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "backend real-gold eval returned non-JSON output"
        ) from exc
    if not isinstance(decoded, dict):
        raise RuntimeError("backend real-gold eval returned a non-object payload")
    if not isinstance(decoded.get("summary"), dict):
        raise RuntimeError("backend real-gold eval payload is missing summary")
    if not isinstance(decoded.get("documents"), list):
        raise RuntimeError("backend real-gold eval payload is missing documents")
    return decoded


def _build_report_markdown(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    dataset_dir: str,
    artifact_paths: dict[str, str],
) -> str:
    lines: list[str] = []
    lines.append("# Extraction Real Eval Summary")
    lines.append("")
    lines.append(f"- Generated: {summary['generated_at']}")
    lines.append(f"- Dataset: `{dataset_dir}`")
    lines.append(f"- Documents: {summary['total_documents']}")
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
    lines.append("| Document | Ticker | Period | Trust | Failed metrics | Context mismatches |")
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


def main() -> int:
    args = _parse_args()
    canonical_dataset_dir = _validate_dataset_dir(args.dataset_dir)
    backend_url = _normalize_backend_url(args.backend_url)
    api_key = _resolve_backend_api_key(args.api_key)
    requested_method = normalize_extraction_method(args.parser_backend or "auto")

    print(
        f"Requesting backend real-gold eval from {backend_url}/api/extraction-eval/real-gold"
    )
    response_payload = _request_real_gold_eval(
        backend_url=backend_url,
        api_key=api_key,
        limit=args.limit,
        tolerance=args.tolerance,
        method=requested_method,
        strict_method=args.strict_method,
        timeout_seconds=args.timeout_seconds,
    )

    summary = response_payload["summary"]
    results = response_payload["documents"]
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
    }
    output_payload = {
        "dataset_dir": dataset_dir,
        "requested_method": response_payload.get("requested_method", requested_method),
        "strict_method": response_payload.get("strict_method", args.strict_method),
        "run_metadata": run_metadata,
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
                "summary": summary,
                "artifact_paths": output_artifact_paths,
            },
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
    print(f"- Wrote detailed JSON: {results_json}")
    print(f"- Wrote summary JSON: {summary_json}")
    print(f"- Wrote markdown report: {report_path}")
    print(f"- Wrote per-document CSV: {artifact_paths['documents_csv']}")
    print(f"- Wrote per-metric CSV: {artifact_paths['metrics_csv']}")
    print(f"- Wrote trust-trigger CSV: {artifact_paths['trust_triggers_csv']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
