from __future__ import annotations

import csv
import json
from pathlib import Path

from app.services.asx_appendix5b_label_review_packet import (
    build_appendix5b_label_review_packet,
    build_labels_template,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _candidate(metric_name: str, value: int, *, line_item: str) -> dict:
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
                }
            ],
        },
    )
    return path


def test_review_packet_preserves_evidence_and_marks_unconfirmed(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -264, line_item="1.9")],
    )

    packet = build_appendix5b_label_review_packet(
        artifact_paths=[artifact_path],
        generated_at="2026-05-16T00:00:00+00:00",
    )

    item = packet["documents"][0]["review_items"][0]
    assert packet["canonical_write"] is False
    assert packet["summary"]["manual_confirmation_required"] == 1
    assert item["review_status"] == "needs_confirmation"
    assert item["trust_status"] == "unconfirmed_candidate"
    assert item["normalized_value"] == -264000
    assert item["source_evidence"]["source_span"] == "page_12:table_5:1.9:col_2"


def test_review_packet_flags_duplicate_metric_candidates(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[
            _candidate("cash_end", 358, line_item="4.6"),
            _candidate("cash_end", 358, line_item="5.5"),
        ],
    )

    packet = build_appendix5b_label_review_packet(artifact_paths=[artifact_path])
    items = packet["documents"][0]["review_items"]

    assert packet["documents"][0]["duplicate_candidate_groups"] == 1
    assert {item["duplicate_count"] for item in items} == {2}


def test_labels_template_keeps_candidates_out_of_metrics(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -264, line_item="1.9")],
    )
    packet = build_appendix5b_label_review_packet(artifact_paths=[artifact_path])

    template = build_labels_template(packet)

    document = template["documents"][0]
    assert template["canonical_write"] is False
    assert document["metrics"] == {}
    assert document["candidate_label_options"][0]["review_status"] == "needs_confirmation"
    assert document["candidate_label_options"][0]["value"] == -264000


def test_review_packet_writes_json_csv_and_template(tmp_path: Path) -> None:
    artifact_path = _artifact(
        tmp_path / "artifact.json",
        candidates=[_candidate("operating_cf", -264, line_item="1.9")],
    )
    output_json = tmp_path / "review.json"
    output_csv = tmp_path / "review.csv"
    labels_template = tmp_path / "labels_template.json"

    packet = build_appendix5b_label_review_packet(
        artifact_paths=[artifact_path],
        output_json_path=output_json,
        output_csv_path=output_csv,
        labels_template_path=labels_template,
    )

    assert json.loads(output_json.read_text(encoding="utf-8")) == packet
    assert json.loads(labels_template.read_text(encoding="utf-8"))["documents"][0]["metrics"] == {}
    rows = list(csv.DictReader(output_csv.read_text(encoding="utf-8").splitlines()))
    assert rows[0]["metric_name"] == "operating_cf"
    assert rows[0]["review_status"] == "needs_confirmation"


def test_review_packet_ignores_non_current_quarter_candidates(tmp_path: Path) -> None:
    year_to_date = _candidate("operating_cf", -1403, line_item="1.9")
    year_to_date["column_role"] = "year_to_date"
    artifact_path = _artifact(tmp_path / "artifact.json", candidates=[year_to_date])

    packet = build_appendix5b_label_review_packet(artifact_paths=[artifact_path])

    assert packet["summary"]["review_items"] == 0
    assert packet["documents"][0]["review_items"] == []
