#!/usr/bin/env python3
import argparse
import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


DEFAULT_METRICS = [
    "revenue",
    "ebit",
    "ebitda",
    "net_income",
    "total_debt",
    "cash_and_equivalents",
]
RISK_INPUT_DERIVED_METRICS = {"net_debt_to_ebitda", "cash_runway_periods", "ebit_margin_pct"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def infer_company_from_path(file_path: str) -> str:
    p = Path(file_path)
    parts = p.parts
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if len(parts) >= 2:
        return parts[-2]
    return ""


def parse_metric_list(text: str) -> List[str]:
    out: List[str] = []
    for tok in (text or "").split(","):
        m = tok.strip().lower()
        if m and m not in out:
            out.append(m)
    return out


def parse_company_filter(values: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for value in values:
        for tok in str(value).split(","):
            v = tok.strip()
            if v:
                out.add(v)
    return out


def load_rows_from_json(path: Path) -> List[Dict[str, object]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, list):
        raise ValueError(f"Expected JSON list in {path}")
    return [r for r in obj if isinstance(r, dict)]


def load_rows_from_csv(path: Path) -> List[Dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def normalize_metric(row: Dict[str, object]) -> str:
    metric_base = str(row.get("metric_base", "")).strip().lower()
    if metric_base:
        return metric_base
    metric = str(row.get("metric", "")).strip().lower()
    if metric in {"cash_and_equivalents_opening", "cash_and_equivalents_closing"}:
        return "cash_and_equivalents"
    return metric


def normalize_period_end(row: Dict[str, object]) -> str:
    return (
        str(row.get("statement_period_end", "")).strip()
        or str(row.get("period_end_date", "")).strip()
        or str(row.get("period_sort_date", "")).strip()
    )


def period_sort_key(period_end: str) -> int:
    if not period_end:
        return 0
    try:
        return int(period_end.replace("-", ""))
    except ValueError:
        return 0


def load_integrity_index(db_path: Path) -> Tuple[Dict[Tuple[str, str], Dict[str, object]], Dict[Tuple[str, str], Dict[str, object]]]:
    by_company: Dict[Tuple[str, str], Dict[str, object]] = {}
    by_file: Dict[Tuple[str, str], Dict[str, object]] = {}
    if not db_path.exists():
        return by_company, by_file
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='financial_statement_integrity'")
        if cur.fetchone() is None:
            return by_company, by_file
        cur.execute(
            """
            SELECT
                file,
                company,
                statement_period_end,
                integrity_score,
                integrity_checks_evaluated,
                integrity_checks_passed,
                integrity_score_max,
                data_anomaly_level
            FROM financial_statement_integrity
            """
        )
        for rec in cur.fetchall():
            file_path = str(rec[0] or "")
            company = str(rec[1] or "")
            period_end = str(rec[2] or "")
            meta = {
                "integrity_score": int(rec[3] or 0),
                "integrity_checks_evaluated": int(rec[4] or 0),
                "integrity_checks_passed": int(rec[5] or 0),
                "integrity_score_max": int(rec[6] or 4),
                "data_anomaly_level": str(rec[7] or "UNKNOWN"),
            }
            if company and period_end:
                by_company[(company, period_end)] = meta
            if file_path and period_end:
                by_file[(file_path, period_end)] = meta
    finally:
        conn.close()
    return by_company, by_file


def load_derived_index(db_path: Path) -> Tuple[Dict[Tuple[str, str], Set[str]], Dict[Tuple[str, str], Set[str]]]:
    by_company: Dict[Tuple[str, str], Set[str]] = {}
    by_file: Dict[Tuple[str, str], Set[str]] = {}
    if not db_path.exists():
        return by_company, by_file
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='derived_metrics'")
        if cur.fetchone() is None:
            return by_company, by_file
        cur.execute(
            """
            SELECT company, statement_period_end, metric, source_file
            FROM derived_metrics
            """
        )
        for rec in cur.fetchall():
            company = str(rec[0] or "")
            period_end = str(rec[1] or "")
            metric = str(rec[2] or "").strip().lower()
            source_file = str(rec[3] or "")
            if company and period_end and metric:
                by_company.setdefault((company, period_end), set()).add(metric)
            if source_file and period_end and metric:
                by_file.setdefault((source_file, period_end), set()).add(metric)
    finally:
        conn.close()
    return by_company, by_file


def load_risk_index(db_path: Path) -> Tuple[Dict[Tuple[str, str], int], Dict[Tuple[str, str], int]]:
    by_company: Dict[Tuple[str, str], int] = {}
    by_file: Dict[Tuple[str, str], int] = {}
    if not db_path.exists():
        return by_company, by_file
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='financial_risk_signals'")
        if cur.fetchone() is None:
            return by_company, by_file
        cur.execute(
            """
            SELECT company, statement_period_end, file, COUNT(*)
            FROM financial_risk_signals
            GROUP BY company, statement_period_end, file
            """
        )
        for rec in cur.fetchall():
            company = str(rec[0] or "")
            period_end = str(rec[1] or "")
            file_path = str(rec[2] or "")
            cnt = int(rec[3] or 0)
            if company and period_end:
                by_company[(company, period_end)] = max(by_company.get((company, period_end), 0), cnt)
            if file_path and period_end:
                by_file[(file_path, period_end)] = max(by_file.get((file_path, period_end), 0), cnt)
    finally:
        conn.close()
    return by_company, by_file


def build_period_matrix(
    rows: List[Dict[str, object]],
    *,
    metrics: List[str],
    company_filter: Set[str],
    sqlite_path: Optional[Path],
) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str], Dict[str, object]] = {}
    for row in rows:
        period_end = normalize_period_end(row)
        if not period_end:
            continue
        file_path = str(row.get("file", "")).strip()
        company = str(row.get("company", "")).strip() or infer_company_from_path(file_path)
        if not company:
            company = "unknown"
        if company_filter and company not in company_filter:
            continue
        key = (company, period_end)
        entry = grouped.get(key)
        if entry is None:
            entry = {
                "company": company,
                "statement_period_end": period_end,
                "source_file": file_path,
                "metrics_present": set(),
                "integrity_score": int(row.get("integrity_score", 0) or 0),
                "integrity_checks_evaluated": int(row.get("integrity_checks_evaluated", 0) or 0),
                "integrity_checks_passed": int(row.get("integrity_checks_passed", 0) or 0),
                "integrity_score_max": int(row.get("integrity_score_max", 4) or 4),
                "data_anomaly_level": str(row.get("data_anomaly_level", "UNKNOWN")),
            }
            grouped[key] = entry
        metric = normalize_metric(row)
        if metric:
            entry["metrics_present"].add(metric)
        # keep strongest available in-row integrity metadata
        entry["integrity_score"] = max(int(entry.get("integrity_score", 0) or 0), int(row.get("integrity_score", 0) or 0))
        entry["integrity_checks_evaluated"] = max(
            int(entry.get("integrity_checks_evaluated", 0) or 0), int(row.get("integrity_checks_evaluated", 0) or 0)
        )
        entry["integrity_checks_passed"] = max(
            int(entry.get("integrity_checks_passed", 0) or 0), int(row.get("integrity_checks_passed", 0) or 0)
        )
        entry["integrity_score_max"] = max(
            int(entry.get("integrity_score_max", 4) or 4), int(row.get("integrity_score_max", 4) or 4)
        )
        if not str(entry.get("source_file", "")) and file_path:
            entry["source_file"] = file_path

    integrity_by_company: Dict[Tuple[str, str], Dict[str, object]] = {}
    integrity_by_file: Dict[Tuple[str, str], Dict[str, object]] = {}
    derived_by_company: Dict[Tuple[str, str], Set[str]] = {}
    derived_by_file: Dict[Tuple[str, str], Set[str]] = {}
    risk_by_company: Dict[Tuple[str, str], int] = {}
    risk_by_file: Dict[Tuple[str, str], int] = {}
    if sqlite_path is not None:
        integrity_by_company, integrity_by_file = load_integrity_index(sqlite_path)
        derived_by_company, derived_by_file = load_derived_index(sqlite_path)
        risk_by_company, risk_by_file = load_risk_index(sqlite_path)

    out: List[Dict[str, object]] = []
    for (company, period_end), entry in grouped.items():
        source_file = str(entry.get("source_file", ""))
        meta = integrity_by_company.get((company, period_end)) or integrity_by_file.get((source_file, period_end))
        if meta is not None:
            entry["integrity_score"] = int(meta.get("integrity_score", entry.get("integrity_score", 0)) or 0)
            entry["integrity_checks_evaluated"] = int(
                meta.get("integrity_checks_evaluated", entry.get("integrity_checks_evaluated", 0)) or 0
            )
            entry["integrity_checks_passed"] = int(
                meta.get("integrity_checks_passed", entry.get("integrity_checks_passed", 0)) or 0
            )
            entry["integrity_score_max"] = int(meta.get("integrity_score_max", entry.get("integrity_score_max", 4)) or 4)
            entry["data_anomaly_level"] = str(meta.get("data_anomaly_level", entry.get("data_anomaly_level", "UNKNOWN")))

        derived_metrics = derived_by_company.get((company, period_end)) or derived_by_file.get((source_file, period_end)) or set()
        risk_signal_count = risk_by_company.get((company, period_end))
        if risk_signal_count is None:
            risk_signal_count = risk_by_file.get((source_file, period_end), 0)

        metrics_present: Set[str] = set(entry.get("metrics_present", set()))
        metric_flags = {m: (m in metrics_present) for m in metrics}
        missing_metrics = [m for m in metrics if m not in metrics_present]
        integrity_checks_evaluated = int(entry.get("integrity_checks_evaluated", 0) or 0)
        derived_ready = bool(derived_metrics)
        risk_ready = bool(set(derived_metrics) & RISK_INPUT_DERIVED_METRICS)

        out.append(
            {
                "company": company,
                "statement_period_end": period_end,
                "period_sort_key": period_sort_key(period_end),
                "source_file": source_file,
                "metrics_present": ",".join(sorted(metrics_present)),
                "missing_metrics": ",".join(missing_metrics),
                "integrity_score": int(entry.get("integrity_score", 0) or 0),
                "integrity_checks_evaluated": integrity_checks_evaluated,
                "integrity_checks_passed": int(entry.get("integrity_checks_passed", 0) or 0),
                "integrity_score_max": int(entry.get("integrity_score_max", 4) or 4),
                "integrity_evaluable": 1 if integrity_checks_evaluated >= 1 else 0,
                "derived_metric_count": len(derived_metrics),
                "derived_ready": 1 if derived_ready else 0,
                "risk_ready": 1 if risk_ready else 0,
                "risk_signal_count": int(risk_signal_count or 0),
                "risk_signaled": 1 if int(risk_signal_count or 0) > 0 else 0,
                "data_anomaly_level": str(entry.get("data_anomaly_level", "UNKNOWN")),
                **{f"has_{m}": 1 if metric_flags[m] else 0 for m in metrics},
            }
        )

    return sorted(out, key=lambda r: (str(r["company"]), int(r["period_sort_key"]), str(r["statement_period_end"])))


def _pct(numer: int, denom: int) -> float:
    if denom <= 0:
        return 0.0
    return (float(numer) / float(denom)) * 100.0


def build_company_summary(period_rows: List[Dict[str, object]], metrics: List[str]) -> List[Dict[str, object]]:
    by_company: Dict[str, List[Dict[str, object]]] = {}
    for row in period_rows:
        by_company.setdefault(str(row["company"]), []).append(row)

    out: List[Dict[str, object]] = []
    for company, rows in sorted(by_company.items()):
        total_periods = len(rows)
        metric_counts = {m: sum(int(r.get(f"has_{m}", 0) or 0) for r in rows) for m in metrics}
        integrity_evaluable_periods = sum(int(r.get("integrity_evaluable", 0) or 0) for r in rows)
        derived_ready_periods = sum(int(r.get("derived_ready", 0) or 0) for r in rows)
        risk_ready_periods = sum(int(r.get("risk_ready", 0) or 0) for r in rows)
        risk_signaled_periods = sum(int(r.get("risk_signaled", 0) or 0) for r in rows)
        periods_sorted = sorted(rows, key=lambda r: int(r.get("period_sort_key", 0) or 0))
        period_start = str(periods_sorted[0]["statement_period_end"]) if periods_sorted else ""
        period_end = str(periods_sorted[-1]["statement_period_end"]) if periods_sorted else ""

        summary: Dict[str, object] = {
            "company": company,
            "total_periods": total_periods,
            "period_start": period_start,
            "period_end": period_end,
            "integrity_evaluable_periods": integrity_evaluable_periods,
            "integrity_evaluable_pct": round(_pct(integrity_evaluable_periods, total_periods), 2),
            "derived_ready_periods": derived_ready_periods,
            "derived_ready_pct": round(_pct(derived_ready_periods, total_periods), 2),
            "risk_ready_periods": risk_ready_periods,
            "risk_ready_pct": round(_pct(risk_ready_periods, total_periods), 2),
            "risk_signaled_periods": risk_signaled_periods,
            "risk_signaled_pct": round(_pct(risk_signaled_periods, total_periods), 2),
            "metric_coverage": {},
        }
        for metric in metrics:
            cnt = metric_counts[metric]
            pct = round(_pct(cnt, total_periods), 2)
            summary[f"{metric}__periods"] = cnt
            summary[f"{metric}__pct"] = pct
            summary["metric_coverage"][metric] = {"periods_present": cnt, "pct_periods": pct}

        out.append(summary)
    return out


def write_json_report(
    summaries: List[Dict[str, object]],
    period_rows: List[Dict[str, object]],
    metrics: List[str],
    out_json: Path,
) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_utc": utc_now_iso(),
        "metrics": metrics,
        "company_count": len(summaries),
        "period_row_count": len(period_rows),
        "companies": summaries,
    }
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_company_csv(summaries: List[Dict[str, object]], metrics: List[str], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "company",
        "total_periods",
        "period_start",
        "period_end",
        "integrity_evaluable_periods",
        "integrity_evaluable_pct",
        "derived_ready_periods",
        "derived_ready_pct",
        "risk_ready_periods",
        "risk_ready_pct",
        "risk_signaled_periods",
        "risk_signaled_pct",
    ]
    for m in metrics:
        fields.append(f"{m}__periods")
        fields.append(f"{m}__pct")
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in summaries:
            w.writerow(row)


