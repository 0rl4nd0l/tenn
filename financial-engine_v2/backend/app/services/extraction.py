from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Mapping

from dateutil import parser as dtparser

EXTRACTOR_VERSION = "ollama_json_v2"

METRIC_FIELDS = (
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
)

EXTRACTION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "period_type",
        "period_end",
        "metrics",
        "confidence_metrics",
        "risk_summary",
        "risk_bullets",
        "guidance_summary",
        "material_changes",
        "confidence_narrative",
    ],
    "properties": {
        "period_type": {"type": ["string", "null"], "enum": ["Q", "H", "A", None]},
        "period_end": {"type": ["string", "null"]},
        "metrics": {
            "type": "object",
            "additionalProperties": False,
            "required": list(METRIC_FIELDS),
            "properties": {field: {"type": ["number", "null"]} for field in METRIC_FIELDS},
        },
        "confidence_metrics": {"type": ["number", "null"]},
        "risk_summary": {"type": ["string", "null"]},
        "risk_bullets": {"type": ["array", "null"], "items": {"type": "string"}},
        "guidance_summary": {"type": ["string", "null"]},
        "material_changes": {"type": ["string", "null"]},
        "confidence_narrative": {"type": ["number", "null"]},
    },
}

_PERIOD_TYPE_ALIASES = {
    "Q": {"q", "quarter", "quarterly", "qtr", "q1", "q2", "q3", "q4"},
    "H": {"h", "half", "half-year", "half year", "halfyear", "h1", "h2", "interim"},
    "A": {"a", "annual", "fy", "full year", "yearly"},
}

_METRIC_ALIASES = {
    "revenue": {"revenue", "sales", "total_revenue"},
    "ebit": {"ebit", "operating_profit", "earnings_before_interest_and_tax"},
    "np_attributable": {
        "np_attributable",
        "npat",
        "net_income",
        "net_profit",
        "profit_after_tax",
        "underlying_profit",
    },
    "operating_cf": {"operating_cf", "operating_cash_flow", "net_operational_cash_flow", "cash_flow"},
    "investing_cf": {"investing_cf", "investing_cash_flow", "cash_flow_from_investing"},
    "financing_cf": {"financing_cf", "financing_cash_flow", "cash_flow_from_financing"},
    "capex": {"capex", "capital_expenditure"},
    "cash_end": {"cash_end", "ending_cash", "cash_balance", "cash_and_cash_equivalents"},
    "net_debt": {"net_debt"},
    "shares_outstanding": {"shares_outstanding", "shares", "shares_on_issue", "weighted_average_shares"},
}

_PERIOD_END_KEY_HINTS = {
    "period_end",
    "period_end_date",
    "period_ending",
    "year_end",
    "date",
    "reporting_period_end",
}


def build_prompt(text: str) -> str:
    clipped = (text or "")[:16000]
    return f"""You are a financial filing extraction engine for ASX periodic reports.
Return ONLY one JSON object matching this schema exactly (no extra keys):
{{
  "period_type": "Q|H|A|null",
  "period_end": "YYYY-MM-DD|null",
  "metrics": {{
    "revenue": "number|null",
    "ebit": "number|null",
    "np_attributable": "number|null",
    "operating_cf": "number|null",
    "investing_cf": "number|null",
    "financing_cf": "number|null",
    "capex": "number|null",
    "cash_end": "number|null",
    "net_debt": "number|null",
    "shares_outstanding": "number|null"
  }},
  "confidence_metrics": "0..1|null",
  "risk_summary": "string|null",
  "risk_bullets": "array<string>|null",
  "guidance_summary": "string|null",
  "material_changes": "string|null",
  "confidence_narrative": "0..1|null"
}}

Rules:
- Use only keys listed above.
- For unknown values, use null.
- "period_end" is the reporting period end date, not publication date.
- Use numeric values only for metrics (no units, no commas, no currency symbols).
- Prefer extracting from summary financial tables and period headers near the beginning of the filing.
- If document is not a periodic financial report, set period_type/period_end/metrics to null values.

Document text:
{clipped}"""


