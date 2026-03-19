#!/usr/bin/env python3
"""Bootstrap gold template files from canonical extraction output."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

DOC_ID_SUFFIX_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", re.IGNORECASE)
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")

CORE_METRICS = [
    "revenue",
    "ebitda",
    "net_income",
    "eps",
    "operating_cash_flow",
    "capital_expenditure",
    "free_cash_flow",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "net_debt",
]


def _doc_id_from_file(file_path: str) -> str:
    stem = Path(str(file_path or "")).stem
    m = DOC_ID_SUFFIX_RE.search(stem)
    if m:
        return str(m.group(1)).lower()
    return stem


def _ticker_from_file(file_path: str) -> str:
    parts = Path(str(file_path or "")).parts
    if "docs" in parts:
        idx = parts.index("docs")
        if idx + 1 < len(parts):
            return str(parts[idx + 1]).upper()
    return ""


def _infer_ticker(file_path: str, tickers_set: set[str]) -> str:
    ticker = _ticker_from_file(file_path)
    if ticker:
        return ticker

    parts_upper = {p.upper() for p in Path(str(file_path or "")).parts}
    for t in sorted(tickers_set):
        if t in parts_upper:
            return t

    # Expansion batches typically run one ticker at a time with /reports/.../pdf_subset paths.
    if len(tickers_set) == 1:
        return next(iter(tickers_set))
    return ""


def _date_from_file(file_path: str) -> str:
    stem = Path(str(file_path or "")).stem
    m = DATE_PREFIX_RE.search(stem)
    return str(m.group(1)) if m else "0000-00-00"


def _norm_metric(value: str) -> str:
    m = str(value or "").strip().lower()
    return {"npat": "net_income", "capex": "capital_expenditure"}.get(m, m)


def _norm_scope(value: str) -> str:
    s = str(value or "").strip().lower()
    return {"consolidated_statement": "group", "consolidated": "group"}.get(s, s or "group")


def bootstrap_templates(
    *,
    canonical_csv: Path,
    out_dir: Path,
    tickers: List[str],
    docs_per_ticker: int,
    overwrite: bool,
) -> Dict[str, object]:
    tickers_set = {t.strip().upper() for t in tickers if t.strip()}
    by_ticker_file: Dict[str, Dict[str, List[Dict[str, str]]]] = defaultdict(lambda: defaultdict(list))

    with canonical_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            file_path = str(row.get("file", "")).strip()
            if not file_path:
                continue
            ticker = _infer_ticker(file_path, tickers_set)
            if tickers_set and ticker not in tickers_set:
                continue
            by_ticker_file[ticker][file_path].append(row)

    created = 0
    skipped = 0
    outputs: List[str] = []

    for ticker in sorted(by_ticker_file.keys()):
        files = sorted(by_ticker_file[ticker].keys(), key=_date_from_file, reverse=True)
        for file_path in files[: int(max(1, docs_per_ticker))]:
            rows = by_ticker_file[ticker][file_path]
            doc_id = _doc_id_from_file(file_path)
            fields: List[Dict[str, object]] = []
            seen = set()
            for row in rows:
                metric = _norm_metric(str(row.get("metric_base", row.get("metric", ""))))
                if metric not in CORE_METRICS:
                    continue
                period_end = str(row.get("statement_period_end", row.get("period_end", ""))).strip()
                if not period_end:
                    continue
                key = (metric, period_end, _norm_scope(str(row.get("statement_scope", ""))))
                if key in seen:
                    continue
                seen.add(key)
                fields.append(
                    {
                        "metric": metric,
                        "period_end": period_end,
                        "period_type": str(row.get("statement_period", row.get("period", ""))).strip() or "UNSPECIFIED",
                        "value": str(row.get("value", "")).strip() or "",
                        "unit_scale": 1,
                        "currency": str(row.get("currency", "")).strip() or "UNKNOWN",
                        "scope": _norm_scope(str(row.get("statement_scope", ""))),
                        "statement_type": str(row.get("statement_family", "")).strip(),
                        "source_hint": {
                            "file": file_path,
                            "page": str(row.get("page_number", row.get("table_page", ""))).strip(),
                            "table_id": str(row.get("table_id", "")).strip(),
                        },
                    }
                )

            template = {
                "doc_id": doc_id,
                "ticker": ticker,
                "pdf_sha256": "",
                "published_at": _date_from_file(file_path),
                "fields": fields,
            }

            target = out_dir / ticker / f"{doc_id}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and not overwrite:
                skipped += 1
                continue
            target.write_text(json.dumps(template, indent=2), encoding="utf-8")
            created += 1
            outputs.append(str(target))

    return {
        "created": int(created),
        "skipped": int(skipped),
        "outputs": outputs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Bootstrap gold templates from canonical CSV.")
    ap.add_argument("--canonical-csv", required=True)
    ap.add_argument("--out-dir", default="gold")
    ap.add_argument("--tickers", default="BHP,CBA,RIO")
    ap.add_argument("--docs-per-ticker", type=int, default=12)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    result = bootstrap_templates(
        canonical_csv=Path(args.canonical_csv).expanduser().resolve(),
        out_dir=Path(args.out_dir).expanduser().resolve(),
        tickers=[t for t in str(args.tickers).split(",")],
        docs_per_ticker=int(max(1, args.docs_per_ticker)),
        overwrite=bool(args.overwrite),
    )

    print(f"Templates created: {result['created']}")
    print(f"Templates skipped: {result['skipped']}")
    if result["outputs"]:
        print(f"First output: {result['outputs'][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