def write_period_csv(period_rows: List[Dict[str, object]], metrics: List[str], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "company",
        "statement_period_end",
        "period_sort_key",
        "source_file",
        "metrics_present",
        "missing_metrics",
        "integrity_score",
        "integrity_checks_evaluated",
        "integrity_checks_passed",
        "integrity_score_max",
        "integrity_evaluable",
        "derived_metric_count",
        "derived_ready",
        "risk_ready",
        "risk_signal_count",
        "risk_signaled",
        "data_anomaly_level",
    ] + [f"has_{m}" for m in metrics]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in period_rows:
            w.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build per-company metric coverage and period readiness report.")
    ap.add_argument("--canonical-json", default="", help="Canonical rows JSON (array).")
    ap.add_argument("--canonical-csv", default="", help="Canonical rows CSV.")
    ap.add_argument(
        "--sqlite",
        default="",
        help="Optional SQLite DB with financial_statement_integrity, derived_metrics and financial_risk_signals tables.",
    )
    ap.add_argument(
        "--metrics",
        default=",".join(DEFAULT_METRICS),
        help="Comma-separated base metrics to track coverage for.",
    )
    ap.add_argument(
        "--company",
        action="append",
        default=[],
        help="Optional company filter (repeatable or comma-separated).",
    )
    ap.add_argument("--out-json", default="reports/metric_coverage_report.json")
    ap.add_argument("--out-csv", default="reports/metric_coverage_report.csv")
    ap.add_argument("--out-period-csv", default="reports/metric_coverage_period_matrix.csv")
    args = ap.parse_args()

    canonical_json = str(args.canonical_json or "").strip()
    canonical_csv = str(args.canonical_csv or "").strip()
    if not canonical_json and not canonical_csv:
        ap.error("Provide one of --canonical-json or --canonical-csv")

    metrics = parse_metric_list(args.metrics)
    if not metrics:
        ap.error("--metrics must include at least one metric")
    company_filter = parse_company_filter(args.company)

    if canonical_json:
        rows = load_rows_from_json(Path(canonical_json).resolve())
    else:
        rows = load_rows_from_csv(Path(canonical_csv).resolve())

    sqlite_path: Optional[Path] = None
    if str(args.sqlite or "").strip():
        sqlite_path = Path(args.sqlite).resolve()

    period_rows = build_period_matrix(rows, metrics=metrics, company_filter=company_filter, sqlite_path=sqlite_path)
    summaries = build_company_summary(period_rows, metrics)

    out_json = Path(args.out_json).resolve()
    out_csv = Path(args.out_csv).resolve()
    out_period_csv = Path(args.out_period_csv).resolve()
    write_json_report(summaries, period_rows, metrics, out_json)
    write_company_csv(summaries, metrics, out_csv)
    write_period_csv(period_rows, metrics, out_period_csv)

    print(f"Coverage companies: {len(summaries)}")
    print(f"Coverage periods: {len(period_rows)}")
    print(f"Metrics tracked: {', '.join(metrics)}")
    print(f"Coverage JSON: {out_json}")
    print(f"Coverage CSV: {out_csv}")
    print(f"Coverage period CSV: {out_period_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

