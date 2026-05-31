from __future__ import annotations

import json
from pathlib import Path

from scripts.reporting import offline_artifact_authority as authority


def test_build_authority_metadata_marks_report_local_only(tmp_path: Path) -> None:
    source = tmp_path / "selected_rows.json"
    source.write_text(json.dumps([{"metric": "revenue"}]) + "\n", encoding="utf-8")

    metadata = authority.build_authority_metadata(
        artifact_type="test_report",
        producer="scripts/test.py",
        lane="Evaluation",
        source_artifacts=[authority.artifact_record(source, "report_local_selected_rows")],
    )

    assert authority.validate_authority_metadata(metadata) == []
    assert metadata["lane"] == "Evaluation"
    assert metadata["truth_status"] == "report_local_only"
    assert metadata["canonical_financial_truth"] is False
    assert metadata["canonical_write_allowed"] is False
    assert metadata["broad_backfill_authorized"] is False
    assert metadata["source_artifacts"][0]["sha256"]
    assert metadata["do_not_overclaim"]


def test_write_authority_manifest_rejects_missing_truth_flags(tmp_path: Path) -> None:
    manifest_path = tmp_path / "authority.json"
    metadata = {
        "artifact_authority_version": authority.AUTHORITY_VERSION,
        "truth_status": "report_local_only",
        "source_artifacts": [],
        "do_not_overclaim": ["test"],
    }

    try:
        authority.write_authority_manifest(manifest_path, metadata)
    except ValueError as exc:
        assert "canonical_financial_truth" in str(exc)
    else:
        raise AssertionError("invalid authority metadata should fail")
