#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


_METRIC_ALIASES = {
    "npat": "net_income",
    "net_cash_movement": "net_change_in_cash",
}


def _to_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _normalize_metric(metric: object) -> str:
    normalized = str(metric or "").strip().lower()
    return _METRIC_ALIASES.get(normalized, normalized)


def _statement_family(row: Dict[str, object]) -> str:
    family = str(row.get("statement_family", "")).strip().lower()
    if family:
        return family
    table_statement_type = str(row.get("table_statement_type", "")).strip().lower()
    if table_statement_type == "cash_flow_statement":
        return "cash_flow"
    if table_statement_type in {"income_statement", "balance_sheet"}:
        return table_statement_type
    statement_type = str(row.get("statement_type", "")).strip().lower()
    if statement_type == "cash_flow_statement":
        return "cash_flow"
    if statement_type in {"income_statement", "balance_sheet"}:
        return statement_type
    return ""


def _entity_key(row: Dict[str, object]) -> str:
    for key in ("company", "entity", "source_file", "file"):
        value = str(row.get(key, "")).strip()
        if value:
            if key in {"source_file", "file"}:
                path = Path(value)
                parent_name = str(path.parent.parent.name).strip() if len(path.parents) >= 2 else ""
                if parent_name:
                    return parent_name
            return value
    return ""


def _statement_period_key(row: Dict[str, object]) -> str:
    for key in ("statement_period_end", "period_end_date", "statement_period", "period"):
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def _statement_key(row: Dict[str, object]) -> Tuple[str, str, str, str]:
    return (
        _entity_key(row),
        _statement_period_key(row),
        _statement_family(row),
        str(row.get("definition_scope", "")).strip().lower() or "reported",
    )


def _duplicate_key(row: Dict[str, object]) -> Tuple[str, str, str, str, str]:
    statement_key = _statement_key(row)
    return statement_key + (_normalize_metric(row.get("metric_base") or row.get("metric")),)


def _candidate_metric_values(
    metric_rows: Dict[str, List[Dict[str, object]]],
    target_metric: str,
    target_row: Dict[str, object],
) -> Dict[str, List[float]]:
    values: Dict[str, List[float]] = {}
    for metric, rows in metric_rows.items():
        bucket: List[float] = []
        source_rows = [target_row] if metric == target_metric else rows
        for row in source_rows:
            parsed = _to_float(row.get("value"))
            if parsed is not None:
                bucket.append(parsed)
        values[metric] = bucket
    return values


def _min_relative_error(candidate: float, options: Iterable[float]) -> Optional[float]:
    best: Optional[float] = None
    for expected in options:
        diff = abs(candidate - expected)
        scale = max(1.0, abs(candidate), abs(expected))
        score = diff / scale
        if best is None or score < best:
            best = score
    return best


