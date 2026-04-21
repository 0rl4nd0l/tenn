#!/usr/bin/env python3
"""Generate a hand-reasoned validation set for metric_ontology_bridge.

Eval-only. Not imported by any runtime code. Writes a small JSONL fixture
with rows sampled from the exhaustive real-gold artifact and annotated
with the expected ontology-bridge projection.

The labelling rules here are intentionally written in a case-statement style
distinct from the bridge's table-driven runtime logic. That makes the
validation set a genuine independent gold for the bridge to validate against,
rather than a tautological restatement of the bridge's own rules.

Run:
    python3 scripts/eval/generate_ontology_bridge_validation.py

Output:
    financial-engine_v2/backend/tests/fixtures/metric_ontology_bridge/validation.jsonl
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "docs/extraction_gold_real_exhaustive_run/all_exhaustive_datapoints.jsonl"
OUT_DIR = REPO_ROOT / "financial-engine_v2/backend/tests/fixtures/metric_ontology_bridge"
OUT_FILE = OUT_DIR / "validation.jsonl"


@dataclass(frozen=True)
class Expected:
    canonical_family: str | None
    unit_type: str
    mapping_confidence: str
    auto_collapse_safe: bool
    note: str = ""


def _load_rows() -> list[dict]:
    with SOURCE.open(encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def _take(
    rows: Iterable[dict],
    pred: Callable[[dict], bool],
    limit: int,
    seen: set[str],
) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        if len(out) >= limit:
            break
        if row["datapoint_id"] in seen:
            continue
        if not pred(row):
            continue
        seen.add(row["datapoint_id"])
        out.append(row)
    return out


def _label_lower(row: dict) -> str:
    return (row.get("row_label") or "").strip().lower()


def _context_lower(row: dict) -> str:
    return (row.get("context_text") or "").strip().lower()


def _raw_value(row: dict) -> str:
    return (row.get("raw_value") or "").strip()


# ---------------------------------------------------------------------------
# Case-by-case labelling. Each builder returns (row, Expected).
# The reasoning below is deliberately verbose so the validation set doubles
# as an explanation for why each expected label is what it is.
# ---------------------------------------------------------------------------


def _revenue_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    # Revenue rows where row_label is unambiguously "Revenue" or a close synonym
    # in a top-line reporting context. Extractor targets `revenue` directly.
    sel = _take(
        rows,
        lambda r: _label_lower(r) in {"revenue", "total revenue", "sales revenue", "sales"}
        and r.get("unit_type") == "currency"
        and r.get("value_status") == "parsed",
        limit=18,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                canonical_family="revenue",
                unit_type="currency",
                mapping_confidence="strong",
                auto_collapse_safe=True,
                note="top-line revenue row with currency value",
            ),
        )
        for r in sel
    ]


def _ebit_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    # Plain "EBIT" / "Operating profit" → canonical family ebit.
    # "Underlying EBIT" or "Statutory EBIT" → canonical family still ebit but
    # auto_collapse_safe=False because the qualifier carries accounting-method
    # semantics that must not be silently dropped.
    plain = _take(
        rows,
        lambda r: _label_lower(r) in {"ebit", "operating profit"}
        and r.get("unit_type") == "currency",
        limit=6,
        seen=seen,
    )
    qualified = _take(
        rows,
        lambda r: _label_lower(r) in {"underlying ebit", "statutory ebit"}
        and r.get("unit_type") == "currency",
        limit=6,
        seen=seen,
    )
    out: list[tuple[dict, Expected]] = []
    out.extend(
        (r, Expected("ebit", "currency", "strong", True, "plain EBIT row"))
        for r in plain
    )
    out.extend(
        (
            r,
            Expected(
                "ebit",
                "currency",
                "medium",
                False,
                "qualified EBIT variant — do not auto-collapse",
            ),
        )
        for r in qualified
    )
    return out


def _ebitda_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    # EBITDA is NOT one of the extractor's 10 targets. It's a known canonical
    # family in the broader ontology mapper, so it becomes supplemental.
    sel = _take(
        rows,
        lambda r: _label_lower(r) in {"ebitda", "underlying ebitda", "statutory ebitda"}
        and r.get("unit_type") == "currency",
        limit=8,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                canonical_family="ebitda",
                unit_type="currency",
                mapping_confidence="supplemental",
                auto_collapse_safe=False,
                note="EBITDA is a known family but outside extractor target set",
            ),
        )
        for r in sel
    ]


def _operating_cf_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    sel = _take(
        rows,
        lambda r: _label_lower(r)
        in {
            "net cash from operating activities",
            "net cash generated from operating activities",
            "cash flow from operating activities",
            "net cash from operations",
            "net cash inflow from operating activities",
        }
        and r.get("unit_type") == "currency",
        limit=10,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                canonical_family="operating_cf",
                unit_type="currency",
                mapping_confidence="strong",
                auto_collapse_safe=True,
                note="operating cash flow header",
            ),
        )
        for r in sel
    ]


def _investing_cf_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    sel = _take(
        rows,
        lambda r: _label_lower(r)
        in {
            "net cash used in investing activities",
            "net cash from investing activities",
            "cash flow from investing activities",
            "net cash outflow from investing activities",
        }
        and r.get("unit_type") == "currency",
        limit=6,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                "investing_cf",
                "currency",
                "strong",
                True,
                "investing cash flow header",
            ),
        )
        for r in sel
    ]


def _financing_cf_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    sel = _take(
        rows,
        lambda r: _label_lower(r)
        in {
            "net cash used in financing activities",
            "net cash from financing activities",
            "cash flow from financing activities",
            "net cash outflow from financing activities",
        }
        and r.get("unit_type") == "currency",
        limit=6,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                "financing_cf",
                "currency",
                "strong",
                True,
                "financing cash flow header",
            ),
        )
        for r in sel
    ]


def _capex_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    sel = _take(
        rows,
        lambda r: _label_lower(r)
        in {
            "capex",
            "capital expenditure",
            "purchase of property, plant and equipment",
            "payments for property, plant and equipment",
            "additions to property, plant and equipment",
        }
        and r.get("unit_type") == "currency",
        limit=8,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                "capex",
                "currency",
                "strong",
                True,
                "capital expenditure line",
            ),
        )
        for r in sel
    ]


def _cash_end_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    sel = _take(
        rows,
        lambda r: _label_lower(r)
        in {
            "cash and cash equivalents at end of period",
            "cash and cash equivalents at end of financial year",
            "cash and cash equivalents at end of the period",
            "cash and cash equivalents at the end of the period",
            "cash and cash equivalents at end of half-year",
            "cash and cash equivalents at end of the year",
        }
        and r.get("unit_type") == "currency",
        limit=6,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                "cash_end",
                "currency",
                "strong",
                True,
                "period-end cash balance",
            ),
        )
        for r in sel
    ]


def _net_debt_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    # Careful here:
    # 1. "Net debt" with currency value → strong, auto-collapse safe (assuming
    #    period-end semantics; period-start/period-end is a separate disambiguation
    #    that we surface by NOT auto-collapsing the "at the beginning/end" variants).
    # 2. "Net debt at the beginning of the period" / "... end of the period" →
    #    still net_debt family but auto_collapse_safe=False (period sub-selection).
    # 3. "Net debt" with unit_type=percent_or_ratio (observed in BHP movement tables)
    #    → bridge should REJECT this as a net_debt match because the numeric is a
    #    percentage change, not a balance. Expected: unsupported + percentage.
    plain = _take(
        rows,
        lambda r: _label_lower(r) == "net debt"
        and r.get("unit_type") == "currency"
        and "%" not in _raw_value(r),
        limit=6,
        seen=seen,
    )
    period_disambig = _take(
        rows,
        lambda r: _label_lower(r)
        in {
            "net debt at the beginning of the period",
            "net debt at the end of the period",
            "net debt at the beginning of the financial year",
            "net debt at the end of the financial year",
        }
        and r.get("unit_type") == "currency",
        limit=4,
        seen=seen,
    )
    percent_misclass = _take(
        rows,
        lambda r: _label_lower(r) == "net debt"
        and r.get("unit_type") == "percent_or_ratio",
        limit=3,
        seen=seen,
    )
    out: list[tuple[dict, Expected]] = []
    out.extend(
        (r, Expected("net_debt", "currency", "strong", True, "plain net debt balance"))
        for r in plain
    )
    out.extend(
        (
            r,
            Expected(
                "net_debt",
                "currency",
                "medium",
                False,
                "period-disambiguated net debt — requires matcher to pick exact period",
            ),
        )
        for r in period_disambig
    )
    out.extend(
        (
            r,
            Expected(
                None,
                "percentage",
                "unsupported",
                False,
                "net debt row in a percent-change column — not a balance",
            ),
        )
        for r in percent_misclass
    )
    return out


def _shares_outstanding_rows(
    rows: list[dict], seen: set[str]
) -> list[tuple[dict, Expected]]:
    # Share-count rows. Raw values can be in the hundreds of millions;
    # generator often labels these as currency, which is WRONG. Bridge must
    # reclassify unit_type to `count` based on row_label semantics.
    sel = _take(
        rows,
        lambda r: "ordinary shares" in _label_lower(r)
        and ("issued" in _label_lower(r) or "on issue" in _label_lower(r))
        and r.get("value_status") == "parsed",
        limit=6,
        seen=seen,
    )
    # Also grab any row where label matches a known share-count pattern
    extra = _take(
        rows,
        lambda r: _label_lower(r) in {"number of ordinary shares on issue"}
        and r.get("value_status") == "parsed",
        limit=3,
        seen=seen,
    )
    out: list[tuple[dict, Expected]] = []
    out.extend(
        (
            r,
            Expected(
                "shares_outstanding",
                "count",
                "strong",
                True,
                "share-count row; bridge must override incoming unit_type=currency",
            ),
        )
        for r in sel + extra
    )
    return out


def _per_share_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    # EPS / DPS in cents. These are per-share metrics; extractor does not
    # target them directly. Mark as supplemental.
    sel = _take(
        rows,
        lambda r: (
            "earnings per ordinary share" in _label_lower(r)
            or "earnings per share" in _label_lower(r)
            or _label_lower(r).startswith("basic eps")
            or _label_lower(r).startswith("diluted eps")
        )
        and r.get("unit_type") == "per_share",
        limit=6,
        seen=seen,
    )
    div = _take(
        rows,
        lambda r: "dividend per share" in _label_lower(r)
        or "dividend per ordinary share" in _label_lower(r),
        limit=3,
        seen=seen,
    )
    out: list[tuple[dict, Expected]] = []
    out.extend(
        (r, Expected(None, "per_share", "supplemental", False, "EPS in cents"))
        for r in sel
    )
    out.extend(
        (r, Expected(None, "per_share", "supplemental", False, "DPS per share"))
        for r in div
    )
    return out


def _percentage_misclass_rows(
    rows: list[dict], seen: set[str]
) -> list[tuple[dict, Expected]]:
    # raw_value ends with '%' but generator labelled as currency. Bridge MUST
    # reclassify to percentage and never auto-collapse into a canonical family.
    sel = _take(
        rows,
        lambda r: _raw_value(r).endswith("%") and r.get("unit_type") == "currency",
        limit=8,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                canonical_family=None,
                unit_type="percentage",
                mapping_confidence="unsupported",
                auto_collapse_safe=False,
                note="raw_value is percent-string — override incoming unit_type=currency",
            ),
        )
        for r in sel
    ]


def _real_percentage_rows(
    rows: list[dict], seen: set[str]
) -> list[tuple[dict, Expected]]:
    # Correctly-labelled percentages. Still unsupported as a canonical target.
    sel = _take(
        rows,
        lambda r: r.get("unit_type") == "percent_or_ratio"
        and _raw_value(r).endswith("%"),
        limit=6,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                None,
                "percentage",
                "unsupported",
                False,
                "percentage value; not a canonical balance",
            ),
        )
        for r in sel
    ]


def _supplemental_balance_rows(
    rows: list[dict], seen: set[str]
) -> list[tuple[dict, Expected]]:
    # Known non-extractor canonical families from scripts/metric_ontology_mapper.py
    mapping = {
        "total assets": "total_assets",
        "total equity": "total_equity",
        "total liabilities": "total_liabilities",
        "shareholders equity": "total_equity",
    }
    out: list[tuple[dict, Expected]] = []
    for label, family in mapping.items():
        sel = _take(
            rows,
            lambda r, _label=label: _label_lower(r) == _label
            and r.get("unit_type") == "currency",
            limit=3,
            seen=seen,
        )
        out.extend(
            (
                r,
                Expected(
                    family,
                    "currency",
                    "supplemental",
                    False,
                    f"{family} — known family, not an extractor target",
                ),
            )
            for r in sel
        )
    return out


def _unsupported_rows(rows: list[dict], seen: set[str]) -> list[tuple[dict, Expected]]:
    # Labels that carry no mappable canonical family. The bridge must refuse
    # to guess, even when unit_type is currency.
    labels = {
        "customers",
        "australia",
        "other",
        "g/tau subtotal",
        "ppmmo subtotal",
        "rod subtotal",
        "8 nov 24",
        "fy2024",
        "fy2025",
    }
    sel = _take(
        rows,
        lambda r: _label_lower(r) in labels,
        limit=12,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                None,
                "currency" if r.get("unit_type") == "currency" else "unknown",
                "unsupported",
                False,
                "no canonical family derivable from row_label",
            ),
        )
        for r in sel
    ]


def _ambiguous_total_rows(
    rows: list[dict], seen: set[str]
) -> list[tuple[dict, Expected]]:
    # "Total" alone is never enough. Bridge may use context_text leading section
    # to infer a weak family, but should not auto-collapse.
    sel = _take(
        rows,
        lambda r: _label_lower(r) == "total" and r.get("unit_type") == "currency",
        limit=8,
        seen=seen,
    )
    out: list[tuple[dict, Expected]] = []
    for r in sel:
        ctx = _context_lower(r)
        if "exceptional" in ctx:
            fam = None
            conf = "unsupported"
            note = "Total under 'Exceptional items' — not a canonical extractor target"
        elif "revenue" in ctx:
            fam = "revenue"
            conf = "weak"
            note = "Total inferred as revenue from context leading section"
        else:
            fam = None
            conf = "unsupported"
            note = "Total row without usable canonical context"
        out.append(
            (
                r,
                Expected(fam, "currency", conf, False, note),
            )
        )
    return out


def _narrative_count_rows(
    rows: list[dict], seen: set[str]
) -> list[tuple[dict, Expected]]:
    # Director holdings (e.g., "Gary Goldberg | 24,000") — share counts in a
    # narrative / governance context. unit_type should be count, family None.
    sel = _take(
        rows,
        lambda r: r.get("unit_type") == "shares",
        limit=4,
        seen=seen,
    )
    return [
        (
            r,
            Expected(
                None,
                "count",
                "unsupported",
                False,
                "director / beneficial holdings count",
            ),
        )
        for r in sel
    ]


BUILDERS: list[Callable[[list[dict], set[str]], list[tuple[dict, Expected]]]] = [
    _revenue_rows,
    _ebit_rows,
    _ebitda_rows,
    _operating_cf_rows,
    _investing_cf_rows,
    _financing_cf_rows,
    _capex_rows,
    _cash_end_rows,
    _net_debt_rows,
    _shares_outstanding_rows,
    _per_share_rows,
    _percentage_misclass_rows,
    _real_percentage_rows,
    _supplemental_balance_rows,
    _unsupported_rows,
    _ambiguous_total_rows,
    _narrative_count_rows,
]


def build() -> list[dict]:
    rows = _load_rows()
    seen: set[str] = set()
    records: list[dict] = []
    for builder in BUILDERS:
        for row, expected in builder(rows, seen):
            records.append(
                {
                    "datapoint_id": row["datapoint_id"],
                    "document_id": row["document_id"],
                    "raw_value": row.get("raw_value"),
                    "parsed_numeric": row.get("parsed_numeric"),
                    "normalized_value": row.get("normalized_value"),
                    "row_label": row.get("row_label"),
                    "context_text": row.get("context_text"),
                    "column_hint": row.get("column_hint"),
                    "unit_type_src": row.get("unit_type"),
                    "raw_scale_src": row.get("raw_scale"),
                    "currency_src": row.get("currency"),
                    "expected": {
                        "canonical_family": expected.canonical_family,
                        "unit_type": expected.unit_type,
                        "mapping_confidence": expected.mapping_confidence,
                        "auto_collapse_safe": expected.auto_collapse_safe,
                        "note": expected.note,
                    },
                }
            )
    return records


def main() -> None:
    records = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records to {OUT_FILE}")
    # Summary
    from collections import Counter

    fam = Counter(r["expected"]["canonical_family"] for r in records)
    conf = Counter(r["expected"]["mapping_confidence"] for r in records)
    unit = Counter(r["expected"]["unit_type"] for r in records)
    print("families:", fam.most_common())
    print("confidence:", conf.most_common())
    print("unit_types:", unit.most_common())


if __name__ == "__main__":
    main()
