#!/usr/bin/env python3
import argparse
import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SignalThresholds:
    leverage_low_max: float
    leverage_medium_max: float
    runway_high_periods: float
    runway_critical_periods: float
    margin_drop_bps: float
    consecutive_margin_drops: int
    max_abs_margin_pct: float
    max_abs_margin_drop_bps: float


def thresholds_for_profile(profile: str) -> SignalThresholds:
    p = (profile or "institutional").strip().lower()
    if p == "aggressive":
        return SignalThresholds(
            leverage_low_max=1.5,
            leverage_medium_max=3.0,
            runway_high_periods=6.0,
            runway_critical_periods=3.0,
            margin_drop_bps=200.0,
            consecutive_margin_drops=2,
            max_abs_margin_pct=300.0,
            max_abs_margin_drop_bps=10000.0,
        )
    return SignalThresholds(
        leverage_low_max=2.0,
        leverage_medium_max=3.5,
        runway_high_periods=4.0,
        runway_critical_periods=2.0,
        margin_drop_bps=300.0,
        consecutive_margin_drops=2,
        max_abs_margin_pct=200.0,
        max_abs_margin_drop_bps=5000.0,
    )


def _safe_float(v: object) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        t = str(v).strip().replace(",", "")
        if not t:
            return None
        return float(t)
    except (TypeError, ValueError):
        return None


def _row_rank(row: Dict[str, object]) -> Tuple[int, int, int, int, str]:
    return (
        int(row.get("canonical_confidence_floor", 0) or 0),
        int(row.get("integrity_score", 0) or 0),
        int(row.get("integrity_checks_evaluated", 0) or 0),
        int(row.get("period_sort_key", 0) or 0),
        str(row.get("source_file", "")),
    )


def load_derived_rows_sqlite(
    db_path: Path,
    *,
    min_canonical_confidence_floor: int,
    min_integrity_score: int,
    min_integrity_checks_evaluated: int,
) -> List[Dict[str, object]]:
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='derived_metrics'")
        if cur.fetchone() is None:
            return []
        cur.execute(
            """
            SELECT
                company,
                statement_period_end,
                period_sort_key,
                metric,
                value_num,
                source_file,
                canonical_confidence_floor,
                integrity_score,
                integrity_checks_evaluated,
                data_anomaly_level
            FROM derived_metrics
            WHERE metric IN (
                'net_debt_to_ebitda',
                'cash_runway_periods',
                'ebit_margin_pct',
                'ebitda_amount'
            )
            """
        )
        rows: List[Dict[str, object]] = []
        for rec in cur.fetchall():
            row = {
                "company": str(rec[0] or ""),
                "statement_period_end": str(rec[1] or ""),
                "period_sort_key": int(rec[2] or 0),
                "metric": str(rec[3] or ""),
                "value_num": _safe_float(rec[4]),
                "source_file": str(rec[5] or ""),
                "canonical_confidence_floor": int(rec[6] or 0),
                "integrity_score": int(rec[7] or 0),
                "integrity_checks_evaluated": int(rec[8] or 0),
                "data_anomaly_level": str(rec[9] or "UNKNOWN"),
            }
            if row["value_num"] is None:
                continue
            if row["canonical_confidence_floor"] < min_canonical_confidence_floor:
                continue
            if row["integrity_score"] < min_integrity_score:
                continue
            if row["integrity_checks_evaluated"] < min_integrity_checks_evaluated:
                continue
            if not row["company"] or not row["statement_period_end"]:
                continue
            rows.append(row)
        return rows
    finally:
        conn.close()


