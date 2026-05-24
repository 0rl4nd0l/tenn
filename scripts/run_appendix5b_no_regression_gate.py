#!/usr/bin/env python3
"""Run the committed PRM-inclusive Appendix 5B no-regression gate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.asx_appendix5b_candidate_scorer import (  # noqa: E402
    score_appendix5b_candidate_artifacts,
)


DEFAULT_LABELS_PATH = Path(
    "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
    "confirmed_labels_prm_included.json"
)
DEFAULT_ARTIFACT_PATHS = [
    Path(
        "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
        "baseline_artifacts/gre_q4_fy2025_appendix5b.rerun_artifact.json"
    ),
    Path(
        "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
        "baseline_artifacts/eqr_q4_fy2026_appendix5b.rerun_artifact.json"
    ),
    Path(
        "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
        "baseline_artifacts/gre_q_2025-09-30.rerun_artifact.json"
    ),
    Path(
        "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
        "baseline_artifacts/gre_asx_june2025_alt.rerun_artifact.json"
    ),
    Path(
        "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
        "baseline_artifacts/pek_asx_july2025_probe.rerun_artifact.json"
    ),
    Path(
        "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
        "baseline_artifacts/tenx_artifact.json"
    ),
    Path("reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_artifact.json"),
]
DEFAULT_OUTPUT_PATH = Path(
    "reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/"
    "no_regression_report.json"
)

ACCEPTANCE_FLOOR = {
    "documents_scored": 7,
    "document_pass": 5,
    "document_fail": 0,
    "labelled_metric_count": 13,
    "labelled_metrics_with_candidate": 13,
    "trusted_metric_count": 13,
    "expected_null_respected": 2,
    "exact_match_rate": 1.0,
    "labelled_metric_coverage": 1.0,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the report-local PRM-inclusive Appendix 5B scorer and enforce "
            "the committed no-regression acceptance floor."
        )
    )
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--artifact",
        action="append",
        dest="artifacts",
        type=Path,
        help="Candidate artifact JSON. May be passed more than once. Defaults to the 10X gate corpus.",
    )
    return parser.parse_args()


def _missing_inputs(paths: list[Path]) -> list[str]:
    return [str(path) for path in paths if not path.exists()]


def _number(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _min_check(name: str, summary: dict[str, Any], minimum: float | int) -> dict[str, Any]:
    observed = _number(summary.get(name))
    passed = observed is not None and observed >= minimum
    return {
        "name": name,
        "operator": ">=",
        "observed": observed,
        "required": minimum,
        "passed": passed,
    }


def _equal_check(name: str, summary: dict[str, Any], expected: float | int) -> dict[str, Any]:
    observed = _number(summary.get(name))
    passed = observed == expected
    return {
        "name": name,
        "operator": "==",
        "observed": observed,
        "required": expected,
        "passed": passed,
    }


def build_gate_report(
    *,
    score_report: dict[str, Any],
    labels_path: Path,
    artifact_paths: list[Path],
    generated_at: str | None = None,
) -> dict[str, Any]:
    summary = score_report.get("summary") or {}
    checks = [
        {
            "name": "canonical_write",
            "operator": "is false",
            "observed": bool(score_report.get("canonical_write")),
            "required": False,
            "passed": score_report.get("canonical_write") is False,
        },
        _min_check("documents_scored", summary, ACCEPTANCE_FLOOR["documents_scored"]),
        _min_check("document_pass", summary, ACCEPTANCE_FLOOR["document_pass"]),
        _equal_check("document_fail", summary, ACCEPTANCE_FLOOR["document_fail"]),
        _min_check("labelled_metric_count", summary, ACCEPTANCE_FLOOR["labelled_metric_count"]),
        _min_check(
            "labelled_metrics_with_candidate",
            summary,
            ACCEPTANCE_FLOOR["labelled_metrics_with_candidate"],
        ),
        _min_check("trusted_metric_count", summary, ACCEPTANCE_FLOOR["trusted_metric_count"]),
        _min_check(
            "expected_null_respected",
            summary,
            ACCEPTANCE_FLOOR["expected_null_respected"],
        ),
        _min_check("exact_match_rate", summary, ACCEPTANCE_FLOOR["exact_match_rate"]),
        _min_check(
            "labelled_metric_coverage",
            summary,
            ACCEPTANCE_FLOOR["labelled_metric_coverage"],
        ),
    ]
    failed_checks = [check for check in checks if not check["passed"]]
    return {
        "artifact_type": "appendix5b_prm_no_regression_gate_v1",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "canonical_write": False,
        "score_scope": "report_local_labels_only",
        "labels_path": str(labels_path),
        "artifact_paths": [str(path) for path in artifact_paths],
        "acceptance_floor": ACCEPTANCE_FLOOR,
        "gate_pass": not failed_checks,
        "failed_checks": failed_checks,
        "checks": checks,
        "summary": summary,
        "score_report": score_report,
    }


def run_gate(*, labels_path: Path, artifact_paths: list[Path], output_path: Path) -> dict[str, Any]:
    missing = _missing_inputs([labels_path, *artifact_paths])
    if missing:
        raise FileNotFoundError("missing no-regression input(s): " + ", ".join(missing))

    score_report = score_appendix5b_candidate_artifacts(
        artifact_paths=artifact_paths,
        labels_path=labels_path,
        output_path=None,
    )
    gate_report = build_gate_report(
        score_report=score_report,
        labels_path=labels_path,
        artifact_paths=artifact_paths,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(gate_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return gate_report


def main() -> int:
    args = _parse_args()
    artifacts = args.artifacts or DEFAULT_ARTIFACT_PATHS
    report = run_gate(
        labels_path=args.labels,
        artifact_paths=artifacts,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": "PASS" if report["gate_pass"] else "FAIL",
                "output": str(args.output),
                "summary": report["summary"],
                "failed_checks": report["failed_checks"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