def parse_period_end(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return dtparser.parse(s).date()
    except Exception:
        return None


def _normalize_key(key: Any) -> str:
    text = str(key or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _coerce_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"none", "null", "na", "n/a", "nan", "unknown"}:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except Exception:
        return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_period_type(value: Any) -> str | None:
    if value is None:
        return None
    token = _normalize_key(value)
    if not token:
        return None
    if token in {"q", "h", "a"}:
        return token.upper()
    for canonical, aliases in _PERIOD_TYPE_ALIASES.items():
        if token in {_normalize_key(a) for a in aliases}:
            return canonical
    return None


def _iter_kv(obj: Any):
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            yield key, value
            yield from _iter_kv(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_kv(item)


def _extract_metrics(raw: Mapping[str, Any]) -> dict[str, float | None]:
    out = {field: None for field in METRIC_FIELDS}
    metrics_node = raw.get("metrics")
    if isinstance(metrics_node, Mapping):
        for field in METRIC_FIELDS:
            out[field] = _coerce_float(metrics_node.get(field))
    alias_lookup = {alias: field for field, aliases in _METRIC_ALIASES.items() for alias in aliases}
    for key, value in _iter_kv(raw):
        norm_key = _normalize_key(key)
        field = alias_lookup.get(norm_key)
        if not field or out[field] is not None:
            continue
        numeric = _coerce_float(value)
        if numeric is not None:
            out[field] = numeric
    return out


def _extract_period_end(raw: Mapping[str, Any]) -> date | None:
    direct = parse_period_end(_coerce_text(raw.get("period_end")))
    if direct:
        return direct
    for key, value in _iter_kv(raw):
        if _normalize_key(key) not in _PERIOD_END_KEY_HINTS:
            continue
        parsed = parse_period_end(_coerce_text(value))
        if parsed:
            return parsed
    return None


def _infer_period_type(doc_class: str, doc_subtype: str, title: str) -> str | None:
    subtype = _normalize_key(doc_subtype)
    dclass = _normalize_key(doc_class)
    t = str(title or "").lower()
    if subtype == "4c":
        return "Q"
    if subtype == "4d":
        return "H"
    if subtype == "4e":
        return "A"
    if dclass == "half_year" or "half year" in t or "half-year" in t:
        return "H"
    if dclass == "annual" or "annual report" in t:
        return "A"
    if dclass == "quarterly" or "quarterly activities report" in t:
        return "Q"
    return None


def _infer_period_end_from_published(period_type: str | None, published_at: datetime | None) -> date | None:
    if period_type not in {"Q", "H", "A"} or not isinstance(published_at, datetime):
        return None
    d = published_at.date()
    if period_type == "Q":
        quarter_ends = [(3, 31), (6, 30), (9, 30), (12, 31)]
    elif period_type == "H":
        quarter_ends = [(6, 30), (12, 31)]
    else:
        quarter_ends = [(6, 30), (12, 31)]
    candidates: list[date] = []
    for year in (d.year - 1, d.year):
        for month, day in quarter_ends:
            try:
                candidate = date(year, month, day)
            except ValueError:
                continue
            if candidate <= d:
                candidates.append(candidate)
    return max(candidates) if candidates else None


def _period_end_is_plausible(period_end: date | None, published_at: datetime | None) -> bool:
    if period_end is None:
        return False
    if not isinstance(published_at, datetime):
        return True
    pub = published_at.date()
    if period_end > pub:
        return False
    return (pub - period_end).days <= 550


def normalize_extraction_payload(
    raw: Mapping[str, Any] | None,
    *,
    doc_title: str = "",
    doc_class: str = "",
    doc_subtype: str = "",
    published_at: datetime | None = None,
) -> dict[str, Any]:
    payload = dict(raw or {})
    period_type = _normalize_period_type(payload.get("period_type")) or _infer_period_type(
        doc_class, doc_subtype, doc_title
    )
    period_end = _extract_period_end(payload)
    if period_end and not _period_end_is_plausible(period_end, published_at):
        period_end = None
    if period_end is None:
        period_end = _infer_period_end_from_published(period_type, published_at)
    normalized: dict[str, Any] = {
        "period_type": period_type,
        "period_end": period_end.isoformat() if period_end else None,
        "metrics": _extract_metrics(payload),
        "confidence_metrics": _coerce_float(payload.get("confidence_metrics")),
        "risk_summary": _coerce_text(payload.get("risk_summary")),
        "risk_bullets": payload.get("risk_bullets") if isinstance(payload.get("risk_bullets"), list) else None,
        "guidance_summary": _coerce_text(payload.get("guidance_summary")),
        "material_changes": _coerce_text(payload.get("material_changes")),
        "confidence_narrative": _coerce_float(payload.get("confidence_narrative")),
    }
    return normalized


def validate_extraction_payload(
    payload: Mapping[str, Any],
    *,
    published_at: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    if payload.get("period_type") not in {"Q", "H", "A"}:
        errors.append("missing_or_invalid_period_type")
    period_end = parse_period_end(_coerce_text(payload.get("period_end")))
    if period_end is None:
        errors.append("missing_or_invalid_period_end")
    elif not _period_end_is_plausible(period_end, published_at):
        errors.append("implausible_period_end")
    metrics = payload.get("metrics")
    if not isinstance(metrics, Mapping):
        errors.append("missing_metrics_object")
    else:
        has_any_metric = any(_coerce_float(metrics.get(field)) is not None for field in METRIC_FIELDS)
        if not has_any_metric:
            errors.append("no_metric_values_extracted")
    return errors
