#!/usr/bin/env python3
"""Hard validation gates and statement-level quarantine helpers."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


def _to_float(value: object) -> float | None:
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


def _norm_metric(row: Dict[str, object]) -> str:
    m = str(row.get("metric_base", row.get("metric", ""))).strip().lower()
    alias = {
        "npat": "net_income",
        "capex": "capital_expenditure",
        "cash": "cash_and_equivalents",
    }
    return alias.get(m, m)


def _group_key(row: Dict[str, object]) -> Tuple[str, str, str]:
    return (
        str(row.get("file", row.get("pdf_path", ""))).strip(),
        str(row.get("statement_period_end", row.get("period_end", ""))).strip(),
        str(row.get("statement_scope", row.get("scope", ""))).strip().lower(),
    )


def evaluate_balance_sheet_equation(
    rows: Sequence[Dict[str, object]],
    *,
    abs_tolerance: float = 2.0,
    rel_tolerance: float = 0.0001,
) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str, str], Dict[str, float]] = defaultdict(dict)
    for row in rows:
        metric = _norm_metric(row)
        if metric not in {"total_assets", "total_liabilities", "total_equity"}:
            continue
        value = _to_float(row.get("value"))
        if value is None:
            continue
        grouped[_group_key(row)][metric] = value

    failures: List[Dict[str, object]] = []
    for key in sorted(grouped.keys()):
        data = grouped[key]
        if not {"total_assets", "total_liabilities", "total_equity"}.issubset(data.keys()):
            continue
        assets = float(data["total_assets"])
        liabilities = float(data["total_liabilities"])
        equity = float(data["total_equity"])

        # Accept either sign convention for liabilities:
        # 1) liabilities stored as positive magnitudes  -> A ~= L + E
        # 2) liabilities stored as negative balances    -> A ~= |L| + E
        diff_signed = assets - (liabilities + equity)
        diff_magnitude = assets - (abs(liabilities) + equity)
        if abs(diff_signed) <= abs(diff_magnitude):
            chosen_mode = "signed_liabilities"
            chosen_diff = diff_signed
        else:
            chosen_mode = "liability_magnitude"
            chosen_diff = diff_magnitude

        tol = max(float(abs_tolerance), abs(assets) * float(rel_tolerance))
        if min(abs(diff_signed), abs(diff_magnitude)) > tol:
            failures.append(
                {
                    "file": key[0],
                    "statement_period_end": key[1],
                    "scope": key[2],
                    "gate": "balance_sheet_equation",
                    "assets": assets,
                    "liabilities": liabilities,
                    "equity": equity,
                    "difference": chosen_diff,
                    "difference_signed": diff_signed,
                    "difference_magnitude": diff_magnitude,
                    "equation_mode": chosen_mode,
                    "tolerance": tol,
                }
            )
    return failures


def evaluate_cash_reconciliation(
    rows: Sequence[Dict[str, object]],
    *,
    abs_tolerance: float = 2.0,
    rel_tolerance: float = 0.0001,
) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str, str], Dict[str, float]] = defaultdict(dict)
    for row in rows:
        metric = _norm_metric(row)
        value = _to_float(row.get("value"))
        if value is None:
            continue
        if metric in {
            "cash_and_equivalents_opening",
            "cash_and_equivalents_closing",
            "operating_cash_flow",
            "investing_cash_flow",
            "financing_cash_flow",
            "net_cash_movement",
        }:
            grouped[_group_key(row)][metric] = value

    failures: List[Dict[str, object]] = []
    for key in sorted(grouped.keys()):
        data = grouped[key]
        opening = data.get("cash_and_equivalents_opening")
        closing = data.get("cash_and_equivalents_closing")
        if opening is None or closing is None:
            continue

        if "net_cash_movement" in data:
            expected = opening + float(data["net_cash_movement"])
        elif {"operating_cash_flow", "investing_cash_flow", "financing_cash_flow"}.issubset(data.keys()):
            expected = opening + float(data["operating_cash_flow"]) + float(data["investing_cash_flow"]) + float(
                data["financing_cash_flow"]
            )
        else:
            continue

        diff = float(closing) - float(expected)
        tol = max(float(abs_tolerance), abs(float(closing)) * float(rel_tolerance))
        if abs(diff) > tol:
            failures.append(
                {
                    "file": key[0],
                    "statement_period_end": key[1],
                    "scope": key[2],
                    "gate": "cash_reconciliation",
                    "opening": opening,
                    "closing": closing,
                    "expected_closing": expected,
                    "difference": diff,
                    "tolerance": tol,
                }
            )
    return failures


def _statement_family(row: Dict[str, object]) -> str:
    return str(row.get("statement_family", row.get("statement_type", ""))).strip().lower()


def _is_balance_family(row: Dict[str, object]) -> bool:
    fam = _statement_family(row)
    if "balance" in fam:
        return True
    metric = _norm_metric(row)
    return metric in {"total_assets", "total_liabilities", "total_equity", "current_assets", "current_liabilities"}


def _is_cash_family(row: Dict[str, object]) -> bool:
    fam = _statement_family(row)
    if "cash" in fam:
        return True
    metric = _norm_metric(row)
    return metric in {
        "operating_cash_flow",
        "capital_expenditure",
        "free_cash_flow",
        "cash_and_equivalents_opening",
        "cash_and_equivalents_closing",
    }


def apply_statement_level_quarantine(
    rows: Sequence[Dict[str, object]],
    *,
    out_dir: Path | None = None,
    abs_tolerance: float = 2.0,
    rel_tolerance: float = 0.0001,
) -> Dict[str, object]:
    failures_bs = evaluate_balance_sheet_equation(rows, abs_tolerance=abs_tolerance, rel_tolerance=rel_tolerance)
    failures_cf = evaluate_cash_reconciliation(rows, abs_tolerance=abs_tolerance, rel_tolerance=rel_tolerance)

    bs_keys = {(f["file"], f["statement_period_end"], f["scope"]) for f in failures_bs}
    cf_keys = {(f["file"], f["statement_period_end"], f["scope"]) for f in failures_cf}

    kept_rows: List[Dict[str, object]] = []
    quarantined_rows: List[Dict[str, object]] = []

    for row in rows:
        key = _group_key(row)
        if key in bs_keys and _is_balance_family(row):
            rr = dict(row)
            rr["quarantine_reason"] = "balance_sheet_equation_failed"
            quarantined_rows.append(rr)
            continue
        if key in cf_keys and _is_cash_family(row):
            rr = dict(row)
            rr["quarantine_reason"] = "cash_reconciliation_failed"
            quarantined_rows.append(rr)
            continue
        kept_rows.append(dict(row))

    summary = {
        "balance_sheet_failures": failures_bs,
        "cash_reconciliation_failures": failures_cf,
        "rows_input": int(len(rows)),
        "rows_kept": int(len(kept_rows)),
        "rows_quarantined": int(len(quarantined_rows)),
    }

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "quarantine_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        if quarantined_rows:
            cols = sorted({k for r in quarantined_rows for k in r.keys()})
            with (out_dir / "quarantined_rows.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                for row in quarantined_rows:
                    w.writerow(row)

            by_doc: Dict[str, List[Dict[str, object]]] = defaultdict(list)
            for row in quarantined_rows:
                stem = Path(str(row.get("file", "unknown"))).stem or "unknown"
                by_doc[stem].append(row)
            for stem, items in by_doc.items():
                doc_dir = out_dir / stem
                doc_dir.mkdir(parents=True, exist_ok=True)
                cols_doc = sorted({k for r in items for k in r.keys()})
                with (doc_dir / "quarantined_rows.csv").open("w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=cols_doc)
                    w.writeheader()
                    for row in items:
                        w.writerow(row)

    return {
        "kept_rows": kept_rows,
        "quarantined_rows": quarantined_rows,
        "summary": summary,
    }


def apply_statement_level_quarantine_df(
    df,
    *,
    out_dir: Path | None = None,
    abs_tolerance: float = 2.0,
    rel_tolerance: float = 0.0001,
):
    records = df.to_dict(orient="records")
    result = apply_statement_level_quarantine(
        records,
        out_dir=out_dir,
        abs_tolerance=abs_tolerance,
        rel_tolerance=rel_tolerance,
    )

    import pandas as pd

    kept_df = pd.DataFrame(result["kept_rows"])
    kept_df = kept_df.reindex(columns=list(df.columns) + [c for c in kept_df.columns if c not in df.columns])
    return kept_df, result["summary"], result["quarantined_rows"]