def _income_statement_errors(metric: str, candidate: float, values: Dict[str, List[float]]) -> List[float]:
    errors: List[float] = []

    if metric in {"ebit", "ebitda", "depreciation_and_amortisation"}:
        ebit_vals = values.get("ebit", [])
        ebitda_vals = values.get("ebitda", [])
        dep_vals = values.get("depreciation_and_amortisation", [])
        options: List[float] = []
        if metric == "ebit" and ebitda_vals and dep_vals:
            options = [ebitda + dep for ebitda in ebitda_vals for dep in dep_vals]
            options.extend(ebitda - abs(dep) for ebitda in ebitda_vals for dep in dep_vals)
        elif metric == "ebitda" and ebit_vals and dep_vals:
            options = [ebit - dep for ebit in ebit_vals for dep in dep_vals]
            options.extend(ebit + abs(dep) for ebit in ebit_vals for dep in dep_vals)
        elif metric == "depreciation_and_amortisation" and ebit_vals and ebitda_vals:
            options = [ebitda - ebit for ebitda in ebitda_vals for ebit in ebit_vals]
            options.extend(ebit - ebitda for ebitda in ebitda_vals for ebit in ebit_vals)
        error = _min_relative_error(candidate, options)
        if error is not None:
            errors.append(error)

    if metric in {"net_income", "pre_tax_income", "income_tax_expense"}:
        net_vals = values.get("net_income", [])
        pretax_vals = values.get("pre_tax_income", [])
        tax_vals = values.get("income_tax_expense", [])
        options = []
        if metric == "net_income" and pretax_vals and tax_vals:
            options = [pretax + tax for pretax in pretax_vals for tax in tax_vals]
            options.extend(pretax - abs(tax) for pretax in pretax_vals for tax in tax_vals)
        elif metric == "pre_tax_income" and net_vals and tax_vals:
            options = [net - tax for net in net_vals for tax in tax_vals]
            options.extend(net + abs(tax) for net in net_vals for tax in tax_vals)
        elif metric == "income_tax_expense" and net_vals and pretax_vals:
            options = [net - pretax for net in net_vals for pretax in pretax_vals]
            options.extend(pretax - net for net in net_vals for pretax in pretax_vals)
        error = _min_relative_error(candidate, options)
        if error is not None:
            errors.append(error)

    return errors


def _balance_sheet_errors(metric: str, candidate: float, values: Dict[str, List[float]]) -> List[float]:
    if metric not in {"total_assets", "total_liabilities", "total_equity"}:
        return []

    asset_vals = values.get("total_assets", [])
    liability_vals = values.get("total_liabilities", [])
    equity_vals = values.get("total_equity", [])
    options: List[float] = []

    if metric == "total_assets" and liability_vals and equity_vals:
        options = [liability + equity for liability in liability_vals for equity in equity_vals]
        options.extend(abs(liability) + equity for liability in liability_vals for equity in equity_vals)
    elif metric == "total_liabilities" and asset_vals and equity_vals:
        options = [asset - equity for asset in asset_vals for equity in equity_vals]
        options.extend(-(asset - equity) for asset in asset_vals for equity in equity_vals)
    elif metric == "total_equity" and asset_vals and liability_vals:
        options = [asset - liability for asset in asset_vals for liability in liability_vals]
        options.extend(asset - abs(liability) for asset in asset_vals for liability in liability_vals)

    error = _min_relative_error(candidate, options)
    return [] if error is None else [error]


def _cash_flow_errors(metric: str, candidate: float, values: Dict[str, List[float]]) -> List[float]:
    if metric not in {"net_change_in_cash", "operating_cash_flow", "investing_cash_flow", "financing_cash_flow"}:
        return []

    net_vals = values.get("net_change_in_cash", [])
    operating_vals = values.get("operating_cash_flow", [])
    investing_vals = values.get("investing_cash_flow", [])
    financing_vals = values.get("financing_cash_flow", [])
    options: List[float] = []

    if metric == "net_change_in_cash" and operating_vals and investing_vals and financing_vals:
        options = [operating + investing + financing for operating in operating_vals for investing in investing_vals for financing in financing_vals]
    elif metric == "operating_cash_flow" and net_vals and investing_vals and financing_vals:
        options = [net - investing - financing for net in net_vals for investing in investing_vals for financing in financing_vals]
    elif metric == "investing_cash_flow" and net_vals and operating_vals and financing_vals:
        options = [net - operating - financing for net in net_vals for operating in operating_vals for financing in financing_vals]
    elif metric == "financing_cash_flow" and net_vals and operating_vals and investing_vals:
        options = [net - operating - investing for net in net_vals for operating in operating_vals for investing in investing_vals]

    error = _min_relative_error(candidate, options)
    return [] if error is None else [error]


