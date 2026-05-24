from __future__ import annotations

import json
from pathlib import Path

from app.services.asx_appendix5b_confirmed_label_importer import (
    import_confirmed_appendix5b_labels,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _fixture(
    path: Path,
    *,
    source: str = "Hand-verified from ASX Appendix 5B.",
    document_id: str = "gre_doc",
    metric_value: int = -264000,
    metrics: dict[str, int] | None = None,
    tolerances: dict[str, float] | None = None,
) -> Path:
    fixture_metrics = metrics or {"operating_cf": metric_value}
    _write_json(
        path,
        {
            "_source": source,
            "document_id": document_id,
            "ticker": "GRE",
            "period_type": "Q",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "thousands",
            "metrics": fixture_metrics,
            "expected_nulls": [],
            "tolerances": tolerances or {metric_name: 0.01 for metric_name in fixture_metrics},
        },
    )
    return path


def _candidate(metric_name: str, value: int, *, line_item: str = "1.9") -> dict:
    return {
        "metric_name": metric_name,
        "value": value,
        "raw_value": str(value),
        "unit": "currency",
        "currency": "AUD",
        "scale": "thousands",
        "period_label": "Current quarter $A'000",
        "column_role": "current_quarter",
        "document_type": "appendix_5b",
        "parser_method": "appendix5b_deterministic_v1",
        "confidence": 0.96,
        "trust_status": "candidate",
        "evidence": {
            "page": 12,
            "table_index": 5,
            "row_index": 15,
            "column_index": 2,
            "row_label": f"{line_item} | row",
            "column_label": "Current quarter $A'000",
            "line_item": line_item,
            "source_span": f"page_12:table_5:{line_item}:col_2",
        },
        "component_evidence": [],
    }


def _artifact(
    path: Path,
    *,
    document_id: str = "gre_doc",
    period_end: str = "2025-06-30",
    candidates: list[dict] | None = None,
) -> Path:
    _write_json(
        path,
        {
            "artifact_type": "appendix5b_candidate_eval_v1",
            "canonical_write": False,
            "documents": [
                {
                    "document_id": document_id,
                    "ticker": "GRE",
                    "period_end": period_end,
                    "period_type": "Q",
                    "document_type": "appendix_5b",
                    "parse_status": "parsed",
                    "candidate_count": len(candidates or []),
                    "missing_count": 0,
                    "candidates": candidates or [],
                    "missing": [],
                }
            ],
        },
    )
    return path


def test_imports_confirmed_fixture_when_candidate_context_and_value_match(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    _fixture(fixtures_dir / "gre.json")
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -264)],
    )

    result = import_confirmed_appendix5b_labels(
        artifact_paths=[artifact_path],
        fixtures_dir=fixtures_dir,
        generated_at="2026-05-16T00:00:00+00:00",
    )

    document = result["labels"]["documents"][0]
    assert result["report"]["summary"]["labels_imported"] == 1
    assert document["metrics"]["operating_cf"]["value"] == -264000
    assert document["metrics"]["operating_cf"]["line_item"] == "1.9"
    assert document["metrics"]["operating_cf"]["review_status"] == "confirmed_source_evidenced"
    assert document["metrics"]["operating_cf"]["source_evidence"]["source_span"] == (
        "page_12:table_5:1.9:col_2"
    )


def test_candidate_review_fixture_is_not_imported_as_confirmed(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    _fixture(
        fixtures_dir / "gre.json",
        source="Claude API verified from ASX Appendix 5B.",
    )
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -264)],
    )

    result = import_confirmed_appendix5b_labels(
        artifact_paths=[artifact_path],
        fixtures_dir=fixtures_dir,
    )

    assert result["labels"]["documents"] == []
    assert result["report"]["summary"]["labels_imported"] == 0
    assert result["report"]["documents"][0]["status"] == "NO_IMPORTS"


def test_document_id_mismatch_is_reported_without_import(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    _fixture(fixtures_dir / "gre.json", document_id="gre_fixture")
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        document_id="gre_artifact",
        candidates=[_candidate("operating_cf", -264)],
    )

    result = import_confirmed_appendix5b_labels(
        artifact_paths=[artifact_path],
        fixtures_dir=fixtures_dir,
    )

    doc = result["report"]["documents"][0]
    assert result["labels"]["documents"] == []
    assert doc["status"] == "NO_MATCHING_FIXTURE"


def test_context_mismatch_is_reported_without_import(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    _fixture(fixtures_dir / "gre.json")
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        period_end="2025-09-30",
        candidates=[_candidate("operating_cf", -264)],
    )

    result = import_confirmed_appendix5b_labels(
        artifact_paths=[artifact_path],
        fixtures_dir=fixtures_dir,
    )

    doc = result["report"]["documents"][0]
    assert result["labels"]["documents"] == []
    assert doc["status"] == "CONTEXT_MISMATCH"
    assert doc["context_mismatches"] == ["period_end"]


def test_duplicate_matching_candidates_are_left_for_manual_review(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    _fixture(fixtures_dir / "gre.json")
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[
            _candidate("operating_cf", -264, line_item="1.9"),
            _candidate("operating_cf", -264, line_item="1.9-alt"),
        ],
    )

    result = import_confirmed_appendix5b_labels(
        artifact_paths=[artifact_path],
        fixtures_dir=fixtures_dir,
    )

    row = result["report"]["documents"][0]["rows"][0]
    assert result["labels"]["documents"] == []
    assert row["status"] == "ambiguous_candidate"


def test_cash_end_duplicate_candidates_prefer_reconciliation_line_5_5(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    _fixture(
        fixtures_dir / "gre.json",
        metrics={"cash_end": 702000},
        tolerances={"cash_end": 0.001},
    )
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[
            _candidate("cash_end", 702, line_item="4.6"),
            _candidate("cash_end", 702, line_item="5.5"),
        ],
    )

    result = import_confirmed_appendix5b_labels(
        artifact_paths=[artifact_path],
        fixtures_dir=fixtures_dir,
    )

    document = result["labels"]["documents"][0]
    row = result["report"]["documents"][0]["rows"][0]
    assert result["report"]["summary"]["labels_imported"] == 1
    assert result["report"]["summary"]["ambiguous_candidate"] == 0
    assert row["status"] == "imported"
    assert row["candidate_line_item"] == "5.5"
    assert document["metrics"]["cash_end"]["line_item"] == "5.5"
    assert document["metrics"]["cash_end"]["source_evidence"]["line_item"] == "5.5"


def test_value_mismatch_is_reported_without_import(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    _fixture(fixtures_dir / "gre.json")
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -100)],
    )

    result = import_confirmed_appendix5b_labels(
        artifact_paths=[artifact_path],
        fixtures_dir=fixtures_dir,
    )

    row = result["report"]["documents"][0]["rows"][0]
    assert result["labels"]["documents"] == []
    assert row["status"] == "candidate_value_mismatch"


def test_importer_writes_labels_and_report(tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    _fixture(fixtures_dir / "gre.json")
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -264)],
    )
    labels_path = tmp_path / "labels.json"
    report_path = tmp_path / "report.json"

    result = import_confirmed_appendix5b_labels(
        artifact_paths=[artifact_path],
        fixtures_dir=fixtures_dir,
        output_labels_path=labels_path,
        output_report_path=report_path,
    )

    assert json.loads(labels_path.read_text(encoding="utf-8")) == result["labels"]
    assert json.loads(report_path.read_text(encoding="utf-8")) == result["report"]
