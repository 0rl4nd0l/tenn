#!/usr/bin/env python3
"""Normalize Gold Metric Coverage artifacts into offline Eval Spine artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.reporting import eval_spine_manifest


CANONICAL_CORE_GUARD = (
    "canonical_core is a strict 10-document / 24-check no-regression proof only"
)
EXPANDED_REQUIRED_GUARD = (
    "expanded_required is a 15-document / 39-check required-metric proof where available"
)
CONFIRMED_COVERAGE_GUARD = (
    "confirmed_metric_coverage is read-only breadth inventory, not current accuracy proof"
)
UNSCORED_GUARD = (
    "confirmed_unscored and schema_supported_but_not_labelled are not accuracy claims"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_metric_inventory(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("metric inventory must be a JSON object")
    return payload


def _int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_scorecards(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    canonical = inventory.get("canonical_core") if isinstance(inventory.get("canonical_core"), dict) else {}
    expanded = inventory.get("expanded_required") if isinstance(inventory.get("expanded_required"), dict) else {}
    confirmed = (
        inventory.get("confirmed_metric_coverage")
        if isinstance(inventory.get("confirmed_metric_coverage"), dict)
        else {}
    )
    return [
        {
            "scorecard_profile": "canonical_core",
            "status": "profile_defined_no_regression",
            "document_count": _int_value(canonical.get("document_count")),
            "metric_check_count": _int_value(canonical.get("metric_check_count")),
            "eligible_metric_count": len(canonical.get("metrics") or []),
            "candidate_count": None,
            "ambiguous_count": None,
            "unsupported_count": None,
            "data_missing_count": 0,
            "accuracy_claim": "strict_no_regression_profile",
            "overclaim_guard": CANONICAL_CORE_GUARD,
        },
        {
            "scorecard_profile": "expanded_required",
            "status": "profile_defined_required_metrics",
            "document_count": _int_value(expanded.get("document_count")),
            "metric_check_count": _int_value(expanded.get("metric_check_count")),
            "eligible_metric_count": len(expanded.get("metrics") or []),
            "candidate_count": None,
            "ambiguous_count": None,
            "unsupported_count": None,
            "data_missing_count": 0,
            "accuracy_claim": "required_metric_profile_where_available",
            "overclaim_guard": EXPANDED_REQUIRED_GUARD,
        },
        {
            "scorecard_profile": "confirmed_metric_coverage",
            "status": "inventory_only_not_accuracy",
            "document_count": _int_value(confirmed.get("fixture_count")),
            "metric_check_count": _int_value(confirmed.get("total_expectations")),
            "eligible_metric_count": _int_value(confirmed.get("scorable_count")),
            "candidate_count": _int_value(confirmed.get("candidate_count")),
            "ambiguous_count": _int_value(confirmed.get("ambiguous_count")),
            "unsupported_count": _int_value(confirmed.get("unsupported_count")),
            "data_missing_count": 1,
            "accuracy_claim": "none_inventory_only",
            "overclaim_guard": CONFIRMED_COVERAGE_GUARD,
        },
    ]


def build_metric_rows(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in ("canonical_core", "expanded_required"):
        payload = inventory.get(profile) if isinstance(inventory.get(profile), dict) else {}
        for metric in payload.get("metrics") or []:
            rows.append(
                {
                    "scorecard_profile": profile,
                    "metric_name": str(metric),
                    "expectation_class": "required_scored_metric",
                    "accuracy_claim": "profile_scorecard_boundary_only",
                    "document_count": _int_value(payload.get("document_count")),
                    "metric_check_count": _int_value(payload.get("metric_check_count")),
                    "notes": "Metric participates in the named scorecard profile only.",
                }
            )
    for metric in inventory.get("confirmed_unscored") or []:
        rows.append(
            {
                "scorecard_profile": "confirmed_metric_coverage",
                "metric_name": str(metric),
                "expectation_class": "confirmed_unscored",
                "accuracy_claim": "none",
                "document_count": _int_value((inventory.get("confirmed_metric_coverage") or {}).get("fixture_count")),
                "metric_check_count": 0,
                "notes": UNSCORED_GUARD,
            }
        )
    for metric in inventory.get("ambiguous_or_derived") or []:
        rows.append(
            {
                "scorecard_profile": "confirmed_metric_coverage",
                "metric_name": str(metric),
                "expectation_class": "ambiguous_or_derived",
                "accuracy_claim": "none",
                "document_count": 0,
                "metric_check_count": 0,
                "notes": "Ambiguous or derived metrics require a separate definition contract.",
            }
        )
    for metric in inventory.get("unsupported") or []:
        rows.append(
            {
                "scorecard_profile": "confirmed_metric_coverage",
                "metric_name": str(metric),
                "expectation_class": "unsupported",
                "accuracy_claim": "none",
                "document_count": 0,
                "metric_check_count": 0,
                "notes": "Unsupported in current runtime/gold scoring semantics.",
            }
        )
    return rows


def _git_value(args: list[str], cwd: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        return None
    value = completed.stdout.strip()
    return value or None


def build_manifest(
    *,
    inventory_path: Path,
    output_dir: Path,
    task_card: Path,
    job_id: str,
    repo_root: Path,
) -> dict[str, Any]:
    inventory = load_metric_inventory(inventory_path)
    manifest = eval_spine_manifest.empty_manifest()
    now = utc_now()
    manifest.update(
        {
            "job_id": job_id,
            "lane": "Evaluation",
            "supporting_lanes": ["Financial Truth"],
            "mode": "safe_extension",
            "production_data_access": False,
            "branch": _git_value(["branch", "--show-current"], repo_root),
            "head": _git_value(["rev-parse", "HEAD"], repo_root),
            "base_head": None,
            "worktree": str(repo_root),
            "task_card": {
                "path": eval_spine_manifest.repo_relative(task_card, repo_root),
                "sha256": eval_spine_manifest.sha256_file(task_card),
                "validation_ok": None,
                "validation_issues": [],
            },
            "output_dir": eval_spine_manifest.repo_relative(output_dir, repo_root),
            "started_at": now,
            "completed_at": now,
            "status": "normalized_offline",
            "verdicts": [
                {
                    "verdict": "GOLD_METRIC_COVERAGE_NORMALIZED_OFFLINE",
                    "truth_status": "report_local_only",
                    "confidence": "artifact_normalization",
                    "notes": "No parser, extraction, gold-label, database, Qdrant, news, or memory writes.",
                    "source_artifact": eval_spine_manifest.repo_relative(inventory_path, repo_root),
                }
            ],
            "scorecards": build_scorecards(inventory),
            "validation_commands": [],
            "changed_files": [],
            "data_missing": [
                {
                    "field": "confirmed_metric_coverage_current_accuracy",
                    "code": "missing_confirmed_metric_coverage_current_accuracy",
                    "class": "accuracy_proof_missing",
                    "description": "confirmed_metric_coverage is breadth inventory only; no current extracted-payload scoring artifact was supplied.",
                    "blocked_by_policy": False,
                    "blocked_by_environment": False,
                    "expected_empty_state": False,
                    "source_artifact": eval_spine_manifest.repo_relative(inventory_path, repo_root),
                },
                {
                    "field": "base_head",
                    "code": "missing_base_head",
                    "class": "comparison_base_missing",
                    "description": "No comparison base is needed for report-local normalization.",
                    "blocked_by_policy": False,
                    "blocked_by_environment": False,
                    "expected_empty_state": True,
                    "source_artifact": "gold_metric_coverage_eval_spine_normalizer",
                },
            ],
            "degraded_states": [],
            "source_artifacts": [
                eval_spine_manifest.source_artifact(inventory_path, repo_root, "metric_inventory"),
                eval_spine_manifest.source_artifact(task_card, repo_root, "task_card"),
            ],
            "save_recommendation": "SAVE_RECOMMENDED",
            "do_not_overclaim": [
                CANONICAL_CORE_GUARD,
                EXPANDED_REQUIRED_GUARD,
                CONFIRMED_COVERAGE_GUARD,
                UNSCORED_GUARD,
                "No normalized row is a canonical financial truth write.",
            ],
        }
    )
    if not manifest["branch"]:
        eval_spine_manifest.add_missing(
            manifest,
            "branch",
            "Git branch was unavailable for the supplied repo root.",
            "gold_metric_coverage_eval_spine_normalizer",
        )
    if not manifest["head"]:
        eval_spine_manifest.add_missing(
            manifest,
            "head",
            "Git HEAD was unavailable for the supplied repo root.",
            "gold_metric_coverage_eval_spine_normalizer",
        )
    return manifest


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_outputs(
    *,
    inventory_path: Path,
    output_dir: Path,
    task_card: Path,
    job_id: str,
    repo_root: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = load_metric_inventory(inventory_path)
    manifest = build_manifest(
        inventory_path=inventory_path,
        output_dir=output_dir,
        task_card=task_card,
        job_id=job_id,
        repo_root=repo_root,
    )
    issues = eval_spine_manifest.validate_manifest(manifest)
    if issues:
        raise ValueError("; ".join(issues))

    manifest_path = output_dir / "normalized_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scorecards_path = output_dir / "scorecards.csv"
    metric_expectations_path = output_dir / "metric_expectations.csv"
    write_csv(scorecards_path, build_scorecards(inventory))
    write_csv(metric_expectations_path, build_metric_rows(inventory))
    return {
        "normalized_manifest": str(manifest_path),
        "scorecards_csv": str(scorecards_path),
        "metric_expectations_csv": str(metric_expectations_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metric-inventory", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--task-card", required=True, type=Path)
    parser.add_argument(
        "--job-id",
        default="gold_metric_coverage_eval_spine_normalizer_v1_20260524",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    outputs = write_outputs(
        inventory_path=args.metric_inventory.resolve(strict=True),
        output_dir=args.out_dir.resolve(strict=False),
        task_card=args.task_card.resolve(strict=True),
        job_id=args.job_id,
        repo_root=args.repo_root.resolve(strict=False),
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
