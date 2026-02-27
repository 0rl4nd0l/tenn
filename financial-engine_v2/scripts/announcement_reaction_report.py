#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse_iso_utc(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def build_close_series(price_payload: dict[str, Any]) -> list[tuple[datetime, float]]:
    history = price_payload.get("history")
    if not isinstance(history, list):
        return []
    deduped: dict[str, tuple[datetime, float]] = {}
    for row in history:
        if not isinstance(row, dict):
            continue
        ts = _parse_iso_utc(row.get("timestamp"))
        close = _safe_float(row.get("close"))
        if ts is None or close is None:
            continue
        deduped[ts.isoformat()] = (ts, close)
    series = list(deduped.values())
    series.sort(key=lambda item: item[0].timestamp())
    return series


def compute_reaction_for_time(
    close_series: list[tuple[datetime, float]],
    published_at: datetime,
) -> dict[str, Any] | None:
    if not close_series:
        return None

    anchor_idx = -1
    for idx, (ts, _) in enumerate(close_series):
        if ts <= published_at:
            anchor_idx = idx
        else:
            break
    if anchor_idx < 0:
        return None

    anchor_ts, anchor_close = close_series[anchor_idx]
    if anchor_close == 0:
        return None

    def _ret(days: int) -> float | None:
        target_idx = anchor_idx + days
        if target_idx >= len(close_series):
            return None
        target_close = close_series[target_idx][1]
        return ((target_close / anchor_close) - 1.0) * 100.0

    return {
        "anchor_time_utc": anchor_ts.isoformat(),
        "anchor_close": anchor_close,
        "ret_1d": _ret(1),
        "ret_5d": _ret(5),
        "ret_20d": _ret(20),
    }


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _normalize_database_url(repo_root: Path, database_url: str) -> str:
    value = (database_url or "").strip()
    if not value:
        value = "sqlite:///./data/fe_local.db"
    if value.startswith("sqlite:///"):
        path_part = value[len("sqlite:///"):]
        if path_part.startswith("./") or not path_part.startswith("/"):
            return f"sqlite:///{(repo_root / path_part).resolve()}"
    return value


