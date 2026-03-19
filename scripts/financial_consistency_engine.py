#!/usr/bin/env python3
"""Cross-metric accounting consistency checks for extracted rows."""

from __future__ import annotations

import importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

try:
    from metric_ontology_mapper import canonicalize_metric_name
except Exception:
    _MODULE_PATH = Path(__file__).resolve().with_name("metric_ontology_mapper.py")
    _SPEC = importlib.util.spec_from_file_location("metric_ontology_mapper", str(_MODULE_PATH))
    if _SPEC is None or _SPEC.loader is None:
        raise RuntimeError(f"failed to load module: {_MODULE_PATH}")
    _MODULE = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_MODULE)
    canonicalize_metric_name = _MODULE.canonicalize_metric_name


def _row_group_key(row: Dict[str, object]) -> Tuple[str, str, str]:
    return (
        str(row.get("file") or row.get("source_file") or row.get("pdf_path") or "").strip(),
        str(row.get("statement_period_end") or row.get("period_end") or "").strip(),
        str(row.get("currency") or "").strip().upper(),
    )


def _tolerance(lhs: float, rhs: float, relative_tolerance: float, absolute_tolerance: float) -> float:
    return max(absolute_tolerance, relative_tolerance * max(abs(lhs), abs(rhs), 1.0))


def _check_identity(
    *,
    identity: str,
    left_value: float,
    right_value: float,
    context: Tuple[str, str, str],
    relative_tolerance: float,
    absolute_tolerance: float,
) -> Dict[str, object]:
    delta = left_value - right_value
    passed = abs(delta) <= _tolerance(left_value, right_value, relative_tolerance, absolute_tolerance)
    return {
        "identity": identity,
        "passed": passed,
        "expected": left_value,
        "actual": right_value,
        "delta": delta,
        "file": context[0],
        "statement_period_end": context[1],
        "currency": context[2],
    }


def evaluate_financial_consistency(
    rows: Sequence[Dict[str, object]],
    *,
    relative_tolerance: float = 0.02,
    absolute_tolerance: float = 1.0,
) -> Dict[str, object]:
    """Validate a small set of accounting identities across extracted rows."""
    grouped: Dict[Tuple[str, str, str], Dict[str, float]] = defaultdict(dict)

    for row in rows:
        period_end = str(row.get("statement_period_end") or row.get("period_end") or "").strip()
        if not period_end:
            continue
        metric_name = canonicalize_metric_name(row.get("metric_base") or row.get("metric"))
        if not metric_name:
            continue
        try:
            value = float(row.get("value", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        key = _row_group_key(dict(row))
        current = grouped[key].get(metric_name)
        if current is None:
            grouped[key][metric_name] = value

    checks: List[Dict[str, object]] = []
    failed_checks: List[Dict[str, object]] = []

    for context, metrics in grouped.items():
        if {"ebitda", "depreciation_and_amortisation", "ebit"} <= metrics.keys():
            left = float(metrics["ebitda"]) - abs(float(metrics["depreciation_and_amortisation"]))
            right = float(metrics["ebit"])
            check = _check_identity(
                identity="ebitda_minus_depreciation_equals_ebit",
                left_value=left,
                right_value=right,
                context=context,
                relative_tolerance=relative_tolerance,
                absolute_tolerance=absolute_tolerance,
            )
            checks.append(check)
            if not check["passed"]:
                failed_checks.append(check)

        if {"total_assets", "total_liabilities", "total_equity"} <= metrics.keys():
            left = float(metrics["total_assets"])
            right = float(metrics["total_liabilities"]) + float(metrics["total_equity"])
            check = _check_identity(
                identity="assets_equals_liabilities_plus_equity",
                left_value=left,
                right_value=right,
                context=context,
                relative_tolerance=relative_tolerance,
                absolute_tolerance=absolute_tolerance,
            )
            checks.append(check)
            if not check["passed"]:
                failed_checks.append(check)

        if {"operating_cash_flow", "capital_expenditure", "free_cash_flow"} <= metrics.keys():
            ocf = float(metrics["operating_cash_flow"])
            capex = abs(float(metrics["capital_expenditure"]))
            right = float(metrics["free_cash_flow"])
            check = _check_identity(
                identity="ocf_minus_capex_equals_fcf",
                left_value=ocf - capex,
                right_value=right,
                context=context,
                relative_tolerance=relative_tolerance,
                absolute_tolerance=absolute_tolerance,
            )
            checks.append(check)
            if not check["passed"]:
                failed_checks.append(check)

    return {
        "passed": len(failed_checks) == 0,
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_reasons": [str(check["identity"]) for check in failed_checks],
        "groups_evaluated": len(grouped),
        "checks_evaluated": len(checks),
    }
