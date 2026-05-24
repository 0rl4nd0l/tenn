from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_appendix5b_no_regression_gate.py"

spec = importlib.util.spec_from_file_location("run_appendix5b_no_regression_gate", str(SCRIPT_PATH))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _score_report(**summary_overrides: object) -> dict[str, object]:
    summary = {
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
    summary.update(summary_overrides)
    return {
        "canonical_write": False,
        "summary": summary,
        "documents": [],
    }


def test_gate_passes_at_prm_acceptance_floor() -> None:
    report = mod.build_gate_report(
        score_report=_score_report(),
        labels_path=Path("labels.json"),
        artifact_paths=[Path("artifact.json")],
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert report["gate_pass"]
    assert report["failed_checks"] == []
    assert report["summary"]["trusted_metric_count"] == 13


def test_gate_fails_on_match_rate_regression() -> None:
    report = mod.build_gate_report(
        score_report=_score_report(exact_match_rate=0.99),
        labels_path=Path("labels.json"),
        artifact_paths=[Path("artifact.json")],
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert not report["gate_pass"]
    assert [check["name"] for check in report["failed_checks"]] == ["exact_match_rate"]


def test_gate_fails_on_unexpected_document_failure() -> None:
    report = mod.build_gate_report(
        score_report=_score_report(document_fail=1),
        labels_path=Path("labels.json"),
        artifact_paths=[Path("artifact.json")],
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert not report["gate_pass"]
    assert [check["name"] for check in report["failed_checks"]] == ["document_fail"]


def test_gate_fails_if_score_report_claims_canonical_write() -> None:
    payload = _score_report()
    payload["canonical_write"] = True

    report = mod.build_gate_report(
        score_report=payload,
        labels_path=Path("labels.json"),
        artifact_paths=[Path("artifact.json")],
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert not report["gate_pass"]
    assert [check["name"] for check in report["failed_checks"]] == ["canonical_write"]
