#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


RELATIVE_ONLY_PERIODS = {
    "current quarter",
    "previous quarter",
    "prior quarter",
    "current period",
    "previous period",
}

NON_CASH_LABEL_HINTS = {
    "revenue": [r"\brevenue\b", r"\bturnover\b", r"\btotal\s+income\b"],
    "gross_profit": [r"\bgross\s+profit\b", r"\bgross\s+income\b"],
    "ebit": [r"\bebit\b", r"\boperating\s+profit\b", r"\boperating\s+income\b", r"\bprofit\s+from\s+operations\b"],
    "ebitda": [r"\bebitda\b"],
    "net_income": [
        r"\bnet\s+income\b",
        r"\bnet\s+profit\b",
        r"\bprofit\s+after\s+tax\b",
        r"\bprofit\s+after\s+taxation\b",
        r"\bloss\s+after\s+tax\b",
        r"\bloss\s+after\s+taxation\b",
        r"\bprofit\s+or\s+loss\b",
        r"\bprofit\s*/?\s*\(?loss\)?\b",
        r"\b(?:profit|loss)(?:\s+after\s+tax(?:ation)?)?\s+attributable\s+to\b",
    ],
    "npat": [r"\bnpat\b", r"\bnet\s+profit\s+after\s+tax\b"],
}

NET_CASH_MOVEMENT_RE = re.compile(
    r"\b(net\s*(?:decrease|increase)\s*/?\s*\(?(?:decrease|increase)?\)?\s+in\s+cash(?:\s+and\s+cash\s+equivalents)?|"
    r"net\s+cash\s+flows?\b)",
    re.IGNORECASE,
)
RETAINED_EARNINGS_OPEN_RE = re.compile(
    r"\bretained\s+earnings\b.*\b(opening|at\s+beginning|beginning\s+of)\b|\bopening\s+retained\s+earnings\b",
    re.IGNORECASE,
)
RETAINED_EARNINGS_CLOSE_RE = re.compile(
    r"\bretained\s+earnings\b.*\b(closing|at\s+end|end\s+of)\b|\bclosing\s+retained\s+earnings\b",
    re.IGNORECASE,
)
DIVIDENDS_RE = re.compile(r"\bdividend[s]?\b", re.IGNORECASE)
EXPENSES_RE = re.compile(
    r"\b(total\s+expenses?|expenses?|cost\s+of\s+sales|operating\s+expenses?)\b",
    re.IGNORECASE,
)


def _to_float(v: object) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _score_row(row: Dict[str, object]) -> Tuple[int, int]:
    return (
        int(row.get("canonical_confidence_score", 0) or 0),
        int(row.get("line_no", 0) or 0),
    )


def _pick_best(rows: List[Dict[str, object]]) -> Optional[Dict[str, object]]:
    if not rows:
        return None
    return sorted(rows, key=_score_row, reverse=True)[0]


def _tol_abs(lhs: float, rhs: float, rel_pct: float) -> float:
    return max(1.0, abs(rel_pct) * max(abs(lhs), abs(rhs), 1.0))


