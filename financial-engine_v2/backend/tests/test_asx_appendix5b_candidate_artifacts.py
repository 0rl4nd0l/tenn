from __future__ import annotations

import json
from pathlib import Path

from app.services.asx_appendix5b_candidate_artifacts import (
    build_artifact_from_manifest,
    run_manifest_to_artifact,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _gold_fixture(**overrides: object) -> dict:
    payload = {
        "ticker": "GRE",
        "document_id": "gre_q4_fy2025_appendix5b",
        "period_type": "Q",
        "period_end": "2024-12-31",
        "currency": "AUD",
        "scale": "thousands",
        "metrics": {
            "operating_cf": -450000,
            "investing_cf": -624000,
            "financing_cf": 869000,
            "cash_end": 702000,
        },
        "expected_nulls": [
            "revenue",
            "ebit",
            "np_attributable",
            "net_debt",
            "shares_outstanding",
        ],
        "tolerances": {
            "operating_cf": 0.01,
            "investing_cf": 0.01,
            "financing_cf": 0.01,
            "cash_end": 0.001,
        },
    }
    payload.update(overrides)
    return payload


def _appendix5b_document(gold_fixture_path: str, *, rows: list[list[str]] | None = None) -> dict:
    headers = ["Item", "Description", "Current quarter $A'000", "Year to date $A'000"]
    return {
        "document_id": "gre_q4_fy2025_appendix5b",
        "ticker": "GRE",
        "period_type": "Q",
        "period_end": "2024-12-31",
        "gold_fixture_path": gold_fixture_path,
        "tables": [
            {
                "page_number": 12,
                "caption": "Appendix 5B Mining exploration entity quarterly cash flow report",
                "headers": headers,
                "rows": [
                    headers,
                    *(
                        rows
                        if rows is not None
                        else [
                            ["2.1(c)", "Payments to acquire property, plant and equipment", "0", "0"],
                            ["2.1(d)", "Payments for exploration and evaluation", "(624)", "(624)"],
                            ["1.9", "Net cash from / (used in) operating activities", "(450)", "(450)"],
                            ["2.6", "Net cash from / (used in) investing activities", "(624)", "(624)"],
                            ["3.10", "Net cash from / (used in) financing activities", "869", "869"],
                            ["4.6", "Cash and cash equivalents at end of period", "702", "702"],
                        ]
                    ),
                ],
            }
        ],
    }


def test_artifact_matches_gold_with_scale_normalization(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    _write_json(fixture_path, _gold_fixture())
    manifest = {
        "run_id": "unit",
        "documents": [_appendix5b_document(str(fixture_path))],
    }

    artifact = build_artifact_from_manifest(
        manifest,
        repo_root=tmp_path,
        generated_at="2026-05-16T00:00:00+00:00",
    )

    assert artifact["canonical_write"] is False
    assert artifact["summary"]["match"] == 4
    assert artifact["summary"]["candidate_unlabelled"] == 1

    comparisons = {
        comparison["metric_name"]: comparison
        for comparison in artifact["documents"][0]["comparisons"]
    }
    assert comparisons["operating_cf"]["status"] == "match"
    assert comparisons["operating_cf"]["candidate_value"] == -450000
    assert comparisons["operating_cf"]["raw_candidate_value"] == -450
    assert comparisons["capex"]["status"] == "candidate_unlabelled"
    assert comparisons["capex"]["candidate_value"] == -624000


def test_artifact_reports_candidate_missing_for_labelled_metric(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    _write_json(fixture_path, _gold_fixture())
    manifest = {
        "documents": [
            _appendix5b_document(
                str(fixture_path),
                rows=[
                    ["1.9", "Net cash from / (used in) operating activities", "(450)", "(450)"],
                    ["3.10", "Net cash from / (used in) financing activities", "869", "869"],
                    ["4.6", "Cash and cash equivalents at end of period", "702", "702"],
                ],
            )
        ]
    }

    artifact = build_artifact_from_manifest(manifest, repo_root=tmp_path)
    comparisons = {
        comparison["metric_name"]: comparison
        for comparison in artifact["documents"][0]["comparisons"]
    }

    assert comparisons["investing_cf"]["status"] == "candidate_missing"
    assert comparisons["investing_cf"]["gold_value"] == -624000
    assert "DATA_MISSING" in comparisons["investing_cf"]["failure_reason"]


def test_artifact_matches_investing_cf_from_reconciliation_row(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    _write_json(
        fixture_path,
        _gold_fixture(
            metrics={
                "operating_cf": -63000,
                "investing_cf": -5000,
                "cash_end": 290000,
            },
            expected_nulls=["financing_cf"],
        ),
    )
    manifest = {
        "documents": [
            _appendix5b_document(
                str(fixture_path),
                rows=[
                    ["1.9", "Net cash from / (used in) operating activities", "(63)", "(63)"],
                    ["2.6", "Net cash from / (used in) investing activities", "-", "-"],
                    ["3.10", "Net cash from / (used in) financing activities", "-", "-"],
                    ["4.3", "Net cash from / (used in) investing activities (item 2.6 above)", "(5)", "(5)"],
                    ["4.6", "Cash and cash equivalents at end of period", "290", "290"],
                ],
            )
        ]
    }

    artifact = build_artifact_from_manifest(manifest, repo_root=tmp_path)
    comparisons = {
        comparison["metric_name"]: comparison
        for comparison in artifact["documents"][0]["comparisons"]
    }

    assert comparisons["investing_cf"]["status"] == "match"
    assert comparisons["investing_cf"]["candidate_value"] == -5000
    assert comparisons["investing_cf"]["candidate"]["evidence"]["line_item"] == "4.3"


def test_artifact_reports_mismatch_without_promoting_truth(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    _write_json(fixture_path, _gold_fixture())
    manifest = {
        "documents": [
            _appendix5b_document(
                str(fixture_path),
                rows=[
                    ["1.9", "Net cash from / (used in) operating activities", "(100)", "(100)"],
                    ["2.6", "Net cash from / (used in) investing activities", "(624)", "(624)"],
                    ["3.10", "Net cash from / (used in) financing activities", "869", "869"],
                    ["4.6", "Cash and cash equivalents at end of period", "702", "702"],
                ],
            )
        ]
    }

    artifact = build_artifact_from_manifest(manifest, repo_root=tmp_path)
    comparisons = {
        comparison["metric_name"]: comparison
        for comparison in artifact["documents"][0]["comparisons"]
    }

    assert artifact["canonical_write"] is False
    assert comparisons["operating_cf"]["status"] == "mismatch"
    assert comparisons["operating_cf"]["candidate_value"] == -100000
    assert comparisons["operating_cf"]["gold_value"] == -450000


def test_expected_nulls_are_reported_without_zero_fabrication(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    _write_json(
        fixture_path,
        _gold_fixture(
            metrics={"operating_cf": -450000},
            expected_nulls=["cash_end", "investing_cf", "financing_cf"],
        ),
    )
    manifest = {
        "documents": [
            _appendix5b_document(
                str(fixture_path),
                rows=[
                    ["1.9", "Net cash from / (used in) operating activities", "(450)", "(450)"],
                ],
            )
        ]
    }

    artifact = build_artifact_from_manifest(manifest, repo_root=tmp_path)
    comparisons = {
        comparison["metric_name"]: comparison
        for comparison in artifact["documents"][0]["comparisons"]
    }

    assert comparisons["cash_end"]["status"] == "expected_null_respected"
    assert comparisons["cash_end"]["candidate_value"] is None
    assert artifact["documents"][0]["missing_count"] > 0


def test_run_manifest_to_artifact_writes_json(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    manifest_path = tmp_path / "manifest.json"
    output_path = tmp_path / "artifact.json"
    _write_json(fixture_path, _gold_fixture())
    _write_json(manifest_path, {"documents": [_appendix5b_document(str(fixture_path))]})

    artifact = run_manifest_to_artifact(
        manifest_path=manifest_path,
        output_path=output_path,
        repo_root=tmp_path,
        generated_at="2026-05-16T00:00:00+00:00",
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved == artifact
    assert saved["summary"]["match"] == 4
