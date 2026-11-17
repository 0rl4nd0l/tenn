from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.evaluate_youtube_intake_quality import (
    DECISIONS,
    REQUIRED_CASE_IDS,
    evaluate_cases,
    evaluate_fixture_file,
    validate_results,
)


FIXTURE_PATH = Path("financial-engine_v2/backend/tests/fixtures/youtube_intake_quality/matrix.json")
SCRIPT_PATH = Path("scripts/evaluate_youtube_intake_quality.py")


def test_fixture_matrix_covers_required_decisions():
    report = evaluate_fixture_file(FIXTURE_PATH)

    assert report["ok"] is True
    case_ids = {case["id"] for case in report["cases"]}
    assert REQUIRED_CASE_IDS <= case_ids
    assert {case["decision"] for case in report["cases"]} <= DECISIONS
    assert report["decision_counts"] == {
        "factual_candidate": 1,
        "quarantine": 1,
        "reject": 2,
        "requires_user_review": 2,
        "speculative_candidate": 1,
    }
    assert all(case["matches_expected"] for case in report["cases"])


def test_each_decision_exposes_memory_routing_evidence():
    report = evaluate_fixture_file(FIXTURE_PATH)

    for case in report["cases"]:
        evidence = case["evidence"]
        routing = case["routing_fields"]
        assert "has_transcript" in evidence
        assert "transcript_chars" in evidence
        assert "tickers" in evidence
        assert "factual_signal_count" in evidence
        assert "speculative_signal_count" in evidence
        assert routing["may_write_memory"] is False
        assert routing["candidate_kind"] in {"none", "review", "factual", "speculative"}


def test_speculative_takeaways_are_not_factual_candidates():
    report = evaluate_fixture_file(FIXTURE_PATH)

    for case in report["cases"]:
        if case["evidence"]["speculative_signal_count"]:
            assert case["decision"] != "factual_candidate"

    bad_report = [
        {
            "id": "bad-speculative",
            "decision": "factual_candidate",
            "expected_decision": "factual_candidate",
            "evidence": {"speculative_signal_count": 1},
            "routing_fields": {"may_write_memory": False},
        }
    ]
    validation = validate_results(bad_report)
    assert validation["ok"] is False
    assert {
        "id": "bad-speculative",
        "error": "speculative_as_factual_candidate",
    } in validation["errors"]


def test_eval_cli_writes_json_report(tmp_path):
    output = tmp_path / "youtube_intake_quality_eval.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--fixtures",
            str(FIXTURE_PATH),
            "--out-json",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert len(report["cases"]) == len(REQUIRED_CASE_IDS)


def test_expected_decision_mismatch_fails_eval():
    cases = [
        {
            "id": "ticker_speculative",
            "video": {"duration_seconds": 120, "access_status": "public"},
            "transcript_text": "I think BHP could 10x. This is not financial advice.",
            "ticker_allowlist": ["BHP"],
            "expected_decision": "factual_candidate",
        },
        {
            "id": "no_transcript",
            "transcript_text": "",
            "expected_decision": "reject",
        },
        {
            "id": "members_only",
            "access_status": "members_only",
            "expected_decision": "reject",
        },
        {
            "id": "short_incomplete",
            "duration_seconds": 1560,
            "transcript_text": "BHP reported a short fragment.",
            "expected_decision": "quarantine",
        },
        {
            "id": "generic_low_signal",
            "duration_seconds": 120,
            "transcript_text": "Generic market talk with no concrete company evidence.",
            "expected_decision": "requires_user_review",
        },
        {
            "id": "ticker_factual",
            "duration_seconds": 120,
            "transcript_text": "BHP reported quarterly production and cash flow growth.",
            "ticker_allowlist": ["BHP"],
            "expected_decision": "factual_candidate",
        },
        {
            "id": "mixed_factual_speculative",
            "duration_seconds": 120,
            "transcript_text": "BHP reported results and could double if copper rises.",
            "ticker_allowlist": ["BHP"],
            "expected_decision": "requires_user_review",
        },
    ]

    report = evaluate_cases(cases)

    assert report["ok"] is False
    assert any(
        error["id"] == "ticker_speculative"
        and error["error"] == "decision_mismatch"
        for error in report["validation"]["errors"]
    )