def _candidate_identity_score(
    row: Dict[str, object],
    metric_rows: Dict[str, List[Dict[str, object]]],
    target_metric: str,
) -> Optional[Tuple[float, int]]:
    candidate = _to_float(row.get("value"))
    if candidate is None:
        return None

    values = _candidate_metric_values(metric_rows, target_metric, row)
    family = _statement_family(row)
    errors: List[float] = []
    if family == "income_statement":
        errors.extend(_income_statement_errors(target_metric, candidate, values))
    elif family == "balance_sheet":
        errors.extend(_balance_sheet_errors(target_metric, candidate, values))
    elif family == "cash_flow":
        errors.extend(_cash_flow_errors(target_metric, candidate, values))

    if not errors:
        return None
    return (sum(errors) / len(errors), len(errors))


def _row_rank(row: Dict[str, object]) -> Tuple[int, float, int]:
    return (
        int(row.get("canonical_confidence_score", 0) or 0),
        float(row.get("confidence", 0.0) or 0.0),
        -int(row.get("line_no", 0) or 0),
    )


def resolve_duplicate_metrics(
    rows: Sequence[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], Dict[str, object]]:
    indexed_rows = list(enumerate(rows))
    duplicate_groups: Dict[Tuple[str, str, str, str, str], List[Tuple[int, Dict[str, object]]]] = defaultdict(list)
    statement_metric_rows: Dict[Tuple[str, str, str, str], Dict[str, List[Dict[str, object]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for index, row in indexed_rows:
        duplicate_groups[_duplicate_key(row)].append((index, dict(row)))
        statement_metric_rows[_statement_key(row)][_normalize_metric(row.get("metric_base") or row.get("metric"))].append(dict(row))

    kept: List[Tuple[int, Dict[str, object]]] = []
    demoted: List[Tuple[int, Dict[str, object]]] = []
    resolved_conflicts = 0

    for duplicate_key, group in duplicate_groups.items():
        if len(group) <= 1:
            kept.extend(group)
            continue

        metric = duplicate_key[-1]
        statement_key = duplicate_key[:-1]
        metric_rows = statement_metric_rows.get(statement_key, {})
        ranked_group = sorted(group, key=lambda item: _row_rank(item[1]), reverse=True)

        candidate_scores: List[Tuple[Tuple[float, int], int, Dict[str, object]]] = []
        for row_index, row in group:
            score = _candidate_identity_score(row, metric_rows, metric)
            if score is None:
                continue
            candidate_scores.append((score, row_index, dict(row)))

        if not candidate_scores:
            kept.extend(group)
            continue

        candidate_scores.sort(key=lambda item: (item[0][0], -item[0][1], -_row_rank(item[2])[0], item[1]))
        best_score = candidate_scores[0][0]
        best_candidates = [item for item in candidate_scores if item[0] == best_score]
        if len(best_candidates) != 1:
            kept.extend(group)
            continue

        _, winner_index, winner_row = best_candidates[0]
        winner = dict(winner_row)
        winner["duplicate_resolution_method"] = "financial_identity"
        winner["identity_resolution_error"] = round(best_score[0], 8)
        kept.append((winner_index, winner))

        for loser_index, loser_row in group:
            if loser_index == winner_index and loser_row == winner_row:
                continue
            demoted_row = dict(loser_row)
            demoted_row["context_reason"] = "identity_resolved_same_period"
            demoted_row["duplicate_resolution_method"] = "financial_identity"
            demoted_row["canonical_conflict_winner_line_no"] = winner.get("line_no", 0)
            demoted_row["canonical_conflict_winner_file"] = winner.get("file", "")
            demoted.append((loser_index, demoted_row))
        resolved_conflicts += 1

    kept_rows = [row for _, row in sorted(kept, key=lambda item: item[0])]
    demoted_rows = [row for _, row in sorted(demoted, key=lambda item: item[0])]
    diagnostics = {
        "identity_resolution_applied": bool(resolved_conflicts > 0),
        "identity_resolution_conflicts": int(resolved_conflicts),
    }
    return kept_rows, demoted_rows, diagnostics
