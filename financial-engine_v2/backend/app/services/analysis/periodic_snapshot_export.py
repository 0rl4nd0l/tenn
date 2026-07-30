"""Export deterministic JSON snapshots from `asx_periodic_financials`.

No LLM calls. Output is suitable for `reports/analysis/{TICKER}/` per roadmap.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.analysis.financial_metrics import build_metrics_summary
from app.services.financial_observations import stable_financial_profile

SCHEMA_VERSION = "financial_snapshot_v0"
_PERIODIC_ROW_FIELDS = (
    "ticker",
    "period_end",
    "period_type",
    "revenue",
    "ebit",
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
    "shares_outstanding",
    "total_equity",
    "interest_expense",
    "period_start",
    "currency",
    "source_document_id",
    "confidence_metrics",
    "metric_provenance",
    "created_at",
    "updated_at",
)
_NUMERIC_FIELDS = {
    "revenue",
    "ebit",
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
    "shares_outstanding",
    "total_equity",
    "interest_expense",
}


def _snapshot_row(row: dict[str, Any]) -> dict[str, Any]:
    shaped = {field: row.get(field) for field in _PERIODIC_ROW_FIELDS}
    for field in _NUMERIC_FIELDS:
        if shaped[field] is not None:
            shaped[field] = Decimal(shaped[field])
    return shaped


def _serialize_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _serialize_periodic_row(row: dict[str, Any]) -> dict[str, Any]:
    """Stable key order + JSON-safe values."""
    return {k: _serialize_cell(row[k]) for k in sorted(row.keys())}


def build_financial_snapshot_v0_from_rows(
    ticker: str,
    raw_rows: list[dict[str, Any]],
    *,
    period_type: str = "A",
    max_periods: int = 5,
) -> dict[str, Any]:
    """
    Core builder: ``raw_rows`` are plain dicts as returned from ORM rows
    (``_row_to_dict``). Deterministic for identical inputs.
    """
    ticker_key = ticker.strip().upper()
    ptype = period_type.strip().upper()

    warnings: list[str] = []
    if not raw_rows:
        warnings.append(f"No financial rows in asx_periodic_financials for {ticker_key}.")

    metrics_summary = build_metrics_summary(
        raw_rows, period_type=ptype, max_periods=max_periods
    )

    matching = [
        r for r in raw_rows if str(r.get("period_type") or "").upper() == ptype
    ]
    matching.sort(key=lambda r: str(r.get("period_end") or ""))
    matching = matching[-max_periods:]
    periodic_rows = [_serialize_periodic_row(r) for r in matching]

    return {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker_key,
        "period_type": ptype,
        "source_table": "asx_periodic_financials",
        "warnings": warnings,
        "metrics_summary": metrics_summary,
        "periodic_rows": periodic_rows,
    }


def build_financial_snapshot_v0(
    ticker: str,
    db: Session,
    *,
    period_type: str = "A",
    max_periods: int = 5,
    fetch_limit: int = 48,
) -> dict[str, Any]:
    """
    Build the v0 financial snapshot dict from canonical periodic rows.

    ``metrics_summary`` matches ``financial_metrics.build_metrics_summary``;
    ``periodic_rows`` lists the same underlying DB rows (filtered to
    ``period_type``), oldest→newest, capped at ``max_periods``.
    """
    ticker_key = ticker.strip().upper()
    raw_rows = [
        _snapshot_row(row)
        for row in stable_financial_profile(db, ticker=ticker_key)[:fetch_limit]
    ]
    return build_financial_snapshot_v0_from_rows(
        ticker_key,
        raw_rows,
        period_type=period_type,
        max_periods=max_periods,
    )


def write_financial_snapshot_v0(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with stable key ordering (recursive)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")


def default_analysis_dir(repo_root: Path | None = None) -> Path:
    """``reports/analysis`` under Tenn repo root (parent of financial-engine_v2)."""
    if repo_root is not None:
        return repo_root / "reports" / "analysis"
    here = Path(__file__).resolve()
    fe_root = here.parents[4]  # .../financial-engine_v2
    tenn_root = fe_root.parent
    return tenn_root / "reports" / "analysis"
