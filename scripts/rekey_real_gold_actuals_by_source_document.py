#!/usr/bin/env python3
"""Rekey real-gold actual payloads by source document id.

The real-gold evaluator scores payloads by fixture ``document_id``. Runtime
exports are usually keyed by backend source document id. This helper bridges
that gap by reading fixture metadata and producing a new actual-payload map
keyed by the matching real-gold fixture ids.

It does not run extraction, create labels, or authorize canonical writes.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any, Mapping


SUMMARY_ARTIFACT_TYPE = "real_gold_source_document_actual_rekey_summary_v1"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Map actual payloads keyed by source document id to real-gold "
            "fixture document ids."
        )
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        required=True,
        help="Directory containing real-gold fixture JSON files.",
    )
    parser.add_argument(
        "--actuals-json",
        type=Path,
        required=True,
        help="JSON object mapping source document id -> extracted payload.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        required=True,
        help="Output JSON object keyed by real-gold fixture document_id.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional summary artifact path.",
    )
    parser.add_argument(
        "--require-all-actuals-matched",
        action="store_true",
        help="Fail if any supplied actual payload cannot be matched to a fixture.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation for output files.",
    )
    return parser.parse_args()


def _normalize_identifier(raw: Any) -> str:
    return str(raw or "").strip().lower().replace("-", "")


def _display_identifier(raw: Any) -> str:
    value = str(raw or "").strip()
    normalized = _normalize_identifier(value)
    if len(normalized) == 32:
        try:
            return str(uuid.UUID(hex=normalized))
        except ValueError:
            return value
    return value


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return data


def _load_fixture_source_map(fixtures_dir: Path) -> dict[str, dict[str, str]]:
    if not fixtures_dir.exists():
        raise FileNotFoundError(f"fixture directory not found: {fixtures_dir}")

    source_map: dict[str, dict[str, str]] = {}
    for fixture_path in sorted(fixtures_dir.glob("*.json")):
        fixture = _load_json_object(fixture_path, label="fixture")
        fixture_id = str(fixture.get("document_id") or fixture_path.stem)
        source_document_id = fixture.get("source_document_id")
        if not source_document_id:
            continue
        source_key = _normalize_identifier(source_document_id)
        if not source_key:
            continue
        if source_key in source_map:
            existing = source_map[source_key]
            raise ValueError(
                "duplicate source_document_id "
                f"{_display_identifier(source_document_id)} in "
                f"{existing['fixture_file']} and {fixture_path}"
            )
        source_map[source_key] = {
            "fixture_id": fixture_id,
            "fixture_file": str(fixture_path),
            "source_document_id": _display_identifier(source_document_id),
        }
    return source_map


def _actual_source_candidates(
    actual_key: str,
    payload: Mapping[str, Any],
) -> list[str]:
    candidates = [actual_key]
    direct_source = payload.get("source_document_id")
    if direct_source:
        candidates.append(str(direct_source))

    run_provenance = payload.get("extraction_run_provenance")
    if isinstance(run_provenance, Mapping):
        run_document_id = run_provenance.get("document_id")
        if run_document_id:
            candidates.append(str(run_document_id))

    output: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = _normalize_identifier(candidate)
        if normalized and normalized not in seen:
            output.append(normalized)
            seen.add(normalized)
    return output


def rekey_actuals_by_source_document(
    *,
    fixtures_dir: Path,
    actuals_json: Path,
    require_all_actuals_matched: bool = False,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    fixture_source_map = _load_fixture_source_map(fixtures_dir)
    actuals_raw = _load_json_object(actuals_json, label="actuals")

    keyed_actuals: dict[str, dict[str, Any]] = {}
    matched: list[dict[str, str]] = []
    unmatched: list[str] = []

    for actual_key, raw_payload in actuals_raw.items():
        if not isinstance(raw_payload, dict):
            raise ValueError(f"actual payload for {actual_key!r} must be an object")
        fixture_match = None
        for candidate in _actual_source_candidates(actual_key, raw_payload):
            fixture_match = fixture_source_map.get(candidate)
            if fixture_match is not None:
                break
        if fixture_match is None:
            unmatched.append(_display_identifier(actual_key))
            continue

        fixture_id = fixture_match["fixture_id"]
        if fixture_id in keyed_actuals:
            raise ValueError(f"multiple actual payloads map to fixture {fixture_id}")
        keyed_actuals[fixture_id] = raw_payload
        matched.append(
            {
                "actual_key": _display_identifier(actual_key),
                "fixture_id": fixture_id,
                "source_document_id": fixture_match["source_document_id"],
                "fixture_file": fixture_match["fixture_file"],
            }
        )

    if require_all_actuals_matched and unmatched:
        raise ValueError(
            "actual payload(s) did not match a source_document_id fixture: "
            + ", ".join(sorted(unmatched))
        )

    matched_fixture_ids = set(keyed_actuals)
    fixtures_without_actuals = [
        entry["fixture_id"]
        for entry in fixture_source_map.values()
        if entry["fixture_id"] not in matched_fixture_ids
    ]
    summary = {
        "artifact_type": SUMMARY_ARTIFACT_TYPE,
        "fixtures_dir": str(fixtures_dir),
        "actuals_json": str(actuals_json),
        "fixture_source_document_count": len(fixture_source_map),
        "input_actual_payload_count": len(actuals_raw),
        "matched_actual_payload_count": len(keyed_actuals),
        "unmatched_actual_payload_count": len(unmatched),
        "unmatched_actual_payload_ids": sorted(unmatched),
        "fixtures_without_actual_count": len(fixtures_without_actuals),
        "fixtures_without_actual_ids": sorted(fixtures_without_actuals),
        "matched_actuals": sorted(matched, key=lambda item: item["fixture_id"]),
        "boundaries": {
            "ran_extraction": False,
            "created_gold_labels": False,
            "canonical_write_allowed": False,
            "broad_backfill_authorized": False,
        },
    }
    return keyed_actuals, summary


def _write_json(path: Path, payload: Mapping[str, Any], *, indent: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered_indent = None if indent <= 0 else indent
    path.write_text(
        json.dumps(payload, indent=rendered_indent, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    args = _parse_args()
    keyed_actuals, summary = rekey_actuals_by_source_document(
        fixtures_dir=args.fixtures_dir,
        actuals_json=args.actuals_json,
        require_all_actuals_matched=args.require_all_actuals_matched,
    )
    _write_json(args.out_json, keyed_actuals, indent=args.indent)
    if args.summary_json is not None:
        _write_json(args.summary_json, summary, indent=args.indent)
    print(f"Wrote real-gold keyed actuals: {args.out_json}")
    if args.summary_json is not None:
        print(f"Wrote rekey summary: {args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
