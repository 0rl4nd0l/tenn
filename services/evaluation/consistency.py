#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.evaluation.normalizer import normalize_numeric

_CONFLICT_DEMOTION_HINTS = (
    "canonical_conflict",
    "canonical_duplicate",
)


def _row_has_numeric(row: Mapping[str, Any]) -> bool:
    for key in ("value", "raw_value"):
        if normalize_numeric(row.get(key)) is not None:
            return True
    return False


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _line_index(canonical_rows: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in canonical_rows:
        try:
            line_no = int(row.get("line_no") or 0)
        except (TypeError, ValueError):
            continue
        if line_no <= 0:
            continue
        out[line_no] = dict(row)
    return out


def _is_conflict_demotion_row(row: Mapping[str, Any]) -> bool:
    reason = str(row.get("context_reason") or row.get("rejection_reason") or "").lower()
    return any(hint in reason for hint in _CONFLICT_DEMOTION_HINTS)


def compute_extraction_consistency_checks(
    *,
    selected_payload: Mapping[str, Any],
    verified_metrics: Mapping[str, Any],
    final_metrics: Mapping[str, Any],
    strict_truth_mode: bool,
) -> dict[str, Any]:
    """
    Cross-stage checks using row payloads already produced by benchmark/extraction
    plus verification and final metric maps.
    """
    flags: list[str] = []
    details: dict[str, Any] = {}

    canonical_rows = list(selected_payload.get("canonical_rows") or [])
    context_rows = list(selected_payload.get("context_rows") or [])
    rejected_rows = list(selected_payload.get("rejected_rows") or [])
    primary_rows = list(selected_payload.get("primary_rows") or [])

    verified = dict(verified_metrics or {})
    final = dict(final_metrics or {})

    final_keys = set(final.keys())
    verified_keys = set(verified.keys())

    missing_from_final = sorted(verified_keys - final_keys)
    if missing_from_final:
        flags.append("verified_metric_missing_from_final")
        details["verified_metric_missing_from_final"] = {
            "metrics": missing_from_final[:24],
            "count": len(missing_from_final),
        }

    unverified_final = sorted(final_keys - verified_keys)
    if strict_truth_mode and unverified_final:
        flags.append("final_metric_without_verified_evidence")
        details["final_metric_without_verified_evidence"] = {
            "metrics": unverified_final[:24],
            "count": len(unverified_final),
        }

    primary_without_numeric: list[dict[str, Any]] = []
    for row in primary_rows:
        if not _row_has_numeric(row):
            primary_without_numeric.append(
                {
                    "line_no": row.get("line_no"),
                    "metric": row.get("metric_base") or row.get("metric"),
                }
            )
    if primary_without_numeric:
        flags.append("canonical_primary_without_numeric")
        details["canonical_primary_without_numeric"] = {
            "rows": primary_without_numeric[:16],
            "count": len(primary_without_numeric),
        }

    by_line = _line_index(canonical_rows)
    demoted_pool: list[Mapping[str, Any]] = []
    demoted_pool.extend(r for r in context_rows if _is_conflict_demotion_row(r))
    demoted_pool.extend(r for r in rejected_rows if _is_conflict_demotion_row(r))

    numeric_demoted_label_winner = 0
    weaker_winner_count = 0
    sample_numeric_demotion: list[dict[str, Any]] = []
    sample_weaker_winner: list[dict[str, Any]] = []

    for row in demoted_pool:
        if not _row_has_numeric(row):
            continue
        try:
            wline = int(row.get("canonical_conflict_winner_line_no") or 0)
        except (TypeError, ValueError):
            wline = 0
        if wline <= 0:
            continue
        winner = by_line.get(wline)
        if winner is None:
            continue
        if not _row_has_numeric(winner):
            numeric_demoted_label_winner += 1
            if len(sample_numeric_demotion) < 8:
                sample_numeric_demotion.append(
                    {
                        "demoted_line": row.get("line_no"),
                        "winner_line": wline,
                        "metric": row.get("metric_base") or row.get("metric"),
                    }
                )

        loser_score = _safe_int(row.get("canonical_confidence_score"))
        winner_score = _safe_int(winner.get("canonical_confidence_score"))
        if loser_score > winner_score:
            weaker_winner_count += 1
            if len(sample_weaker_winner) < 8:
                sample_weaker_winner.append(
                    {
                        "demoted_line": row.get("line_no"),
                        "winner_line": wline,
                        "loser_score": loser_score,
                        "winner_score": winner_score,
                    }
                )

    if numeric_demoted_label_winner:
        flags.append("numeric_candidate_demoted_while_label_only_selected")
        details["numeric_candidate_demoted_while_label_only_selected"] = {
            "count": numeric_demoted_label_winner,
            "sample": sample_numeric_demotion,
        }

    if weaker_winner_count:
        flags.append("conflict_winner_is_weaker_than_loser")
        details["conflict_winner_is_weaker_than_loser"] = {
            "count": weaker_winner_count,
            "sample": sample_weaker_winner,
        }

    return {
        "has_inconsistency": bool(flags),
        "flags": sorted(set(flags)),
        "details": details,
    }