def _group_rows(rows: List[Dict[str, object]]) -> Dict[Tuple[str, str], List[Dict[str, object]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for r in rows:
        file_path = str(r.get("file", ""))
        period_end = str(r.get("statement_period_end", "")).strip() or str(r.get("period_end_date", "")).strip()
        if not file_path or not period_end:
            continue
        grouped.setdefault((file_path, period_end), []).append(r)
    return grouped


def _evaluate_integrity(
    rows: List[Dict[str, object]],
    *,
    balance_sheet_tolerance_pct: float = 0.02,
    cash_bridge_tolerance_pct: float = 0.03,
    retained_earnings_tolerance_pct: float = 0.05,
    income_tolerance_pct: float = 0.05,
) -> Tuple[Dict[str, List[Dict[str, object]]], Dict[str, int], Dict[Tuple[str, str], Dict[str, Any]]]:
    issues: Dict[str, List[Dict[str, object]]] = {
        "balance_sheet_identity_mismatch": [],
        "cash_flow_bridge_mismatch": [],
        "retained_earnings_roll_mismatch": [],
        "income_integrity_mismatch": [],
    }
    stats = {
        "balance_sheet_identity_evaluated": 0,
        "cash_flow_bridge_evaluated": 0,
        "retained_earnings_roll_evaluated": 0,
        "income_integrity_evaluated": 0,
    }

    grouped = _group_rows(rows)
    integrity_state: Dict[Tuple[str, str], Dict[str, Optional[bool]]] = {
        key: {
            "balance_sheet_identity_pass": None,
            "cash_flow_bridge_pass": None,
            "retained_earnings_roll_pass": None,
            "income_integrity_pass": None,
        }
        for key in grouped.keys()
    }
    for (file_path, period_end), rs in grouped.items():
        def by_metric(name: str) -> List[Dict[str, object]]:
            return [r for r in rs if str(r.get("metric", "")).strip().lower() == name]

        assets_r = _pick_best(by_metric("total_assets"))
        liab_r = _pick_best(by_metric("total_liabilities"))
        eq_r = _pick_best(by_metric("total_equity"))
        assets = _to_float(assets_r.get("value")) if assets_r else None
        liab = _to_float(liab_r.get("value")) if liab_r else None
        eq = _to_float(eq_r.get("value")) if eq_r else None
        if assets is not None and liab is not None and eq is not None:
            stats["balance_sheet_identity_evaluated"] += 1
            lhs = assets
            rhs = liab + eq
            delta = lhs - rhs
            tol = _tol_abs(lhs, rhs, balance_sheet_tolerance_pct)
            passed = abs(delta) <= tol
            integrity_state[(file_path, period_end)]["balance_sheet_identity_pass"] = passed
            if not passed:
                issues["balance_sheet_identity_mismatch"].append(
                    {
                        "file": file_path,
                        "statement_period_end": period_end,
                        "total_assets": lhs,
                        "total_liabilities": liab,
                        "total_equity": eq,
                        "delta": delta,
                        "tolerance": tol,
                    }
                )

        opening_r = _pick_best(by_metric("cash_and_equivalents_opening"))
        closing_r = _pick_best(by_metric("cash_and_equivalents_closing"))
        net_rows = [
            r
            for r in rs
            if NET_CASH_MOVEMENT_RE.search(
                f"{str(r.get('row_label', ''))} {str(r.get('line', ''))}"
            )
        ]
        net_r = _pick_best(net_rows)
        opening = _to_float(opening_r.get("value")) if opening_r else None
        closing = _to_float(closing_r.get("value")) if closing_r else None
        net_mv = _to_float(net_r.get("value")) if net_r else None
        if opening is not None and closing is not None and net_mv is not None:
            stats["cash_flow_bridge_evaluated"] += 1
            lhs = closing - opening
            rhs = net_mv
            delta = lhs - rhs
            tol = _tol_abs(lhs, rhs, cash_bridge_tolerance_pct)
            passed = abs(delta) <= tol
            integrity_state[(file_path, period_end)]["cash_flow_bridge_pass"] = passed
            if not passed:
                issues["cash_flow_bridge_mismatch"].append(
                    {
                        "file": file_path,
                        "statement_period_end": period_end,
                        "cash_opening": opening,
                        "cash_closing": closing,
                        "net_cash_movement": rhs,
                        "delta": delta,
                        "tolerance": tol,
                    }
                )

        re_open_rows = [
            r
            for r in rs
            if RETAINED_EARNINGS_OPEN_RE.search(
                f"{str(r.get('row_label', ''))} {str(r.get('line', ''))}"
            )
        ]
        re_close_rows = [
            r
            for r in rs
            if RETAINED_EARNINGS_CLOSE_RE.search(
                f"{str(r.get('row_label', ''))} {str(r.get('line', ''))}"
            )
        ]
        dividends_rows = [
            r
            for r in rs
            if DIVIDENDS_RE.search(f"{str(r.get('row_label', ''))} {str(r.get('line', ''))}")
        ]
        ni_r = _pick_best(by_metric("npat") or by_metric("net_income"))
        re_open = _to_float((_pick_best(re_open_rows) or {}).get("value")) if re_open_rows else None
        re_close = _to_float((_pick_best(re_close_rows) or {}).get("value")) if re_close_rows else None
        dividends = _to_float((_pick_best(dividends_rows) or {}).get("value")) if dividends_rows else None
        ni = _to_float(ni_r.get("value")) if ni_r else None
        if re_open is not None and re_close is not None and dividends is not None and ni is not None:
            stats["retained_earnings_roll_evaluated"] += 1
            # Handle both signed-dividend and absolute-dividend conventions.
            pred_signed = re_open + ni + dividends
            pred_unsigned = re_open + ni - abs(dividends)
            if abs(re_close - pred_signed) <= abs(re_close - pred_unsigned):
                pred = pred_signed
            else:
                pred = pred_unsigned
            delta = re_close - pred
            tol = _tol_abs(re_close, pred, retained_earnings_tolerance_pct)
            passed = abs(delta) <= tol
            integrity_state[(file_path, period_end)]["retained_earnings_roll_pass"] = passed
            if not passed:
                issues["retained_earnings_roll_mismatch"].append(
                    {
                        "file": file_path,
                        "statement_period_end": period_end,
                        "retained_earnings_opening": re_open,
                        "npat_or_net_income": ni,
                        "dividends": dividends,
                        "retained_earnings_closing": re_close,
                        "predicted_closing": pred,
                        "delta": delta,
                        "tolerance": tol,
                    }
                )

        rev_r = _pick_best(by_metric("revenue"))
        ebit_r = _pick_best(by_metric("ebit"))
        expense_rows = [
            r
            for r in rs
            if EXPENSES_RE.search(f"{str(r.get('row_label', ''))} {str(r.get('line', ''))}")
            and str(r.get("metric", "")).strip().lower() not in {"revenue", "ebit", "ebitda"}
        ]
        expense_r = _pick_best(expense_rows)
        rev = _to_float(rev_r.get("value")) if rev_r else None
        ebit = _to_float(ebit_r.get("value")) if ebit_r else None
        expenses = _to_float(expense_r.get("value")) if expense_r else None
        if rev is not None and ebit is not None and expenses is not None:
            stats["income_integrity_evaluated"] += 1
            lhs = rev - expenses
            rhs = ebit
            delta = lhs - rhs
            tol = _tol_abs(lhs, rhs, income_tolerance_pct)
            passed = abs(delta) <= tol
            integrity_state[(file_path, period_end)]["income_integrity_pass"] = passed
            if not passed:
                issues["income_integrity_mismatch"].append(
                    {
                        "file": file_path,
                        "statement_period_end": period_end,
                        "revenue": rev,
                        "expenses": expenses,
                        "ebit": ebit,
                        "delta": delta,
                        "tolerance": tol,
                    }
                )

    integrity_index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for key, st in integrity_state.items():
        checks_total = len(st)
        checks_unknown = sum(1 for v in st.values() if v is None)
        checks_evaluated = checks_total - checks_unknown
        checks_passed = sum(1 for v in st.values() if v is True)
        checks_failed = sum(1 for v in st.values() if v is False)
        if checks_evaluated == 0:
            anomaly = "UNKNOWN"
        elif checks_failed >= 2:
            anomaly = "HIGH"
        elif checks_failed == 1:
            anomaly = "MEDIUM"
        else:
            anomaly = "LOW"
        evaluated_flags = {
            "balance_sheet_identity": st.get("balance_sheet_identity_pass"),
            "cash_flow_bridge": st.get("cash_flow_bridge_pass"),
            "retained_earnings_roll": st.get("retained_earnings_roll_pass"),
            "income_integrity": st.get("income_integrity_pass"),
        }
        integrity_index[key] = {
            **st,
            "integrity_checks_evaluated": checks_evaluated,
            "integrity_checks_passed": checks_passed,
            # Score gives credit to both passing and not-evaluated checks.
            "integrity_score": checks_passed + checks_unknown,
            "integrity_score_max": 4,
            "data_anomaly_level": anomaly,
            "evaluated_flags": evaluated_flags,
        }

    return issues, stats, integrity_index


def gather_integrity_issues(
    rows: List[Dict[str, object]],
    *,
    balance_sheet_tolerance_pct: float = 0.02,
    cash_bridge_tolerance_pct: float = 0.03,
    retained_earnings_tolerance_pct: float = 0.05,
    income_tolerance_pct: float = 0.05,
) -> Tuple[Dict[str, List[Dict[str, object]]], Dict[str, int]]:
    issues, stats, _ = _evaluate_integrity(
        rows,
        balance_sheet_tolerance_pct=balance_sheet_tolerance_pct,
        cash_bridge_tolerance_pct=cash_bridge_tolerance_pct,
        retained_earnings_tolerance_pct=retained_earnings_tolerance_pct,
        income_tolerance_pct=income_tolerance_pct,
    )
    return issues, stats


def build_integrity_index(
    rows: List[Dict[str, object]],
    *,
    balance_sheet_tolerance_pct: float = 0.02,
    cash_bridge_tolerance_pct: float = 0.03,
    retained_earnings_tolerance_pct: float = 0.05,
    income_tolerance_pct: float = 0.05,
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    _, _, idx = _evaluate_integrity(
        rows,
        balance_sheet_tolerance_pct=balance_sheet_tolerance_pct,
        cash_bridge_tolerance_pct=cash_bridge_tolerance_pct,
        retained_earnings_tolerance_pct=retained_earnings_tolerance_pct,
        income_tolerance_pct=income_tolerance_pct,
    )
    return idx


def load_rows(path: Path) -> List[Dict[str, object]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, list):
        raise ValueError(f"Expected JSON array at {path}")
    return [r for r in obj if isinstance(r, dict)]


def gather_issues(rows: List[Dict[str, object]]) -> Dict[str, List[Dict[str, object]]]:
    issues: Dict[str, List[Dict[str, object]]] = {
        "empty_period": [],
        "empty_statement_period_end": [],
        "relative_only_period": [],
        "split_missing_balance_date": [],
        "numeric_only_statement_title": [],
        "page_footer_statement_title": [],
        "trailing_note_statement_title": [],
        "cash_unsplit_end_phrase": [],
        "cash_unsplit_begin_phrase": [],
        "non_cash_missing_row_label": [],
        "non_cash_label_metric_mismatch": [],
    }
    for row in rows:
        metric = str(row.get("metric", "")).strip().lower()
        period = str(row.get("period", "")).strip()
        period_l = period.lower()
        sp_end = str(row.get("statement_period_end", "")).strip()
        bal_date = str(row.get("balance_date", "")).strip()
        title = str(row.get("statement_title", "")).strip()
        line = str(row.get("line", "")).strip()
        row_label = str(row.get("row_label", "")).strip()

        if not period:
            issues["empty_period"].append(row)
        if not sp_end:
            issues["empty_statement_period_end"].append(row)
        if period_l in RELATIVE_ONLY_PERIODS:
            issues["relative_only_period"].append(row)
        if metric.endswith("_opening") or metric.endswith("_closing"):
            if not bal_date:
                issues["split_missing_balance_date"].append(row)
        if re.fullmatch(r"\d{1,3}", title):
            issues["numeric_only_statement_title"].append(row)
        if re.fullmatch(r"page\s+\d+\s+of\s+\d+", title, flags=re.IGNORECASE):
            issues["page_footer_statement_title"].append(row)
        if re.search(r"should\s+be\s+read\s+in\s+conjunction", title, flags=re.IGNORECASE):
            issues["trailing_note_statement_title"].append(row)
        if metric == "cash_and_equivalents":
            if re.search(r"cash\s+and\s+cash\s+equivalents\s+at\s+(?:the\s+)?end\s+of", line, flags=re.IGNORECASE):
                issues["cash_unsplit_end_phrase"].append(row)
            if re.search(
                r"cash\s+and\s+cash\s+equivalents\s+at\s+(?:the\s+)?beginning\s+of",
                line,
                flags=re.IGNORECASE,
            ):
                issues["cash_unsplit_begin_phrase"].append(row)
        if metric in NON_CASH_LABEL_HINTS:
            if not row_label:
                issues["non_cash_missing_row_label"].append(row)
            else:
                row_label_l = row_label.lower()
                if not any(re.search(pat, row_label_l, flags=re.IGNORECASE) for pat in NON_CASH_LABEL_HINTS[metric]):
                    issues["non_cash_label_metric_mismatch"].append(row)
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit canonical financial metric extraction quality gates.")
    ap.add_argument("--canonical-json", required=True, help="Canonical JSON output from extract_financial_metrics.py")
    ap.add_argument("--max-empty-period", type=int, default=0)
    ap.add_argument("--max-empty-statement-period-end", type=int, default=0)
    ap.add_argument("--max-relative-only-period", type=int, default=0)
    ap.add_argument("--max-split-missing-balance-date", type=int, default=0)
    ap.add_argument("--max-numeric-title", type=int, default=0)
    ap.add_argument("--max-page-footer-title", type=int, default=0)
    ap.add_argument("--max-trailing-note-title", type=int, default=0)
    ap.add_argument("--max-cash-unsplit-end", type=int, default=0)
    ap.add_argument("--max-cash-unsplit-begin", type=int, default=0)
    ap.add_argument("--max-non-cash-missing-row-label", type=int, default=0)
    ap.add_argument("--max-non-cash-label-mismatch", type=int, default=0)
    ap.add_argument("--max-balance-sheet-identity-mismatch", type=int, default=0)
    ap.add_argument("--max-cash-flow-bridge-mismatch", type=int, default=0)
    ap.add_argument("--max-retained-earnings-roll-mismatch", type=int, default=0)
    ap.add_argument("--max-income-integrity-mismatch", type=int, default=0)
    ap.add_argument("--balance-sheet-tolerance-pct", type=float, default=0.02)
    ap.add_argument("--cash-flow-bridge-tolerance-pct", type=float, default=0.03)
    ap.add_argument("--retained-earnings-tolerance-pct", type=float, default=0.05)
    ap.add_argument("--income-integrity-tolerance-pct", type=float, default=0.05)
    ap.add_argument("--sample-size", type=int, default=5)
    ap.add_argument("--out-json", default="", help="Optional summary JSON output path")
    args = ap.parse_args()

    canonical_path = Path(args.canonical_json).resolve()
    if not canonical_path.exists():
        print(f"[fail] canonical json not found: {canonical_path}")
        return 2

    rows = load_rows(canonical_path)
    issues = gather_issues(rows)
    integrity_issues, integrity_stats = gather_integrity_issues(
        rows,
        balance_sheet_tolerance_pct=max(0.0, float(args.balance_sheet_tolerance_pct)),
        cash_bridge_tolerance_pct=max(0.0, float(args.cash_flow_bridge_tolerance_pct)),
        retained_earnings_tolerance_pct=max(0.0, float(args.retained_earnings_tolerance_pct)),
        income_tolerance_pct=max(0.0, float(args.income_integrity_tolerance_pct)),
    )
    issues.update(integrity_issues)

    thresholds = {
        "empty_period": max(0, int(args.max_empty_period)),
        "empty_statement_period_end": max(0, int(args.max_empty_statement_period_end)),
        "relative_only_period": max(0, int(args.max_relative_only_period)),
        "split_missing_balance_date": max(0, int(args.max_split_missing_balance_date)),
        "numeric_only_statement_title": max(0, int(args.max_numeric_title)),
        "page_footer_statement_title": max(0, int(args.max_page_footer_title)),
        "trailing_note_statement_title": max(0, int(args.max_trailing_note_title)),
        "cash_unsplit_end_phrase": max(0, int(args.max_cash_unsplit_end)),
        "cash_unsplit_begin_phrase": max(0, int(args.max_cash_unsplit_begin)),
        "non_cash_missing_row_label": max(0, int(args.max_non_cash_missing_row_label)),
        "non_cash_label_metric_mismatch": max(0, int(args.max_non_cash_label_mismatch)),
        "balance_sheet_identity_mismatch": max(0, int(args.max_balance_sheet_identity_mismatch)),
        "cash_flow_bridge_mismatch": max(0, int(args.max_cash_flow_bridge_mismatch)),
        "retained_earnings_roll_mismatch": max(0, int(args.max_retained_earnings_roll_mismatch)),
        "income_integrity_mismatch": max(0, int(args.max_income_integrity_mismatch)),
    }

    summary = {
        "canonical_json": str(canonical_path),
        "rows": len(rows),
        "issue_counts": {k: len(v) for k, v in issues.items()},
        "integrity_stats": integrity_stats,
        "thresholds": thresholds,
        "status": "pass",
    }

    failed = False
    print(f"[audit] rows={len(rows)}")
    for key in sorted(issues.keys()):
        count = len(issues[key])
        limit = thresholds[key]
        status = "ok" if count <= limit else "fail"
        print(f"[{status}] {key}: {count} (max={limit})")
        eval_key = f"{key.replace('_mismatch', '')}_evaluated"
        if eval_key in integrity_stats:
            print(f"  evaluated={integrity_stats[eval_key]}")
        if count > limit:
            failed = True
            for row in issues[key][: max(0, int(args.sample_size))]:
                if any(k in row for k in ("total_assets", "cash_opening", "retained_earnings_opening", "revenue")):
                    print(
                        "  sample:",
                        "file=",
                        row.get("file", ""),
                        "| sp_end=",
                        row.get("statement_period_end", ""),
                        "| delta=",
                        row.get("delta", ""),
                        "| tol=",
                        row.get("tolerance", ""),
                    )
                else:
                    print(
                        "  sample:",
                        row.get("metric", ""),
                        "| period=",
                        row.get("period", ""),
                        "| sp_end=",
                        row.get("statement_period_end", ""),
                        "| title=",
                        row.get("statement_title", ""),
                        "| line=",
                        row.get("line", ""),
                    )

    if failed:
        summary["status"] = "fail"
    if args.out_json:
        out_path = Path(args.out_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[audit] summary json: {out_path}")

    if failed:
        print("[result] FAIL")
        return 1
    print("[result] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
