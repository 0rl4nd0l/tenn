from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.asx_appendix5b_candidate_scorer import (
    score_appendix5b_candidate_artifacts,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _candidate(
    metric_name: str,
    value: int,
    *,
    line_item: str,
    column_role: str = "current_quarter",
) -> dict:
    return {
        "metric_name": metric_name,
        "value": value,
        "raw_value": str(value),
        "unit": "currency",
        "currency": "AUD",
        "scale": "thousands",
        "period_label": "Current quarter $A'000",
        "column_role": column_role,
        "document_type": "appendix_5b",
        "parser_method": "appendix5b_deterministic_v1",
        "confidence": 0.96,
        "trust_status": "candidate",
        "evidence": {
            "page": 12,
            "table_index": 1,
            "row_index": 4,
            "column_index": 2,
            "row_label": f"{line_item} | row",
            "column_label": "Current quarter $A'000",
            "line_item": line_item,
            "source_span": "page_12:table_1:row_4:col_2",
        },
        "component_evidence": [],
    }


def _artifact(path: Path, *, candidates: list[dict]) -> Path:
    _write_json(
        path,
        {
            "artifact_type": "appendix5b_candidate_eval_v1",
            "canonical_write": False,
            "documents": [
                {
                    "document_id": "gre_doc",
                    "ticker": "GRE",
                    "period_end": "2025-06-30",
                    "period_type": "Q",
                    "document_type": "appendix_5b",
                    "parse_status": "parsed",
                    "candidate_count": len(candidates),
                    "missing_count": 0,
                    "candidates": candidates,
                    "missing": [],
                    "comparisons": [],
                }
            ],
        },
    )
    return path


def _labels(path: Path, document: dict) -> Path:
    _write_json(
        path,
        {
            "label_schema": "appendix5b_candidate_labels_v1",
            "documents": [document],
        },
    )
    return path


def test_scorer_matches_labelled_metric_and_preserves_evidence(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -264, line_item="1.9")],
    )
    labels_path = _labels(
        tmp_path / "labels.json",
        {
            "document_id": "gre_doc",
            "metrics": {
                "operating_cf": {
                    "value": -264000,
                    "line_item": "1.9",
                    "source_evidence": "manual_label_fixture:1.9",
                }
            },
        },
    )

    report = score_appendix5b_candidate_artifacts(
        artifact_paths=[artifact_path],
        labels_path=labels_path,
        generated_at="2026-05-16T00:00:00+00:00",
    )

    assert report["canonical_write"] is False
    assert report["summary"]["match"] == 1
    assert report["summary"]["exact_match_rate"] == 1.0
    comparison = report["documents"][0]["comparisons"][0]
    assert comparison["candidate"]["evidence"]["source_span"] == "page_12:table_1:row_4:col_2"
    assert comparison["label_source_evidence"] == "manual_label_fixture:1.9"


def test_scorer_reports_mismatch_without_promoting_truth(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -100, line_item="1.9")],
    )
    labels_path = _labels(
        tmp_path / "labels.json",
        {"document_id": "gre_doc", "metrics": {"operating_cf": -264000}},
    )

    report = score_appendix5b_candidate_artifacts(
        artifact_paths=[artifact_path],
        labels_path=labels_path,
    )

    comparison = report["documents"][0]["comparisons"][0]
    assert report["documents"][0]["status"] == "FAIL"
    assert comparison["status"] == "mismatch"
    assert comparison["candidate_value"] == -100000
    assert comparison["gold_value"] == -264000
    assert "does not match" in comparison["failure_reason"]


def test_scorer_reports_missing_labelled_metric_as_data_missing(tmp_path: Path) -> None:
    artifact_path = _artifact(tmp_path / "artifact.json", candidates=[])
    labels_path = _labels(
        tmp_path / "labels.json",
        {"document_id": "gre_doc", "metrics": {"operating_cf": -264000}},
    )

    report = score_appendix5b_candidate_artifacts(
        artifact_paths=[artifact_path],
        labels_path=labels_path,
    )

    comparison = report["documents"][0]["comparisons"][0]
    assert comparison["status"] == "candidate_missing"
    assert "DATA_MISSING" in comparison["failure_reason"]
    assert report["summary"]["labelled_metric_coverage"] == 0.0


def test_scorer_reports_unlabelled_candidates_separately(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[
            _candidate("operating_cf", -264, line_item="1.9"),
            _candidate("investing_cf", -638, line_item="2.6"),
        ],
    )
    labels_path = _labels(
        tmp_path / "labels.json",
        {"document_id": "gre_doc", "metrics": {"operating_cf": -264000}},
    )

    report = score_appendix5b_candidate_artifacts(
        artifact_paths=[artifact_path],
        labels_path=labels_path,
    )

    statuses = [comparison["status"] for comparison in report["documents"][0]["comparisons"]]
    assert statuses == ["match", "candidate_unlabelled"]
    assert report["summary"]["candidate_unlabelled"] == 1


def test_expected_null_and_unexpected_candidate_statuses(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("capex", -10, line_item="2.1(c)")],
    )
    labels_path = _labels(
        tmp_path / "labels.json",
        {
            "document_id": "gre_doc",
            "metrics": {},
            "expected_nulls": ["cash_end", "capex"],
        },
    )

    report = score_appendix5b_candidate_artifacts(
        artifact_paths=[artifact_path],
        labels_path=labels_path,
    )

    comparisons = {
        comparison["metric_name"]: comparison
        for comparison in report["documents"][0]["comparisons"]
    }
    assert comparisons["cash_end"]["status"] == "expected_null_respected"
    assert comparisons["capex"]["status"] == "unexpected_candidate_for_expected_null"


def test_duplicate_metric_requires_line_item_binding(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[
            _candidate("cash_end", 358, line_item="4.6"),
            _candidate("cash_end", 358, line_item="5.5"),
        ],
    )
    labels_path = _labels(
        tmp_path / "labels.json",
        {"document_id": "gre_doc", "metrics": {"cash_end": 358000}},
    )

    report = score_appendix5b_candidate_artifacts(
        artifact_paths=[artifact_path],
        labels_path=labels_path,
    )

    comparison = report["documents"][0]["comparisons"][0]
    assert comparison["status"] == "ambiguous_candidate"
    assert "line_item" in comparison["failure_reason"]


def test_scorer_writes_output_path(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -264, line_item="1.9")],
    )
    labels_path = _labels(
        tmp_path / "labels.json",
        {"document_id": "gre_doc", "metrics": {"operating_cf": -264000}},
    )
    output_path = tmp_path / "score.json"

    report = score_appendix5b_candidate_artifacts(
        artifact_paths=[artifact_path],
        labels_path=labels_path,
        output_path=output_path,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == report


def test_labels_require_documents_list(tmp_path: Path) -> None:
    artifact_path = _artifact(tmp_path / "artifact.json", candidates=[])
    labels_path = tmp_path / "labels.json"
    _write_json(labels_path, {"documents": {}})

    with pytest.raises(ValueError, match="labels.documents must be a list"):
        score_appendix5b_candidate_artifacts(
            artifact_paths=[artifact_path],
            labels_path=labels_path,
        )
