#!/usr/bin/env python3
"""
Output 29M extracted metrics in the same quarter grid as the reference (Website) for accuracy comparison.
Values in $ millions for P&L/balance sheet metrics. Reads reports/29m_metrics.csv.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "reports" / "29m_metrics.csv"

# Reference column order (quarter label -> period_end)
QUARTERS = [
    ("Q4 '25", "2025-12-31"),
    ("Q3 '25", "2025-09-30"),
    ("Q2 '25", "2025-06-30"),
    ("Q1 '25", "2025-03-31"),
    ("Q4 '24", "2024-12-31"),
    ("Q3 '24", "2024-09-30"),
    ("Q2 '24", "2024-06-30"),
    ("Q1 '24", "2024-03-31"),
    ("Q4 '23", "2023-12-31"),
    ("Q3 '23", "2023-09-30"),
    ("Q2 '23", "2023-06-30"),
    ("Q1 '23", "2023-03-31"),
    ("Q4 '22", "2022-12-31"),
    ("Q3 '22", "2022-09-30"),
    ("Q2 '22", "2022-06-30"),
    ("Q1 '22", "2022-03-31"),
    ("Q4 '21", "2021-12-31"),
    ("Q4 '20", "2020-12-31"),
    ("Q4 '19", "2019-12-31"),
    ("Q4 '18", "2018-12-31"),
]

# Our metric -> reference label; metrics we express in $ millions
METRICS_IN_MILLIONS = [
    ("revenue", "Total Revenues (extracted)"),
    ("ebitda", "EBITDA (extracted)"),
    ("gross_profit", "Gross Profit (extracted)"),
    ("net_income", "Net Income (extracted)"),
    ("ebit", "Operating Profit (extracted)"),
]


def to_millions(val):
    try:
        v = float(val)
        if abs(v) >= 1e6:
            return round(v / 1e6, 1)
        if abs(v) >= 1e3:
            return round(v / 1e3, 1)  # was in thousands
        return v
    except (TypeError, ValueError):
        return val


def main():
    if not CSV_PATH.exists():
        print(f"Run: python scripts/query_financial_metrics.py --ticker 29M --format csv > reports/29m_metrics.csv")
        return 1

    by_key = {}  # (metric, period_end) -> list of (value, currency)
    with open(CSV_PATH) as f:
        r = csv.DictReader(f)
        for row in r:
            m = row.get("metric", "")
            p = row.get("statement_period_end", "")
            try:
                v = float(row.get("value", 0))
            except (TypeError, ValueError):
                continue
            curr = (row.get("currency") or "").strip()
            by_key.setdefault((m, p), []).append((v, curr))

    def pick_value(values_list):
        """Prefer $ and value in millions range (abs 1e5–1e10) for P&L/BS."""
        if not values_list:
            return None
        # Prefer AUD ($) over US$
        aud = [(v, c) for v, c in values_list if c == "$"]
        cand = aud if aud else values_list
        # Prefer magnitude that looks like dollars (not cents or per-share)
        best = cand[0]
        for v, c in cand:
            if 1e5 <= abs(v) <= 1e11:
                return to_millions(v)
            if 1e3 <= abs(v) <= 1e8:
                best = (v, c)
        return to_millions(best[0])

    print("29M — Extracted vs reference (Website). Values in $ millions unless noted.\n")
    print("Metric (extracted)" + "".join(f",{q[0]}" for q in QUARTERS))
    print("-" * (50 + 10 * len(QUARTERS)))

    for our_metric, label in METRICS_IN_MILLIONS:
        row_vals = []
        for _qlabel, period_end in QUARTERS:
            vals = by_key.get((our_metric, period_end), [])
            v = pick_value(vals) if vals else ""
            row_vals.append(str(v) if v not in (None, "") else "—")
        print(f"{label}" + "".join(f",{x}" for x in row_vals))

    print("\nReference (from your paste) — key rows for comparison:")
    print("  Total Revenues Q4 '25: 566.6  |  We have: revenue 2025-12-31")
    print("  EBITDA         Q4 '25: 128.8 |  We have: ebitda 2025-12-31 (may be USD or multiple)")
    print("  Gross Profit   Q4 '25: 84.6  |  We have: gross_profit 2025-12-31")
    print("  Net Income     Q4 '25: 24.2  |  We have: net_income 2025-12-31")
    print("  Operating Profit Q4 '25: 37 |  We have: ebit 2025-12-31")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
