from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.asx_appendix5b_manifest_builder import (
    DATA_MISSING,
    build_manifest_from_gold_fixtures,
    parse_structured_source_args,
    write_data_missing_artifact,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _gold_payload(**overrides: object) -> dict:
    payload = {
        "document_id": "gre_q4_fy2025_appendix5b",
        "ticker": "GRE",
        "period_type": "Q",
        "period_end": "2024-12-31",
        "pdf_path": "data/asx/docs/GRE/report.pdf",
        "metrics": {"operating_cf": -450000},
        "expected_nulls": ["revenue"],
    }
    payload.update(overrides)
    return payload


def _structured_payload() -> dict:
    return {
        "extraction_method": "docling",
        "tables": [
            {
                "page_number": 12,
                "caption": "Appendix 5B quarterly cash flow report",
                "headers": ["Item", "Description", "Current quarter $A'000"],
                "rows": [
                    ["Item", "Description", "Current quarter $A'000"],
                    ["1.9", "Net cash from / (used in) operating activities", "(450)"],
                ],
            }
        ],
        "sections": [],
    }


def test_build_manifest_uses_explicit_structured_source(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    structured_path = tmp_path / "structured" / "gre.docling.json"
    _write_json(fixture_path, _gold_payload())
    _write_json(structured_path, _structured_payload())

    manifest = build_manifest_from_gold_fixtures(
        gold_fixture_paths=[fixture_path],
        repo_root=tmp_path,
        structured_sources={"gre_q4_fy2025_appendix5b": structured_path},
        generated_at="2026-05-16T00:00:00+00:00",
    )

    assert manifest["canonical_write"] is False
    assert manifest["summary"] == {
        "documents_requested": 1,
        "documents_ready": 1,
        "documents_skipped": 0,
        "tables_ready": 1,
    }
    document = manifest["documents"][0]
    assert document["gold_fixture_path"] == "fixtures/gre.json"
    assert document["structured_source_path"] == "structured/gre.docling.json"
    assert document["structured_source_type"] == "explicit_structured_json"
    assert document["tables"][0]["rows"][1] == [
        "1.9",
        "Net cash from / (used in) operating activities",
        "(450)",
    ]


def test_build_manifest_uses_existing_docling_cache_next_to_pdf(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    pdf_path = tmp_path / "data" / "asx" / "docs" / "GRE" / "report.pdf"
    cache_path = Path(str(pdf_path) + ".docling.json")
    _write_json(fixture_path, _gold_payload())
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")
    _write_json(cache_path, _structured_payload())

    manifest = build_manifest_from_gold_fixtures(
        gold_fixture_paths=[fixture_path],
        repo_root=tmp_path,
    )

    assert manifest["summary"]["documents_ready"] == 1
    assert manifest["documents"][0]["structured_source_type"] == "docling_cache"


def test_build_manifest_reports_data_missing_when_no_source_exists(tmp_path: Path) -> None:
    fixture_path = tmp_path / "fixtures" / "gre.json"
    _write_json(fixture_path, _gold_payload())

    manifest = build_manifest_from_gold_fixtures(
        gold_fixture_paths=[fixture_path],
        repo_root=tmp_path,
    )

    assert manifest["documents"] == []
    assert manifest["summary"]["documents_skipped"] == 1
    skipped = manifest["skipped_documents"][0]
    assert skipped["status"] == DATA_MISSING
    assert "no explicit structured JSON" in skipped["failure_reason"]
    assert any(path.endswith("report.pdf.docling.json") for path in skipped["checked_paths"])


def test_write_data_missing_artifact_preserves_blockers(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    manifest = {
        "run_id": "unit",
        "summary": {"documents_requested": 1, "documents_ready": 0, "documents_skipped": 1},
        "skipped_documents": [{"document_id": "missing", "status": DATA_MISSING}],
    }

    artifact = write_data_missing_artifact(artifact_path, manifest)

    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert saved == artifact
    assert saved["status"] == DATA_MISSING
    assert saved["canonical_write"] is False
    assert saved["skipped_documents"] == [{"document_id": "missing", "status": DATA_MISSING}]


def test_parse_structured_source_args_validates_shape() -> None:
    parsed = parse_structured_source_args(["doc1=/tmp/doc1.json"])
    assert parsed == {"doc1": Path("/tmp/doc1.json")}

    with pytest.raises(ValueError, match="document_id=path"):
        parse_structured_source_args(["/tmp/doc1.json"])