def build_report(
    *,
    database_url: str,
    api_base_url: str,
    exchange: str,
    range_: str,
    interval: str,
    days_back: int,
    limit: int,
    top: int,
    ticker_filter: set[str] | None = None,
    doc_class_filter: set[str] | None = None,
) -> dict[str, Any]:
    from cockpit.integrations.backend_api import BackendApiClient
    from sqlalchemy import create_engine, text

    db_url = _normalize_database_url(REPO_ROOT, database_url)
    engine = create_engine(db_url, pool_pre_ping=True)
    since = datetime.now(timezone.utc) - timedelta(days=max(1, int(days_back)))
    since_iso = since.isoformat()

    sql = text(
        """
        select document_id, ticker, doc_class, doc_subtype, published_at, title
        from documents
        where ticker is not null
          and trim(ticker) <> ''
          and published_at is not null
          and published_at >= :since_iso
        order by published_at desc, document_id desc
        limit :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"since_iso": since_iso, "limit": max(1, int(limit))}).mappings().all()

    documents: list[dict[str, Any]] = [dict(r) for r in rows]
    if ticker_filter:
        documents = [d for d in documents if str(d.get("ticker") or "").strip().upper() in ticker_filter]
    if doc_class_filter:
        documents = [
            d
            for d in documents
            if str(d.get("doc_class") or "").strip().lower() in doc_class_filter
        ]

    docs_by_ticker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in documents:
        ticker = str(doc.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        docs_by_ticker[ticker].append(doc)

    client = BackendApiClient(api_base_url)
    ticker_errors: dict[str, str] = {}
    reactions: list[dict[str, Any]] = []
    class_bucket: dict[str, list[float]] = defaultdict(list)
    ticker_bucket: dict[str, list[float]] = defaultdict(list)

    for ticker, docs in docs_by_ticker.items():
        price_result = client.get_price(
            ticker=ticker,
            exchange=exchange,
            range_=range_,
            interval=interval,
            timeout=15.0,
        )
        if not price_result.get("ok"):
            ticker_errors[ticker] = str(price_result.get("error") or "price lookup failed")
            continue

        payload = price_result.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        close_series = build_close_series(payload)
        if not close_series:
            ticker_errors[ticker] = "no close series returned"
            continue

        for doc in docs:
            published_at = _parse_iso_utc(doc.get("published_at"))
            if published_at is None:
                continue
            reaction = compute_reaction_for_time(close_series, published_at=published_at)
            if reaction is None:
                continue

            ret_1d = reaction.get("ret_1d")
            doc_class = str(doc.get("doc_class") or "unknown").strip().lower() or "unknown"
            record = {
                "document_id": doc.get("document_id"),
                "ticker": ticker,
                "doc_class": doc_class,
                "doc_subtype": doc.get("doc_subtype"),
                "published_at": published_at.isoformat(),
                "title": doc.get("title"),
                "anchor_time_utc": reaction.get("anchor_time_utc"),
                "ret_1d": ret_1d,
                "ret_5d": reaction.get("ret_5d"),
                "ret_20d": reaction.get("ret_20d"),
            }
            reactions.append(record)
            if isinstance(ret_1d, float):
                class_bucket[doc_class].append(ret_1d)
                ticker_bucket[ticker].append(ret_1d)

    top_movers = sorted(
        [row for row in reactions if isinstance(row.get("ret_1d"), float)],
        key=lambda row: abs(float(row["ret_1d"])),
        reverse=True,
    )[: max(1, int(top))]

    summary_by_doc_class = []
    for doc_class, values in sorted(class_bucket.items(), key=lambda item: (_avg([abs(x) for x in item[1]]) or 0.0), reverse=True):
        positives = [v for v in values if v > 0]
        summary_by_doc_class.append(
            {
                "doc_class": doc_class,
                "count": len(values),
                "avg_ret_1d": _avg(values),
                "avg_abs_ret_1d": _avg([abs(v) for v in values]),
                "positive_ratio": (len(positives) / len(values)) if values else None,
            }
        )

    summary_by_ticker = []
    for ticker, values in sorted(ticker_bucket.items(), key=lambda item: (_avg([abs(x) for x in item[1]]) or 0.0), reverse=True):
        positives = [v for v in values if v > 0]
        summary_by_ticker.append(
            {
                "ticker": ticker,
                "count": len(values),
                "avg_ret_1d": _avg(values),
                "avg_abs_ret_1d": _avg([abs(v) for v in values]),
                "positive_ratio": (len(positives) / len(values)) if values else None,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "database_url": db_url,
            "api_base_url": api_base_url,
            "exchange": exchange,
            "range": range_,
            "interval": interval,
            "days_back": days_back,
            "limit": limit,
            "top": top,
            "ticker_filter": sorted(ticker_filter) if ticker_filter else [],
            "doc_class_filter": sorted(doc_class_filter) if doc_class_filter else [],
        },
        "documents_scanned": len(documents),
        "tickers_scanned": len(docs_by_ticker),
        "reaction_rows": len(reactions),
        "ticker_price_errors": ticker_errors,
        "top_movers": top_movers,
        "summary_by_doc_class": summary_by_doc_class,
        "summary_by_ticker": summary_by_ticker,
    }


def _parse_csv_set(raw: str | None, *, upper: bool = False, lower: bool = False) -> set[str] | None:
    text_value = str(raw or "").strip()
    if not text_value:
        return None
    out: set[str] = set()
    for part in text_value.split(","):
        token = part.strip()
        if not token:
            continue
        if upper:
            token = token.upper()
        if lower:
            token = token.lower()
        out.add(token)
    return out or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an announcement reaction report (top movers by doc class/ticker).",
    )
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db"))
    parser.add_argument("--api-base-url", default=os.getenv("COCKPIT_BACKEND_API_URL", "http://localhost:8000"))
    parser.add_argument("--exchange", default="ASX")
    parser.add_argument("--range", dest="range_", default="1y")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--days-back", type=int, default=45)
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--ticker", default="", help="Optional comma-separated tickers.")
    parser.add_argument("--doc-class", default="", help="Optional comma-separated doc classes.")
    parser.add_argument(
        "--output",
        default=f"reports/announcement_reaction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ticker_filter = _parse_csv_set(args.ticker, upper=True)
    doc_class_filter = _parse_csv_set(args.doc_class, lower=True)

    report = build_report(
        database_url=args.database_url,
        api_base_url=args.api_base_url,
        exchange=str(args.exchange or "ASX").strip().upper(),
        range_=str(args.range_ or "1y").strip(),
        interval=str(args.interval or "1d").strip(),
        days_back=max(1, int(args.days_back)),
        limit=max(1, int(args.limit)),
        top=max(1, int(args.top)),
        ticker_filter=ticker_filter,
        doc_class_filter=doc_class_filter,
    )

    out_path = (REPO_ROOT / str(args.output)).resolve() if not Path(str(args.output)).is_absolute() else Path(str(args.output))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(
        f"[announcement-reaction] wrote {out_path} "
        f"(documents={report['documents_scanned']}, reactions={report['reaction_rows']}, "
        f"tickers={report['tickers_scanned']}, price_errors={len(report['ticker_price_errors'])})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