def build_risk_signals(rows: List[Dict[str, object]], thresholds: SignalThresholds) -> List[Dict[str, object]]:
    best_by_period_metric: Dict[Tuple[str, str, str], Dict[str, object]] = {}
    for row in rows:
        key = (str(row.get("company", "")), str(row.get("statement_period_end", "")), str(row.get("metric", "")))
        prev = best_by_period_metric.get(key)
        if prev is None or _row_rank(row) > _row_rank(prev):
            best_by_period_metric[key] = row

    by_period: Dict[Tuple[str, str], Dict[str, Dict[str, object]]] = {}
    for (company, period_end, metric), row in best_by_period_metric.items():
        by_period.setdefault((company, period_end), {})[metric] = row

    signals: List[Dict[str, object]] = []
    now = utc_now_iso()

    def add_signal(
        *,
        file_path: str,
        company: str,
        statement_period_end: str,
        period_sort_key: int,
        signal_type: str,
        signal_name: str,
        signal_value: float,
        risk_level: str,
        explanation: str,
    ) -> None:
        signals.append(
            {
                "file": file_path,
                "company": company,
                "statement_period_end": statement_period_end,
                "period_sort_key": period_sort_key,
                "signal_type": signal_type,
                "signal_name": signal_name,
                "signal_value": float(signal_value),
                "risk_level": risk_level,
                "explanation": explanation,
                "created_utc": now,
            }
        )

    # Per-period leverage and liquidity
    for (company, period_end), metric_map in by_period.items():
        rank_source = next(iter(metric_map.values()))
        file_path = str(rank_source.get("source_file", ""))
        period_sort_key = int(rank_source.get("period_sort_key", 0) or 0)

        ebitda_row = metric_map.get("ebitda_amount")
        ratio_row = metric_map.get("net_debt_to_ebitda")
        if ebitda_row is not None and float(ebitda_row.get("value_num", 0.0) or 0.0) <= 0.0:
            ebitda_val = float(ebitda_row.get("value_num", 0.0) or 0.0)
            add_signal(
                file_path=file_path,
                company=company,
                statement_period_end=period_end,
                period_sort_key=period_sort_key,
                signal_type="leverage",
                signal_name="net_debt_to_ebitda_risk",
                signal_value=ebitda_val,
                risk_level="CRITICAL",
                explanation="EBITDA is non-positive; leverage servicing capacity is critically weak.",
            )
        elif ratio_row is not None:
            ratio = float(ratio_row.get("value_num", 0.0) or 0.0)
            if ratio < thresholds.leverage_low_max:
                level = "LOW"
            elif ratio <= thresholds.leverage_medium_max:
                level = "MEDIUM"
            else:
                level = "HIGH"
            add_signal(
                file_path=file_path,
                company=company,
                statement_period_end=period_end,
                period_sort_key=period_sort_key,
                signal_type="leverage",
                signal_name="net_debt_to_ebitda_risk",
                signal_value=ratio,
                risk_level=level,
                explanation=(
                    f"Net debt / EBITDA = {ratio:.2f}; thresholds "
                    f"<{thresholds.leverage_low_max:.1f}=LOW, "
                    f"{thresholds.leverage_low_max:.1f}-{thresholds.leverage_medium_max:.1f}=MEDIUM, "
                    f">{thresholds.leverage_medium_max:.1f}=HIGH."
                ),
            )

        runway_row = metric_map.get("cash_runway_periods")
        if runway_row is not None:
            runway = float(runway_row.get("value_num", 0.0) or 0.0)
            if runway < thresholds.runway_critical_periods:
                level = "CRITICAL"
            elif runway < thresholds.runway_high_periods:
                level = "HIGH"
            else:
                level = "LOW"
            add_signal(
                file_path=file_path,
                company=company,
                statement_period_end=period_end,
                period_sort_key=period_sort_key,
                signal_type="liquidity",
                signal_name="cash_runway_risk",
                signal_value=runway,
                risk_level=level,
                explanation=(
                    f"Cash runway={runway:.2f} periods; "
                    f"<{thresholds.runway_critical_periods:.1f}=CRITICAL, "
                    f"<{thresholds.runway_high_periods:.1f}=HIGH."
                ),
            )

    # Cross-period margin compression
    margin_by_company: Dict[str, List[Dict[str, object]]] = {}
    for (company, _period_end), metric_map in by_period.items():
        row = metric_map.get("ebit_margin_pct")
        if row is not None:
            margin_by_company.setdefault(company, []).append(row)

    for company, series in margin_by_company.items():
        sorted_series = sorted(
            series,
            key=lambda r: (
                int(r.get("period_sort_key", 0) or 0),
                str(r.get("statement_period_end", "")),
            ),
        )
        consecutive_drops = 0
        for idx in range(1, len(sorted_series)):
            prev = sorted_series[idx - 1]
            cur = sorted_series[idx]
            prev_margin = float(prev.get("value_num", 0.0) or 0.0)
            cur_margin = float(cur.get("value_num", 0.0) or 0.0)
            drop_pp = prev_margin - cur_margin
            drop_bps = drop_pp * 100.0
            if (
                abs(prev_margin) > thresholds.max_abs_margin_pct
                or abs(cur_margin) > thresholds.max_abs_margin_pct
                or abs(drop_bps) > thresholds.max_abs_margin_drop_bps
            ):
                consecutive_drops = 0
                continue
            if drop_pp > 0:
                consecutive_drops += 1
            else:
                consecutive_drops = 0

            if drop_bps > thresholds.margin_drop_bps:
                level = "CRITICAL" if drop_bps > (thresholds.margin_drop_bps * 2.0) else "HIGH"
                add_signal(
                    file_path=str(cur.get("source_file", "")),
                    company=company,
                    statement_period_end=str(cur.get("statement_period_end", "")),
                    period_sort_key=int(cur.get("period_sort_key", 0) or 0),
                    signal_type="profitability",
                    signal_name="ebit_margin_compression",
                    signal_value=drop_bps,
                    risk_level=level,
                    explanation=(
                        f"EBIT margin dropped {drop_bps:.0f} bps from "
                        f"{prev_margin:.2f}% to {cur_margin:.2f}%."
                    ),
                )

            if consecutive_drops >= thresholds.consecutive_margin_drops:
                add_signal(
                    file_path=str(cur.get("source_file", "")),
                    company=company,
                    statement_period_end=str(cur.get("statement_period_end", "")),
                    period_sort_key=int(cur.get("period_sort_key", 0) or 0),
                    signal_type="profitability",
                    signal_name="ebit_margin_structural_compression",
                    signal_value=float(consecutive_drops),
                    risk_level="HIGH",
                    explanation=(
                        f"EBIT margin declined for {consecutive_drops} consecutive periods "
                        f"(latest {prev_margin:.2f}% -> {cur_margin:.2f}%)."
                    ),
                )

    # Deduplicate strongest risk per (file, period, signal_name)
    risk_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    dedup: Dict[Tuple[str, str, str], Dict[str, object]] = {}
    for sig in signals:
        key = (
            str(sig.get("file", "")),
            str(sig.get("statement_period_end", "")),
            str(sig.get("signal_name", "")),
        )
        prev = dedup.get(key)
        if prev is None:
            dedup[key] = sig
            continue
        prev_rank = risk_rank.get(str(prev.get("risk_level", "LOW")).upper(), -1)
        cur_rank = risk_rank.get(str(sig.get("risk_level", "LOW")).upper(), -1)
        if cur_rank > prev_rank:
            dedup[key] = sig

    return sorted(
        dedup.values(),
        key=lambda s: (
            str(s.get("company", "")),
            int(s.get("period_sort_key", 0) or 0),
            str(s.get("signal_name", "")),
        ),
    )


