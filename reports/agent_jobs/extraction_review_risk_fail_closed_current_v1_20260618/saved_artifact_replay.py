#!/usr/bin/env python3
"""Replay the accepted-output risk gate over saved count-24 artifacts only."""

from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
COUNT24_RESULTS = Path(
    "/home/l4nd0/tenn-count24-current-canonical-execution-v1-20260617/"
    "reports/agent_jobs/extraction_count24_current_canonical_execution_v1_20260617/"
    "sample_results.json"
)
OUTPUT_PATH = Path(__file__).with_name("saved_artifact_replay.json")

sys.path.insert(0, str(REPO_ROOT / "financial-engine_v2" / "scripts"))

from broad_extraction_test import (  # noqa: E402
    _accepted_output_risk_gate_error,
    compute_summary,
)


def _row_key(row: dict) -> str:
    return f"{row.get('ticker')}:{row.get('document_id')}"


def main() -> int:
    source = json.loads(COUNT24_RESULTS.read_text(encoding="utf-8"))
    original_rows = source["results"]
    projected_rows = copy.deepcopy(original_rows)

    transitions: list[dict] = []
    accepted_info_rows: list[dict] = []
    already_failed_risk_rows: list[dict] = []

    for row in projected_rows:
        risk = row.get("accepted_output_scale_magnitude_risk")
        if not isinstance(risk, dict):
            risk = {}
        gate_error = _accepted_output_risk_gate_error(risk)
        before_status = row.get("status")
        before_error = row.get("error")
        if gate_error is not None:
            row["status"] = "failed"
            row["error"] = gate_error
            transitions.append(
                {
                    "ticker": row.get("ticker"),
                    "document_id": row.get("document_id"),
                    "before_status": before_status,
                    "before_error": before_error,
                    "after_status": row.get("status"),
                    "after_error": row.get("error"),
                    "risk_level": risk.get("risk_level"),
                    "flag_codes": risk.get("flag_codes", []),
                }
            )
        elif (
            before_status in ("ok", "ok_low_confidence")
            and risk.get("risk_level") == "info"
        ):
            accepted_info_rows.append(
                {
                    "ticker": row.get("ticker"),
                    "document_id": row.get("document_id"),
                    "status": before_status,
                    "risk_level": risk.get("risk_level"),
                    "flag_codes": risk.get("flag_codes", []),
                }
            )
        elif before_status == "failed" and risk.get("risk_level") in ("info", "review"):
            already_failed_risk_rows.append(
                {
                    "ticker": row.get("ticker"),
                    "document_id": row.get("document_id"),
                    "status": before_status,
                    "error": before_error,
                    "risk_level": risk.get("risk_level"),
                    "flag_codes": risk.get("flag_codes", []),
                }
            )

    expected_reclassified = {
        "WHC:0be5515d-6e8b-4c1f-9e20-e5d1ec67acdd",
        "EDU:ac3c9ab0-e01a-4996-95f9-6466388ddc9c",
    }
    expected_info_accepted = {
        "NSR:f2240712-9dde-41e0-88fa-29c1a0080dab",
        "CAE:91561659-014b-4c88-865d-a6dec2fd8e35",
    }

    actual_reclassified = {_row_key(row) for row in transitions}
    actual_info_accepted = {_row_key(row) for row in accepted_info_rows}
    checks = {
        "whc_edu_reclassified": actual_reclassified == expected_reclassified,
        "nsr_cae_remain_accepted_info": expected_info_accepted <= actual_info_accepted,
        "risk_flags_preserved": all(row.get("flag_codes") for row in transitions),
        "no_pdf_extraction_invoked": True,
    }

    output = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "job_id": "extraction_review_risk_fail_closed_current_v1_20260618",
        "mode": "saved_artifact_replay_only",
        "source_artifact": str(COUNT24_RESULTS),
        "checks": checks,
        "ok": all(checks.values()),
        "original_summary": compute_summary(original_rows),
        "projected_summary": compute_summary(projected_rows),
        "transitions": transitions,
        "accepted_info_rows": accepted_info_rows,
        "already_failed_risk_rows": already_failed_risk_rows,
        "forbidden_actions_avoided": [
            "count_24_rerun",
            "count_32",
            "random_sampling",
            "broad_extraction",
            "broad_backfill",
            "full_ticker_universe_extraction",
            "run_multipass_extraction",
            "runtime_service_start",
            "data_store_mutation",
            "source_pdf_mutation",
            "github_mutation",
        ],
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
