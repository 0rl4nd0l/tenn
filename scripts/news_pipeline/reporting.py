from __future__ import annotations

import csv
import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from .ingest import FailureBucketTracker, REQUIRED_FAILURE_BUCKETS
from .utils import load_ticker_universe, now_utc_iso


def _safe_pct(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round((100.0 * float(num)) / float(den), 4)


def _query_rows(conn: sqlite3.Connection, sql: str, args: Sequence[Any]) -> List[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return list(conn.execute(sql, tuple(args)).fetchall())


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def write_run_reports(
    *,
    db_path: Path,
    run_id: str,
    out_dir: Path,
    ticker_universe_path: Path,
    failures: FailureBucketTracker | None = None,
) -> Dict[str, Any]:
    out_root = Path(out_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    tickers = load_ticker_universe(Path(ticker_universe_path).expanduser().resolve())
    ticker_set = set(tickers)

    conn = sqlite3.connect(str(Path(db_path).expanduser().resolve()))
    conn.row_factory = sqlite3.Row
    try:
        # 1) articles/day by provider
        rows = _query_rows(
            conn,
            """
            SELECT substr(published_at_utc, 1, 10) AS day, provider_best AS provider, COUNT(*) AS articles
              FROM articles
             GROUP BY day, provider
             ORDER BY day DESC, provider ASC
            """,
            (),
        )
        day_rows = [{"day": row["day"], "provider": row["provider"], "articles": int(row["articles"] or 0)} for row in rows]
        _write_csv(out_root / "articles_per_day_by_provider.csv", day_rows, ["day", "provider", "articles"])

        # 2) ticker coverage (1/7/30 days, both lanes)
        now = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)
        coverage_payload: Dict[str, Any] = {"generated_at_utc": now_utc_iso(), "ticker_universe_size": len(tickers), "windows": {}}
        for days in (1, 7, 30):
            since = (now - dt.timedelta(days=days)).isoformat().replace("+00:00", "Z")
            lane_payload: Dict[str, Any] = {}
            for lane in ("high_precision", "high_recall"):
                lane_rows = _query_rows(
                    conn,
                    """
                    SELECT DISTINCT ticker
                      FROM entity_links
                     WHERE lane = ? AND published_at_utc >= ?
                    """,
                    (lane, since),
                )
                covered = {str(row["ticker"] or "") for row in lane_rows if str(row["ticker"] or "")}
                in_universe = covered & ticker_set
                lane_payload[lane] = {
                    "covered_tickers": len(in_universe),
                    "covered_pct": _safe_pct(len(in_universe), len(tickers)),
                }
            coverage_payload["windows"][str(days)] = lane_payload
        _write_json(out_root / "ticker_coverage_1_7_30_days.json", coverage_payload)

        # 3) rejection rates by reason for this run
        rej_rows = _query_rows(
            conn,
            """
            SELECT reason, COUNT(*) AS rejected
              FROM rejected_items
             WHERE run_id = ?
             GROUP BY reason
             ORDER BY rejected DESC, reason ASC
            """,
            (run_id,),
        )
        reject_csv_rows = [{"reason": row["reason"], "rejected": int(row["rejected"] or 0)} for row in rej_rows]
        _write_csv(out_root / "rejections_by_reason.csv", reject_csv_rows, ["reason", "rejected"])

        # 4) duplicate rate
        run_row = conn.execute("SELECT * FROM provider_runs WHERE run_id = ?", (run_id,)).fetchone()
        duplicate_payload = {
            "run_id": run_id,
            "provider": str((run_row["provider"] if run_row else "") or ""),
            "fetched": int((run_row["fetched"] if run_row else 0) or 0),
            "inserted": int((run_row["inserted"] if run_row else 0) or 0),
            "deduped": int((run_row["deduped"] if run_row else 0) or 0),
            "rejected": int((run_row["rejected"] if run_row else 0) or 0),
            "errors": int((run_row["errors"] if run_row else 0) or 0),
        }
        fetched = int(duplicate_payload["fetched"] or 0)
        deduped = int(duplicate_payload["deduped"] or 0)
        duplicate_payload["duplicate_rate_pct"] = _safe_pct(deduped, fetched)
        _write_json(out_root / "duplicate_rates.json", duplicate_payload)

        # 5) top uncovered tickers (30 days, by lane)
        since_30 = (now - dt.timedelta(days=30)).isoformat().replace("+00:00", "Z")
        covered_by_lane: Dict[str, set[str]] = {}
        for lane in ("high_precision", "high_recall"):
            lane_rows = _query_rows(
                conn,
                """
                SELECT DISTINCT ticker
                  FROM entity_links
                 WHERE lane = ? AND published_at_utc >= ?
                """,
                (lane, since_30),
            )
            covered_by_lane[lane] = {str(row["ticker"] or "") for row in lane_rows if str(row["ticker"] or "")}

        uncovered_rows: List[Dict[str, Any]] = []
        for ticker in tickers:
            hp = 1 if ticker in covered_by_lane["high_precision"] else 0
            hr = 1 if ticker in covered_by_lane["high_recall"] else 0
            uncovered_rows.append(
                {
                    "ticker": ticker,
                    "covered_high_precision": hp,
                    "covered_high_recall": hr,
                }
            )
        uncovered_rows.sort(key=lambda row: (row["covered_high_recall"], row["covered_high_precision"], row["ticker"]))
        _write_csv(
            out_root / "top_uncovered_tickers.csv",
            uncovered_rows,
            ["ticker", "covered_high_precision", "covered_high_recall"],
        )

        # 6) failure bucket sample files.
        sample_dir = out_root / "failure_bucket_samples"
        sample_dir.mkdir(parents=True, exist_ok=True)
        if failures is not None:
            failures.write_sample_files(sample_dir)
            failure_payload = failures.as_dict()
        else:
            failure_payload = {
                "counts": {reason: 0 for reason in REQUIRED_FAILURE_BUCKETS},
                "samples": {reason: [] for reason in REQUIRED_FAILURE_BUCKETS},
            }
            sample_rows = _query_rows(
                conn,
                """
                SELECT reason, diagnostics_json
                  FROM rejected_items
                 WHERE run_id = ?
                 ORDER BY reject_id DESC
                """,
                (run_id,),
            )
            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for row in sample_rows:
                reason = str(row["reason"] or "")
                if not reason:
                    continue
                grouped.setdefault(reason, [])
                if len(grouped[reason]) >= 5:
                    continue
                raw_diag = str(row["diagnostics_json"] or "").strip()
                diag = {}
                if raw_diag:
                    try:
                        diag = json.loads(raw_diag)
                    except Exception:
                        diag = {"raw": raw_diag}
                grouped[reason].append(diag)
            for reason, samples in grouped.items():
                failure_payload["counts"][reason] = int(failure_payload["counts"].get(reason, 0)) + len(samples)
                failure_payload["samples"][reason] = samples
            for reason in sorted(failure_payload["counts"]):
                samples = failure_payload["samples"].get(reason, [])
                with (sample_dir / f"{reason}.jsonl").open("w", encoding="utf-8") as fh:
                    for sample in samples:
                        fh.write(json.dumps(sample, ensure_ascii=False) + "\n")

        summary = {
            "run_id": run_id,
            "generated_at_utc": now_utc_iso(),
            "outputs": {
                "articles_per_day_by_provider_csv": "articles_per_day_by_provider.csv",
                "ticker_coverage_json": "ticker_coverage_1_7_30_days.json",
                "rejections_by_reason_csv": "rejections_by_reason.csv",
                "duplicate_rates_json": "duplicate_rates.json",
                "top_uncovered_tickers_csv": "top_uncovered_tickers.csv",
                "failure_bucket_samples_dir": "failure_bucket_samples",
            },
            "failure_buckets": failure_payload.get("counts", {}),
        }
        _write_json(out_root / "report_summary.json", summary)
        return summary
    finally:
        conn.close()
