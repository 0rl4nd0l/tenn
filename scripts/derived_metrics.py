#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from scripts.reporting.offline_artifact_authority import (
        artifact_record,
        build_authority_metadata,
        write_authority_manifest,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct `python scripts/...` runs
    from reporting.offline_artifact_authority import (
        artifact_record,
        build_authority_metadata,
        write_authority_manifest,
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_rows(path: Path) -> List[Dict[str, object]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, list):
        raise ValueError(f"Expected JSON array at {path}")
    return [r for r in obj if isinstance(r, dict)]


def load_statement_integrity_index(db_path: Path) -> Dict[Tuple[str, str], Dict[str, object]]:
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name='financial_statement_integrity'
            """
        )
        if cur.fetchone() is None:
            return {}
        cur.execute(
            """
            SELECT
                file,
                statement_period_end,
                integrity_score,
                integrity_checks_evaluated,
                integrity_checks_passed,
                integrity_score_max,
                data_anomaly_level
            FROM financial_statement_integrity
            """
        )
        out: Dict[Tuple[str, str], Dict[str, object]] = {}
        for row in cur.fetchall():
            file_path, period_end, score, evaluated, passed, score_max, anomaly = row
            out[(str(file_path or ""), str(period_end or ""))] = {
                "integrity_score": int(score or 0),
                "integrity_checks_evaluated": int(evaluated or 0),
                "integrity_checks_passed": int(passed or 0),
                "integrity_score_max": int(score_max or 4),
                "data_anomaly_level": str(anomaly or "UNKNOWN"),
            }
        return out
    finally:
        conn.close()


def _to_float(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


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


def _period_sort_key(period_end: str) -> int:
    try:
        return int(period_end.replace("-", ""))
    except (TypeError, ValueError):
        return 0


def _integrity_key(row: Dict[str, object]) -> Tuple[str, str]:
    return (
        str(row.get("file", "")).strip(),
        str(row.get("statement_period_end", "")).strip() or str(row.get("period_end_date", "")).strip(),
    )


def apply_statement_integrity_index(
    rows: List[Dict[str, object]],
    integrity_index: Dict[Tuple[str, str], Dict[str, object]],
) -> List[Dict[str, object]]:
    if not integrity_index:
        return rows
    out: List[Dict[str, object]] = []
    for row in rows:
        key = _integrity_key(row)
        meta = integrity_index.get(key)
        if not meta:
            out.append(row)
            continue
        rr = dict(row)
        rr["integrity_score"] = int(meta.get("integrity_score", rr.get("integrity_score", 0)) or 0)
        rr["integrity_checks_evaluated"] = int(
            meta.get("integrity_checks_evaluated", rr.get("integrity_checks_evaluated", 0)) or 0
        )
        rr["integrity_checks_passed"] = int(meta.get("integrity_checks_passed", rr.get("integrity_checks_passed", 0)) or 0)
        rr["integrity_score_max"] = int(meta.get("integrity_score_max", rr.get("integrity_score_max", 4)) or 4)
        rr["data_anomaly_level"] = str(meta.get("data_anomaly_level", rr.get("data_anomaly_level", "UNKNOWN")))
        out.append(rr)
    return out


def _row_score(row: Dict[str, object]) -> Tuple[int, float, int]:
    return (
        int(row.get("canonical_confidence_score", 0) or 0),
        float(row.get("confidence", 0.0) or 0.0),
        int(row.get("line_no", 0) or 0),
    )


def _variant_rank(variant: str, preferred: List[str]) -> int:
    v = (variant or "").strip().lower()
    for idx, pref in enumerate(preferred):
        if pref in v:
            return idx
    return len(preferred)


def _pick_metric_row(rows: List[Dict[str, object]], metric: str, preferred_variants: Optional[List[str]] = None) -> Optional[Dict[str, object]]:
    cands = [r for r in rows if str(r.get("metric", "")).strip().lower() == metric and str(r.get("value_type", "")) == "amount"]
    if not cands:
        return None
    preferred = preferred_variants or []
    ranked = sorted(
        cands,
        key=lambda r: (
            -_variant_rank(str(r.get("metric_variant", "")), preferred),
            *_row_score(r),
        ),
        reverse=True,
    )
    return ranked[0]


def gate_rows(
    rows: List[Dict[str, object]],
    *,
    min_canonical_confidence: int,
    min_integrity_score: int,
    min_integrity_checks_evaluated: int,
) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for r in rows:
        if not str(r.get("statement_period_end", "")).strip():
            continue
        if int(r.get("canonical_confidence_score", 0) or 0) < min_canonical_confidence:
            continue
        if int(r.get("integrity_score", 0) or 0) < min_integrity_score:
            continue
        if int(r.get("integrity_checks_evaluated", 0) or 0) < min_integrity_checks_evaluated:
            continue
        out.append(r)
    return out


def _derived_row_id(row: Dict[str, object]) -> str:
    key = "|".join(
        [
            str(row.get("company", "")),
            str(row.get("statement_period_end", "")),
            str(row.get("metric", "")),
            str(row.get("source_file", "")),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def build_derived_metrics(
    rows: List[Dict[str, object]],
    *,
    min_canonical_confidence: int,
    min_integrity_score: int,
    min_integrity_checks_evaluated: int,
    default_tax_rate: float,
) -> List[Dict[str, object]]:
    gated = gate_rows(
        rows,
        min_canonical_confidence=min_canonical_confidence,
        min_integrity_score=min_integrity_score,
        min_integrity_checks_evaluated=min_integrity_checks_evaluated,
    )

    groups: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for r in gated:
        file_path = str(r.get("file", ""))
        period_end = str(r.get("statement_period_end", "")).strip() or str(r.get("period_end_date", "")).strip()
        if not file_path or not period_end:
            continue
        company = str(r.get("company", "")).strip() or infer_company_from_path(file_path)
        groups.setdefault((company, period_end), []).append(r)

    derived: List[Dict[str, object]] = []
    now = utc_now_iso()

    per_company_points: Dict[str, List[Tuple[str, Dict[str, Optional[float]], Dict[str, object]]]] = {}

    for (company, period_end), rs in groups.items():
        source_file = str(_pick_metric_row(rs, "revenue").get("file", "")) if _pick_metric_row(rs, "revenue") else str(rs[0].get("file", ""))
        period_key = _period_sort_key(period_end)
        integrity_score = int(max((int(r.get("integrity_score", 0) or 0) for r in rs), default=0))
        integrity_eval = int(max((int(r.get("integrity_checks_evaluated", 0) or 0) for r in rs), default=0))
        anomaly = str(max((str(r.get("data_anomaly_level", "UNKNOWN")) for r in rs), default="UNKNOWN"))
        conf_floor = int(min((int(r.get("canonical_confidence_score", 0) or 0) for r in rs), default=0))

        rev_r = _pick_metric_row(rs, "revenue")
        ebit_r = _pick_metric_row(rs, "ebit", preferred_variants=["underlying", "adjusted", "statutory"])
        ebitda_r = _pick_metric_row(rs, "ebitda", preferred_variants=["underlying", "adjusted", "statutory"])
        npat_r = _pick_metric_row(rs, "npat") or _pick_metric_row(rs, "net_income")
        net_debt_r = _pick_metric_row(rs, "net_debt")
        total_debt_r = _pick_metric_row(rs, "total_debt")
        total_equity_r = _pick_metric_row(rs, "total_equity")
        fcf_r = _pick_metric_row(rs, "free_cash_flow")
        ocf_r = _pick_metric_row(rs, "operating_cash_flow")
        cash_r = _pick_metric_row(rs, "cash_and_equivalents_closing") or _pick_metric_row(rs, "cash_and_equivalents")

        rev = _to_float(rev_r.get("value")) if rev_r else None
        ebit = _to_float(ebit_r.get("value")) if ebit_r else None
        ebitda = _to_float(ebitda_r.get("value")) if ebitda_r else None
        npat = _to_float(npat_r.get("value")) if npat_r else None
        net_debt = _to_float(net_debt_r.get("value")) if net_debt_r else None
        total_debt = _to_float(total_debt_r.get("value")) if total_debt_r else None
        total_equity = _to_float(total_equity_r.get("value")) if total_equity_r else None
        fcf = _to_float(fcf_r.get("value")) if fcf_r else None
        ocf = _to_float(ocf_r.get("value")) if ocf_r else None
        cash = _to_float(cash_r.get("value")) if cash_r else None

        def add(metric: str, value_num: float, unit: str, formula: str, inputs: Dict[str, object]) -> None:
            row = {
                "company": company,
                "statement_period_end": period_end,
                "period_sort_key": period_key,
                "metric": metric,
                "value_num": float(value_num),
                "unit": unit,
                "formula": formula,
                "inputs_json": json.dumps(inputs, sort_keys=True),
                "source_file": source_file,
                "canonical_confidence_floor": conf_floor,
                "integrity_score": integrity_score,
                "integrity_checks_evaluated": integrity_eval,
                "data_anomaly_level": anomaly,
                "created_utc": now,
            }
            row["derived_row_id"] = _derived_row_id(row)
            derived.append(row)

        if net_debt is None and total_debt is not None and cash is not None:
            net_debt = total_debt - cash
        if total_debt is None and net_debt is not None and cash is not None:
            total_debt = net_debt + cash

        if ebitda is not None:
            add(
                "ebitda_amount",
                ebitda,
                "amount",
                "ebitda",
                {"ebitda": ebitda},
            )

        if ebit is not None and rev is not None and abs(rev) > 1e-9:
            add(
                "ebit_margin_pct",
                (ebit / rev) * 100.0,
                "percent",
                "(ebit / revenue) * 100",
                {"ebit": ebit, "revenue": rev},
            )

        if net_debt is not None and ebitda is not None and abs(ebitda) > 1e-9:
            add(
                "net_debt_to_ebitda",
                net_debt / ebitda,
                "ratio",
                "net_debt / ebitda",
                {"net_debt": net_debt, "ebitda": ebitda},
            )

        if total_debt is not None and total_equity is not None and abs(total_equity) > 1e-9:
            add(
                "debt_to_equity",
                total_debt / total_equity,
                "ratio",
                "total_debt / total_equity",
                {"total_debt": total_debt, "total_equity": total_equity},
            )

        if ebit is not None and total_debt is not None and total_equity is not None and cash is not None:
            invested_capital = total_debt + total_equity - cash
            if abs(invested_capital) > 1e-9:
                nopat = ebit * (1.0 - default_tax_rate)
                add(
                    "roic_pct",
                    (nopat / invested_capital) * 100.0,
                    "percent",
                    "(ebit * (1 - tax_rate)) / (total_debt + total_equity - cash) * 100",
                    {
                        "ebit": ebit,
                        "tax_rate": default_tax_rate,
                        "nopat": nopat,
                        "total_debt": total_debt,
                        "total_equity": total_equity,
                        "cash": cash,
                    },
                )

        if fcf is not None:
            base = npat if npat is not None and abs(npat) > 1e-9 else ebit
            if base is not None and abs(base) > 1e-9:
                add(
                    "fcf_conversion_pct",
                    (fcf / base) * 100.0,
                    "percent",
                    "(free_cash_flow / base_earnings) * 100",
                    {"free_cash_flow": fcf, "base_earnings": base},
                )

        runway_base = fcf if fcf is not None and fcf < 0 else ocf if ocf is not None and ocf < 0 else None
        if cash is not None and runway_base is not None:
            add(
                "cash_runway_periods",
                cash / abs(runway_base),
                "periods",
                "cash_and_equivalents / abs(negative_cash_flow)",
                {"cash_and_equivalents": cash, "negative_cash_flow": runway_base},
            )

        per_company_points.setdefault(company, []).append(
            (
                period_end,
                {"revenue": rev, "ebit": ebit},
                {
                    "company": company,
                    "statement_period_end": period_end,
                    "period_sort_key": period_key,
                    "source_file": source_file,
                    "canonical_confidence_floor": conf_floor,
                    "integrity_score": integrity_score,
                    "integrity_checks_evaluated": integrity_eval,
                    "data_anomaly_level": anomaly,
                    "created_utc": now,
                },
            )
        )

    for company, pts in per_company_points.items():
        pts_sorted = sorted(pts, key=lambda t: t[0])
        for i in range(1, len(pts_sorted)):
            prev_period, prev_vals, _ = pts_sorted[i - 1]
            cur_period, cur_vals, meta = pts_sorted[i]
            prev_rev = prev_vals.get("revenue")
            cur_rev = cur_vals.get("revenue")
            prev_ebit = prev_vals.get("ebit")
            cur_ebit = cur_vals.get("ebit")
            if prev_rev is None or cur_rev is None or prev_ebit is None or cur_ebit is None:
                continue
            d_rev = cur_rev - prev_rev
            d_ebit = cur_ebit - prev_ebit
            if abs(d_rev) > 1e-9:
                row = {
                    **meta,
                    "metric": "incremental_margin_pct",
                    "value_num": (d_ebit / d_rev) * 100.0,
                    "unit": "percent",
                    "formula": "(delta_ebit / delta_revenue) * 100",
                    "inputs_json": json.dumps(
                        {
                            "current_period": cur_period,
                            "previous_period": prev_period,
                            "delta_revenue": d_rev,
                            "delta_ebit": d_ebit,
                        },
                        sort_keys=True,
                    ),
                }
                row["derived_row_id"] = _derived_row_id(row)
                derived.append(row)

        rev_pts = []
        for p, vals, meta in pts_sorted:
            rv = vals.get("revenue")
            if rv is not None and rv > 0:
                rev_pts.append((p, rv, meta))
        if len(rev_pts) >= 2:
            first_p, first_rev, _ = rev_pts[0]
            last_p, last_rev, last_meta = rev_pts[-1]
            try:
                d0 = datetime.strptime(first_p, "%Y-%m-%d")
                d1 = datetime.strptime(last_p, "%Y-%m-%d")
                years = max((d1 - d0).days / 365.25, 0.0)
            except ValueError:
                years = 0.0
            if years >= 1.0 and first_rev > 0:
                cagr = ((last_rev / first_rev) ** (1.0 / years) - 1.0) * 100.0
                row = {
                    **last_meta,
                    "metric": "revenue_cagr_pct",
                    "value_num": cagr,
                    "unit": "percent",
                    "formula": "((revenue_last / revenue_first)^(1/years) - 1) * 100",
                    "inputs_json": json.dumps(
                        {
                            "first_period": first_p,
                            "last_period": last_p,
                            "first_revenue": first_rev,
                            "last_revenue": last_rev,
                            "years": years,
                        },
                        sort_keys=True,
                    ),
                }
                row["derived_row_id"] = _derived_row_id(row)
                derived.append(row)

    return derived


def write_csv(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "derived_row_id",
        "company",
        "statement_period_end",
        "period_sort_key",
        "metric",
        "value_num",
        "unit",
        "formula",
        "inputs_json",
        "source_file",
        "canonical_confidence_floor",
        "integrity_score",
        "integrity_checks_evaluated",
        "data_anomaly_level",
        "created_utc",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_json(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def store_sqlite(rows: List[Dict[str, object]], db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS derived_metrics (
                derived_row_id TEXT PRIMARY KEY,
                company TEXT NOT NULL DEFAULT '',
                statement_period_end TEXT NOT NULL DEFAULT '',
                period_sort_key INTEGER NOT NULL DEFAULT 0,
                metric TEXT NOT NULL,
                value_num REAL NOT NULL,
                unit TEXT NOT NULL DEFAULT '',
                formula TEXT NOT NULL DEFAULT '',
                inputs_json TEXT NOT NULL DEFAULT '{}',
                source_file TEXT NOT NULL DEFAULT '',
                canonical_confidence_floor INTEGER NOT NULL DEFAULT 0,
                integrity_score INTEGER NOT NULL DEFAULT 0,
                integrity_checks_evaluated INTEGER NOT NULL DEFAULT 0,
                data_anomaly_level TEXT NOT NULL DEFAULT 'UNKNOWN',
                created_utc TEXT NOT NULL DEFAULT '',
                updated_utc TEXT NOT NULL DEFAULT ''
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_derived_company_metric_period "
            "ON derived_metrics(company, metric, period_sort_key)"
        )
        now = utc_now_iso()
        upsert_sql = """
            INSERT INTO derived_metrics (
                derived_row_id, company, statement_period_end, period_sort_key, metric, value_num, unit, formula,
                inputs_json, source_file, canonical_confidence_floor, integrity_score, integrity_checks_evaluated,
                data_anomaly_level, created_utc, updated_utc
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?
            )
            ON CONFLICT(derived_row_id) DO UPDATE SET
                company=excluded.company,
                statement_period_end=excluded.statement_period_end,
                period_sort_key=excluded.period_sort_key,
                metric=excluded.metric,
                value_num=excluded.value_num,
                unit=excluded.unit,
                formula=excluded.formula,
                inputs_json=excluded.inputs_json,
                source_file=excluded.source_file,
                canonical_confidence_floor=excluded.canonical_confidence_floor,
                integrity_score=excluded.integrity_score,
                integrity_checks_evaluated=excluded.integrity_checks_evaluated,
                data_anomaly_level=excluded.data_anomaly_level,
                updated_utc=excluded.updated_utc
        """
        for r in rows:
            cur.execute(
                upsert_sql,
                (
                    str(r.get("derived_row_id", "")),
                    str(r.get("company", "")),
                    str(r.get("statement_period_end", "")),
                    int(r.get("period_sort_key", 0) or 0),
                    str(r.get("metric", "")),
                    float(r.get("value_num", 0.0) or 0.0),
                    str(r.get("unit", "")),
                    str(r.get("formula", "")),
                    str(r.get("inputs_json", "{}")),
                    str(r.get("source_file", "")),
                    int(r.get("canonical_confidence_floor", 0) or 0),
                    int(r.get("integrity_score", 0) or 0),
                    int(r.get("integrity_checks_evaluated", 0) or 0),
                    str(r.get("data_anomaly_level", "UNKNOWN")),
                    str(r.get("created_utc", now)),
                    now,
                ),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def default_authority_path(out_json: Path) -> Path:
    return out_json.with_suffix(".authority.json")


def build_derived_authority_metadata(
    *,
    canonical_path: Path,
    out_json: Path,
    out_csv: Path,
    out_sqlite: Path,
    derived_rows: int,
    sqlite_rows_written: int,
    integrity_db_path: Path,
    min_canonical_confidence: int,
    min_integrity_score: int,
    min_integrity_checks_evaluated: int,
    default_tax_rate: float,
) -> Dict[str, object]:
    source_artifacts = [
        artifact_record(canonical_path, "report_local_selected_metric_rows"),
    ]
    if integrity_db_path.exists():
        source_artifacts.append(artifact_record(integrity_db_path, "report_local_statement_integrity_sqlite"))
    return build_authority_metadata(
        artifact_type="derived_financial_metrics_report",
        producer="scripts/derived_metrics.py",
        lane="Analysis",
        source_artifacts=source_artifacts,
        output_artifacts=[
            artifact_record(out_json, "derived_metrics_json"),
            artifact_record(out_csv, "derived_metrics_csv"),
            artifact_record(out_sqlite, "derived_metrics_sqlite"),
        ],
        extra_do_not_overclaim=[
            "Derived metrics are analysis outputs, not extracted source financial facts.",
            "SQLite output is a report-local projection and must not be used as canonical financial truth.",
        ],
        extra={
            "derived_rows": derived_rows,
            "sqlite_rows_written": sqlite_rows_written,
            "min_canonical_confidence": min_canonical_confidence,
            "min_integrity_score": min_integrity_score,
            "min_integrity_checks_evaluated": min_integrity_checks_evaluated,
            "default_tax_rate": default_tax_rate,
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute derived financial metrics from canonical rows.")
    ap.add_argument("--canonical-json", required=True, help="Canonical JSON output from extract_financial_metrics.py")
    ap.add_argument("--out-json", default="reports/derived_metrics.json")
    ap.add_argument("--out-csv", default="reports/derived_metrics.csv")
    ap.add_argument("--out-sqlite", default="reports/financial_metrics.sqlite")
    ap.add_argument(
        "--authority-json",
        default="",
        help="Optional report-local authority manifest path. Default: <out-json stem>.authority.json",
    )
    ap.add_argument(
        "--integrity-sqlite",
        default="",
        help="Optional SQLite DB containing financial_statement_integrity table (defaults to --out-sqlite when available).",
    )
    ap.add_argument("--min-canonical-confidence", type=int, default=3)
    ap.add_argument("--min-integrity-score", type=int, default=2)
    ap.add_argument("--min-integrity-checks-evaluated", type=int, default=0)
    ap.add_argument(
        "--strict-integrity",
        action="store_true",
        help="Require at least one evaluated integrity check (equivalent to min-integrity-checks-evaluated>=1).",
    )
    ap.add_argument("--default-tax-rate", type=float, default=0.30)
    args = ap.parse_args()

    canonical_path = Path(args.canonical_json).resolve()
    if not canonical_path.exists():
        print(f"[fail] canonical json not found: {canonical_path}")
        return 2

    rows = load_rows(canonical_path)
    integrity_db_path = Path(args.integrity_sqlite).resolve() if args.integrity_sqlite else Path(args.out_sqlite).resolve()
    integrity_index = load_statement_integrity_index(integrity_db_path)
    if integrity_index:
        rows = apply_statement_integrity_index(rows, integrity_index)
    min_integrity_checks_evaluated = max(0, int(args.min_integrity_checks_evaluated))
    if args.strict_integrity and min_integrity_checks_evaluated < 1:
        min_integrity_checks_evaluated = 1
    default_tax_rate = min(max(float(args.default_tax_rate), 0.0), 1.0)

    derived = build_derived_metrics(
        rows,
        min_canonical_confidence=max(0, int(args.min_canonical_confidence)),
        min_integrity_score=max(0, int(args.min_integrity_score)),
        min_integrity_checks_evaluated=min_integrity_checks_evaluated,
        default_tax_rate=default_tax_rate,
    )

    out_json = Path(args.out_json)
    out_csv = Path(args.out_csv)
    out_sqlite = Path(args.out_sqlite)
    write_json(derived, out_json)
    write_csv(derived, out_csv)
    written = store_sqlite(derived, out_sqlite)
    authority_path = Path(args.authority_json) if args.authority_json else default_authority_path(out_json)
    authority = build_derived_authority_metadata(
        canonical_path=canonical_path,
        out_json=out_json,
        out_csv=out_csv,
        out_sqlite=out_sqlite,
        derived_rows=len(derived),
        sqlite_rows_written=written,
        integrity_db_path=integrity_db_path,
        min_canonical_confidence=max(0, int(args.min_canonical_confidence)),
        min_integrity_score=max(0, int(args.min_integrity_score)),
        min_integrity_checks_evaluated=min_integrity_checks_evaluated,
        default_tax_rate=default_tax_rate,
    )
    write_authority_manifest(authority_path, authority)

    print(f"Derived metric rows: {len(derived)}")
    print(f"Derived JSON: {out_json}")
    print(f"Derived CSV: {out_csv}")
    print(f"Derived SQLite upserted: {written}")
    print(f"Derived SQLite DB: {out_sqlite}")
    print(f"Authority manifest: {authority_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
