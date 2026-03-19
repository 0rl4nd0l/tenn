#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from services.evaluation.normalizer import normalize_metric_payload, rows_to_canonical_metrics


EXACT_MATCH = "EXACT_MATCH"
TOLERANCE_MATCH = "TOLERANCE_MATCH"
MISSING = "MISSING"
INCORRECT = "INCORRECT"


def _tolerance_for_value(gold_value: float, tolerance_pct: float) -> float:
    if math.isclose(gold_value, 0.0, rel_tol=0.0, abs_tol=0.0):
        return 0.0
    return abs(float(gold_value)) * float(tolerance_pct)


def score_metric_maps(
    predicted_metrics: Mapping[str, Any],
    ground_truth_metrics: Mapping[str, Any],
    *,
    tolerance_pct: float = 0.02,
) -> dict[str, Any]:
    predicted = normalize_metric_payload(predicted_metrics)
    gold = normalize_metric_payload(ground_truth_metrics)
    expected_metrics = sorted(gold.keys())

    if not expected_metrics:
        return {
            "status": "DATA_MISSING",
            "metric_count": 0,
            "aggregate": {
                "accuracy": 0.0,
                "completeness": 0.0,
                "exact_match_rate": 0.0,
                "tolerance_match_rate": 0.0,
            },
            "counts": {
                EXACT_MATCH: 0,
                TOLERANCE_MATCH: 0,
                MISSING: 0,
                INCORRECT: 0,
            },
            "per_metric": {},
        }

    counts = {
        EXACT_MATCH: 0,
        TOLERANCE_MATCH: 0,
        MISSING: 0,
        INCORRECT: 0,
    }
    per_metric: dict[str, dict[str, Any]] = {}

    for metric in expected_metrics:
        gold_value = float(gold[metric])
        predicted_value = predicted.get(metric)
        if predicted_value is None:
            counts[MISSING] += 1
            per_metric[metric] = {
                "status": MISSING,
                "gold_value": gold_value,
                "predicted_value": None,
                "difference": None,
                "tolerance": _tolerance_for_value(gold_value, tolerance_pct),
            }
            continue

        predicted_float = float(predicted_value)
        difference = predicted_float - gold_value
        tolerance = _tolerance_for_value(gold_value, tolerance_pct)
        if math.isclose(predicted_float, gold_value, rel_tol=0.0, abs_tol=0.0):
            status = EXACT_MATCH
        elif abs(difference) <= tolerance:
            status = TOLERANCE_MATCH
        else:
            status = INCORRECT
        counts[status] += 1
        per_metric[metric] = {
            "status": status,
            "gold_value": gold_value,
            "predicted_value": predicted_float,
            "difference": difference,
            "tolerance": tolerance,
        }

    total = float(len(expected_metrics))
    matched = float(counts[EXACT_MATCH] + counts[TOLERANCE_MATCH])
    observed = float(len(expected_metrics) - counts[MISSING])

    return {
        "status": "SUCCESS",
        "metric_count": int(total),
        "aggregate": {
            "accuracy": round(matched / total, 6),
            "completeness": round(observed / total, 6),
            "exact_match_rate": round(float(counts[EXACT_MATCH]) / total, 6),
            "tolerance_match_rate": round(float(counts[TOLERANCE_MATCH]) / total, 6),
        },
        "counts": counts,
        "per_metric": per_metric,
    }


def score_rows(
    predicted_rows: Sequence[Mapping[str, Any]],
    ground_truth_metrics: Mapping[str, Any],
    *,
    tolerance_pct: float = 0.02,
) -> dict[str, Any]:
    predicted_metrics = rows_to_canonical_metrics(predicted_rows)
    score = score_metric_maps(
        predicted_metrics,
        ground_truth_metrics,
        tolerance_pct=tolerance_pct,
    )
    score["predicted_metrics"] = predicted_metrics
    return score
