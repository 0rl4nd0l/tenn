#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DECISIONS = {
    "reject",
    "quarantine",
    "factual_candidate",
    "speculative_candidate",
    "requires_user_review",
}
REQUIRED_CASE_IDS = {
    "no_transcript",
    "members_only",
    "short_incomplete",
    "generic_low_signal",
    "ticker_factual",
    "ticker_speculative",
    "mixed_factual_speculative",
}
MIN_CHARS_PER_SECOND = 2.0
TICKER_STOPWORDS = {
    "ASX",
    "CEO",
    "CFO",
    "EPS",
    "FY",
    "H1",
    "H2",
    "IPO",
    "IRR",
    "NTA",
    "ROE",
}
FACTUAL_PATTERNS = (
    r"\breported\b",
    r"\bannounced\b",
    r"\bquarterly\b",
    r"\bresults?\b",
    r"\bproduction\b",
    r"\brevenue\b",
    r"\bcash flow\b",
    r"\bmargin\b",
    r"\bcosts?\b",
    r"\bdividend\b",
    r"\bcapex\b",
    r"\bguidance\b",
)
SPECULATIVE_PATTERNS = (
    r"\bi think\b",
    r"\bi believe\b",
    r"\bcould\b",
    r"\bmight\b",
    r"\bmay\b",
    r"\bif\b",
    r"\bmy thesis\b",
    r"\bprice target\b",
    r"\bbull case\b",
    r"\bbear case\b",
    r"\b10x\b",
    r"\bten[- ]?bagger\b",
    r"\bnot financial advice\b",
)


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        coerced = int(float(value))
    except (TypeError, ValueError):
        return None
    return coerced if coerced >= 0 else None


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _pattern_hits(text: str, patterns: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, lowered):
            hits.append(pattern.strip("\\b"))
    return hits


def _extract_tickers(text: str, allowlist: list[str] | None = None) -> list[str]:
    candidates = {
        token
        for token in re.findall(r"\b[A-Z]{2,5}\b", text)
        if token not in TICKER_STOPWORDS
    }
    if allowlist is not None:
        allowed = {str(item or "").upper() for item in allowlist}
        candidates = candidates & allowed
    return sorted(candidates)


def _candidate_kind(decision: str) -> str:
    if decision == "factual_candidate":
        return "factual"
    if decision == "speculative_candidate":
        return "speculative"
    if decision == "requires_user_review":
        return "review"
    return "none"


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("id") or "").strip()
    video = case.get("video") if isinstance(case.get("video"), dict) else {}
    transcript = _clean_text(case.get("transcript_text"))
    access_status = str(case.get("access_status") or video.get("access_status") or "").strip()
    duration_seconds = _coerce_int(case.get("duration_seconds") or video.get("duration_seconds"))
    chars = len(transcript)
    chars_per_second = (
        round(chars / duration_seconds, 3)
        if duration_seconds and duration_seconds > 0
        else None
    )
    allowlist = case.get("ticker_allowlist")
    tickers = _extract_tickers(transcript, allowlist if isinstance(allowlist, list) else None)
    factual_hits = _pattern_hits(transcript, FACTUAL_PATTERNS)
    speculative_hits = _pattern_hits(transcript, SPECULATIVE_PATTERNS)

    if access_status == "members_only":
        decision = "reject"
        reason = "members_only"
    elif not transcript:
        decision = "reject"
        reason = "transcript_missing"
    elif duration_seconds and chars_per_second is not None and chars_per_second < MIN_CHARS_PER_SECOND:
        decision = "quarantine"
        reason = "transcript_incomplete"
    elif factual_hits and speculative_hits:
        decision = "requires_user_review"
        reason = "mixed_factual_and_speculative"
    elif speculative_hits:
        decision = "speculative_candidate"
        reason = "speculative_signals"
    elif factual_hits and tickers:
        decision = "factual_candidate"
        reason = "ticker_factual_signals"
    else:
        decision = "requires_user_review"
        reason = "low_signal_or_no_ticker"

    expected_decision = str(case.get("expected_decision") or "").strip()
    return {
        "id": case_id,
        "description": str(case.get("description") or "").strip(),
        "decision": decision,
        "expected_decision": expected_decision or None,
        "matches_expected": not expected_decision or decision == expected_decision,
        "reason": reason,
        "evidence": {
            "has_transcript": bool(transcript),
            "access_status": access_status or "public",
            "transcript_chars": chars,
            "duration_seconds": duration_seconds,
            "chars_per_second": chars_per_second,
            "tickers": tickers,
            "factual_signals": factual_hits,
            "factual_signal_count": len(factual_hits),
            "speculative_signals": speculative_hits,
            "speculative_signal_count": len(speculative_hits),
        },
        "routing_fields": {
            "candidate_kind": _candidate_kind(decision),
            "may_write_memory": False,
            "requires_user_approval": decision in {
                "factual_candidate",
                "speculative_candidate",
                "requires_user_review",
            },
            "source_issue": "refs #100",
        },
    }


def validate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    case_ids = {str(row.get("id") or "") for row in results}
    for missing in sorted(REQUIRED_CASE_IDS - case_ids):
        errors.append({"id": missing, "error": "required_case_missing"})

    for row in results:
        case_id = str(row.get("id") or "")
        decision = str(row.get("decision") or "")
        expected = row.get("expected_decision")
        evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        routing = row.get("routing_fields") if isinstance(row.get("routing_fields"), dict) else {}

        if decision not in DECISIONS:
            errors.append({"id": case_id, "error": "unknown_decision", "decision": decision})
        if expected and decision != expected:
            errors.append(
                {
                    "id": case_id,
                    "error": "decision_mismatch",
                    "expected": expected,
                    "actual": decision,
                }
            )
        if decision == "factual_candidate" and int(evidence.get("speculative_signal_count") or 0) > 0:
            errors.append({"id": case_id, "error": "speculative_as_factual_candidate"})
        if routing.get("may_write_memory") is not False:
            errors.append({"id": case_id, "error": "memory_write_not_fail_closed"})

    return {"ok": not errors, "errors": errors}


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = [evaluate_case(case) for case in cases]
    validation = validate_results(results)
    counts = Counter(str(row.get("decision") or "") for row in results)
    return {
        "schema_version": 1,
        "ok": validation["ok"],
        "decision_counts": dict(sorted(counts.items())),
        "required_case_ids": sorted(REQUIRED_CASE_IDS),
        "validation": validation,
        "cases": results,
    }


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        cases = payload.get("cases")
    else:
        cases = payload
    if not isinstance(cases, list):
        raise ValueError("fixture file must contain a list or a JSON object with cases")
    return [dict(case) for case in cases if isinstance(case, dict)]


def evaluate_fixture_file(path: str | Path) -> dict[str, Any]:
    return evaluate_cases(load_cases(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate YouTube intake quality fixtures.")
    parser.add_argument("--fixtures", required=True, help="Path to fixture JSON.")
    parser.add_argument("--out-json", help="Optional path for the eval report JSON.")
    args = parser.parse_args(argv)

    report = evaluate_fixture_file(args.fixtures)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out_json:
        output_path = Path(args.out_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
