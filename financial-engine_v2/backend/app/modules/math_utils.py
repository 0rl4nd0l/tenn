"""math_utils.py — Null-safe financial math utilities.

Shared across all analysis modules. Every function handles None inputs
gracefully — returns None rather than raising. No fabrication of values.
"""
from __future__ import annotations

import math
from typing import Any, Sequence


def coerce(value: Any) -> float | None:
    """Coerce a DB Decimal / int / str to float, return None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ratio(
    numerator: float | None,
    denominator: float | None,
) -> float | None:
    """Safe division. Returns None if either is absent or denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def pct_change(
    new: float | None,
    old: float | None,
) -> float | None:
    """Percentage change from old to new. Returns None on missing/zero old."""
    if new is None or old is None or old == 0:
        return None
    return (new - old) / abs(old)


def safe_abs(value: float | None) -> float | None:
    """Absolute value, None-safe."""
    if value is None:
        return None
    return abs(value)


def safe_sub(a: float | None, b: float | None) -> float | None:
    """a - b, None-safe."""
    if a is None or b is None:
        return None
    return a - b


def safe_add(a: float | None, b: float | None) -> float | None:
    """a + b, None-safe."""
    if a is None or b is None:
        return None
    return a + b


def safe_mul(a: float | None, b: float | None) -> float | None:
    """a * b, None-safe."""
    if a is None or b is None:
        return None
    return a * b


# ---------------------------------------------------------------------------
# Aggregate statistics
# ---------------------------------------------------------------------------


def mean(values: Sequence[float | None]) -> float | None:
    """Mean of non-None values. Returns None if empty."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def stdev(values: Sequence[float | None]) -> float | None:
    """Population standard deviation of non-None values. None if < 2 values."""
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return None
    avg = sum(clean) / len(clean)
    variance = sum((x - avg) ** 2 for x in clean) / len(clean)
    return math.sqrt(variance)


def linear_slope(values: Sequence[float | None]) -> float | None:
    """Simple linear regression slope over evenly-spaced values.

    Returns change per period. None if < 2 non-None values.
    """
    clean = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(clean) < 2:
        return None
    n = len(clean)
    sum_x = sum(x for x, _ in clean)
    sum_y = sum(y for _, y in clean)
    sum_xy = sum(x * y for x, y in clean)
    sum_x2 = sum(x * x for x, _ in clean)
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return None
    return (n * sum_xy - sum_x * sum_y) / denom


# ---------------------------------------------------------------------------
# Trend helpers
# ---------------------------------------------------------------------------


def count_consecutive_from_end(
    values: Sequence[bool | None],
    target: bool = True,
) -> int:
    """Count consecutive target values from the end of the sequence."""
    count = 0
    for v in reversed(values):
        if v is target:
            count += 1
        else:
            break
    return count


def classify_direction(
    values: Sequence[float | None],
    threshold_pct: float = 0.05,
) -> str:
    """Classify a series direction as improving/stable/deteriorating.

    Based on overall change from first to last non-None value.
    """
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return "insufficient_data"
    change = pct_change(clean[-1], clean[0])
    if change is None:
        return "insufficient_data"
    if change > threshold_pct:
        return "improving"
    if change < -threshold_pct:
        return "deteriorating"
    return "stable"


def round_or_none(value: float | None, decimals: int = 4) -> float | None:
    """Round a float, None-safe."""
    if value is None:
        return None
    return round(value, decimals)