def write_json(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def write_csv(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "file",
        "statement_period_end",
        "company",
        "period_sort_key",
        "signal_type",
        "signal_name",
        "signal_value",
        "risk_level",
        "explanation",
        "created_utc",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def store_signals_sqlite(rows: List[Dict[str, object]], db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_risk_signals (
                file TEXT NOT NULL,
                statement_period_end TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                period_sort_key INTEGER NOT NULL DEFAULT 0,
                signal_type TEXT NOT NULL,
                signal_name TEXT NOT NULL,
                signal_value REAL,
                risk_level TEXT NOT NULL,
                explanation TEXT NOT NULL DEFAULT '',
                created_utc TEXT NOT NULL DEFAULT '',
                updated_utc TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (file, statement_period_end, signal_name)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_fin_risk_company_period "
            "ON financial_risk_signals(company, period_sort_key)"
        )
        # Deterministic rebuild to avoid stale signals after threshold/logic changes.
        cur.execute("DELETE FROM financial_risk_signals")
        now = utc_now_iso()
        upsert_sql = """
            INSERT INTO financial_risk_signals (
                file, statement_period_end, company, period_sort_key, signal_type,
                signal_name, signal_value, risk_level, explanation, created_utc, updated_utc
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(file, statement_period_end, signal_name) DO UPDATE SET
                company=excluded.company,
                period_sort_key=excluded.period_sort_key,
                signal_type=excluded.signal_type,
                signal_value=excluded.signal_value,
                risk_level=excluded.risk_level,
                explanation=excluded.explanation,
                updated_utc=excluded.updated_utc
        """
        for row in rows:
            cur.execute(
                upsert_sql,
                (
                    str(row.get("file", "")),
                    str(row.get("statement_period_end", "")),
                    str(row.get("company", "")),
                    int(row.get("period_sort_key", 0) or 0),
                    str(row.get("signal_type", "")),
                    str(row.get("signal_name", "")),
                    _safe_float(row.get("signal_value")),
                    str(row.get("risk_level", "LOW")),
                    str(row.get("explanation", "")),
                    str(row.get("created_utc", now)),
                    now,
                ),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute cross-period risk signals from derived metrics.")
    ap.add_argument("--sqlite", default="reports/financial_metrics.sqlite", help="SQLite DB containing derived_metrics table.")
    ap.add_argument("--out-json", default="reports/financial_risk_signals.json")
    ap.add_argument("--out-csv", default="reports/financial_risk_signals.csv")
    ap.add_argument("--risk-profile", choices=["institutional", "aggressive"], default="institutional")
    ap.add_argument("--min-canonical-confidence-floor", type=int, default=3)
    ap.add_argument("--min-integrity-score", type=int, default=2)
    ap.add_argument("--min-integrity-checks-evaluated", type=int, default=0)
    ap.add_argument(
        "--strict-integrity",
        action="store_true",
        help="Require at least one evaluated integrity check (equivalent to min-integrity-checks-evaluated>=1).",
    )
    ap.add_argument("--leverage-low-max", type=float, default=None)
    ap.add_argument("--leverage-medium-max", type=float, default=None)
    ap.add_argument("--runway-high-periods", type=float, default=None)
    ap.add_argument("--runway-critical-periods", type=float, default=None)
    ap.add_argument("--margin-drop-bps", type=float, default=None)
    ap.add_argument("--consecutive-margin-drops", type=int, default=None)
    ap.add_argument("--max-abs-margin-pct", type=float, default=None)
    ap.add_argument("--max-abs-margin-drop-bps", type=float, default=None)
    args = ap.parse_args()

    db_path = Path(args.sqlite).resolve()
    base = thresholds_for_profile(args.risk_profile)
    th = SignalThresholds(
        leverage_low_max=float(args.leverage_low_max) if args.leverage_low_max is not None else base.leverage_low_max,
        leverage_medium_max=float(args.leverage_medium_max)
        if args.leverage_medium_max is not None
        else base.leverage_medium_max,
        runway_high_periods=float(args.runway_high_periods)
        if args.runway_high_periods is not None
        else base.runway_high_periods,
        runway_critical_periods=float(args.runway_critical_periods)
        if args.runway_critical_periods is not None
        else base.runway_critical_periods,
        margin_drop_bps=float(args.margin_drop_bps) if args.margin_drop_bps is not None else base.margin_drop_bps,
        consecutive_margin_drops=int(args.consecutive_margin_drops)
        if args.consecutive_margin_drops is not None
        else base.consecutive_margin_drops,
        max_abs_margin_pct=float(args.max_abs_margin_pct)
        if args.max_abs_margin_pct is not None
        else base.max_abs_margin_pct,
        max_abs_margin_drop_bps=float(args.max_abs_margin_drop_bps)
        if args.max_abs_margin_drop_bps is not None
        else base.max_abs_margin_drop_bps,
    )

    min_integrity_checks_evaluated = max(0, int(args.min_integrity_checks_evaluated))
    if args.strict_integrity and min_integrity_checks_evaluated < 1:
        min_integrity_checks_evaluated = 1

    rows = load_derived_rows_sqlite(
        db_path,
        min_canonical_confidence_floor=max(0, int(args.min_canonical_confidence_floor)),
        min_integrity_score=max(0, int(args.min_integrity_score)),
        min_integrity_checks_evaluated=min_integrity_checks_evaluated,
    )
    signals = build_risk_signals(rows, th)

    out_json = Path(args.out_json).resolve()
    out_csv = Path(args.out_csv).resolve()
    write_json(signals, out_json)
    write_csv(signals, out_csv)
    written = store_signals_sqlite(signals, db_path)

    by_level: Dict[str, int] = {}
    for s in signals:
        level = str(s.get("risk_level", "LOW")).upper()
        by_level[level] = by_level.get(level, 0) + 1
    level_summary = ", ".join(f"{k}={v}" for k, v in sorted(by_level.items())) if by_level else "none"

    print(f"Risk signals: {len(signals)}")
    print(f"Risk levels: {level_summary}")
    print(f"Risk JSON: {out_json}")
    print(f"Risk CSV: {out_csv}")
    print(f"Risk SQLite upserted: {written}")
    print(f"Risk SQLite DB: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
