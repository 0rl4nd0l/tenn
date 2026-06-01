import json
from pathlib import Path

import pytest

from rekey_real_gold_actuals_by_source_document import (
    rekey_actuals_by_source_document,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_rekeys_actual_payload_by_fixture_source_document_id(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    source_document_id = "11111111-2222-3333-4444-555555555555"
    _write_json(
        fixtures_dir / "fixture.json",
        {
            "document_id": "fixture_doc",
            "source_document_id": source_document_id,
            "period_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "units",
            "metrics": {"revenue": 100},
        },
    )
    actuals_path = tmp_path / "actuals.json"
    _write_json(
        actuals_path,
        {
            source_document_id: {
                "period_type": "H",
                "period_end": "2025-12-31",
                "currency": "AUD",
                "scale": "units",
                "metrics": {"revenue": 100},
            }
        },
    )

    keyed, summary = rekey_actuals_by_source_document(
        fixtures_dir=fixtures_dir,
        actuals_json=actuals_path,
        require_all_actuals_matched=True,
    )

    assert keyed == {
        "fixture_doc": {
            "period_type": "H",
            "period_end": "2025-12-31",
            "currency": "AUD",
            "scale": "units",
            "metrics": {"revenue": 100},
        }
    }
    assert summary["matched_actual_payload_count"] == 1
    assert summary["unmatched_actual_payload_ids"] == []
    assert summary["boundaries"]["canonical_write_allowed"] is False


def test_rekeys_actual_payload_by_run_provenance_document_id(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    source_document_id = "11111111222233334444555555555555"
    _write_json(
        fixtures_dir / "fixture.json",
        {
            "document_id": "fixture_doc",
            "source_document_id": source_document_id,
            "metrics": {"cash_end": 10},
        },
    )
    actuals_path = tmp_path / "actuals.json"
    _write_json(
        actuals_path,
        {
            "run-key": {
                "metrics": {"cash_end": 10},
                "extraction_run_provenance": {
                    "document_id": "11111111-2222-3333-4444-555555555555"
                },
            }
        },
    )

    keyed, summary = rekey_actuals_by_source_document(
        fixtures_dir=fixtures_dir,
        actuals_json=actuals_path,
    )

    assert set(keyed) == {"fixture_doc"}
    assert summary["matched_actuals"][0]["actual_key"] == "run-key"


def test_duplicate_fixture_source_document_id_fails_closed(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    for name in ("a.json", "b.json"):
        _write_json(
            fixtures_dir / name,
            {
                "document_id": name,
                "source_document_id": "11111111-2222-3333-4444-555555555555",
                "metrics": {"revenue": 1},
            },
        )
    actuals_path = tmp_path / "actuals.json"
    _write_json(actuals_path, {})

    with pytest.raises(ValueError, match="duplicate source_document_id"):
        rekey_actuals_by_source_document(
            fixtures_dir=fixtures_dir,
            actuals_json=actuals_path,
        )


def test_strict_mode_rejects_unmatched_actual_payload(tmp_path):
    fixtures_dir = tmp_path / "fixtures"
    _write_json(
        fixtures_dir / "fixture.json",
        {
            "document_id": "fixture_doc",
            "source_document_id": "11111111-2222-3333-4444-555555555555",
            "metrics": {"revenue": 1},
        },
    )
    actuals_path = tmp_path / "actuals.json"
    _write_json(
        actuals_path,
        {
            "99999999-2222-3333-4444-555555555555": {
                "metrics": {"revenue": 1}
            }
        },
    )

    with pytest.raises(ValueError, match="did not match"):
        rekey_actuals_by_source_document(
            fixtures_dir=fixtures_dir,
            actuals_json=actuals_path,
            require_all_actuals_matched=True,
        )
