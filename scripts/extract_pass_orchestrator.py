#!/usr/bin/env python3
"""Deterministic pass orchestrator for extraction candidates.

This module standardizes candidate shape, applies canonical promotion gates,
resolves collisions deterministically, and returns canonical/context/quarantine
streams with explicit reasons.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROV = _load_module(ROOT / "scripts" / "provenance_contract.py", "provenance_contract")
FINANCIAL_NORMALIZATION = _load_module(ROOT / "scripts" / "financial_normalization.py", "financial_normalization")
METRIC_ONTOLOGY_MAPPER = _load_module(ROOT / "scripts" / "metric_ontology_mapper.py", "metric_ontology_mapper")
PERIOD_ONTOLOGY_MAPPER = _load_module(ROOT / "scripts" / "period_ontology_mapper.py", "period_ontology_mapper")
FINANCIAL_CONSISTENCY_ENGINE = _load_module(
    ROOT / "scripts" / "financial_consistency_engine.py",
    "financial_consistency_engine",
)


def _candidate_group_key(candidate: Dict[str, object]) -> Tuple[str, str, str]:
    return (
        str(candidate.get("metric_name_canonical", "")).strip().lower(),
        str(candidate.get("period_end", "")).strip(),
        str(candidate.get("scope", "")).strip().lower(),
    )


UNIT_SCALE_HINT_RULES: List[Tuple[re.Pattern[str], float]] = [
    (re.compile(r"(?:\bus\$|\ba\$|\$)\s*[b](?:n)?\b|\bbillion\b|\bbn\b", re.IGNORECASE), 1_000_000_000.0),
    (re.compile(r"(?:\bus\$|\ba\$|\$)\s*[m]\b|\bmillion\b|\bmn\b", re.IGNORECASE), 1_000_000.0),
    (re.compile(r"(?:\bus\$|\ba\$|\$)\s*'?\s*0{3}\b|\$'?000\b|\bthousand\b", re.IGNORECASE), 1_000.0),
]
UNIT_SCALE_BUCKETS: Tuple[float, ...] = (1.0, 1_000.0, 1_000_000.0, 1_000_000_000.0)


def _winner_sort_key(candidate: Dict[str, object]) -> Tuple[float, int, int, str, int]:
    provenance = candidate.get("provenance", {}) if isinstance(candidate.get("provenance", {}), dict) else {}
    return (
        -float(candidate.get("confidence", 0.0) or 0.0),
        int(PROV.pass_priority(str(candidate.get("pass_name", "")))),
        -int(PROV.provenance_depth_score(provenance)),
        str(candidate.get("pdf_path", "")),
        int(candidate.get("page", 0) or 0),
    )


def _bucketize_unit_scale(value: float) -> float | None:
    if value <= 0:
        return None
    best = min(UNIT_SCALE_BUCKETS, key=lambda s: abs(value - s) / s)
    if abs(value - best) / best <= 0.15:
        return float(best)
    return None


def _expected_unit_scale(candidate: Dict[str, object]) -> float | None:
    raw = candidate.get("_raw", {})
    if not isinstance(raw, dict):
        return None
    hint_text = " ".join(
        str(raw.get(key, "")).strip()
        for key in ("table_header_text", "statement_title", "statement_scope_header", "line")
        if str(raw.get(key, "")).strip()
    )
    if not hint_text:
        return None
    for pattern, scale in UNIT_SCALE_HINT_RULES:
        if pattern.search(hint_text):
            return scale
    return None


def _unit_evidence_score(candidate: Dict[str, object]) -> int:
    expected = _expected_unit_scale(candidate)
    applied = _bucketize_unit_scale(float(candidate.get("unit_scale", 0.0) or 0.0))
    if expected is None or applied is None:
        return 0
    if expected == applied:
        return 3
    ratio = max(expected, applied) / min(expected, applied)
    if ratio >= 1_000:
        return -3
    if ratio >= 1_000 / 10:
        return -2
    return -1


def _candidate_fingerprint(candidate: Dict[str, object]) -> Tuple[str, int, str, str, str, str, str, float, str]:
    provenance = candidate.get("provenance", {}) if isinstance(candidate.get("provenance", {}), dict) else {}
    return (
        str(candidate.get("pdf_path", "")),
        int(candidate.get("page", 0) or 0),
        str(candidate.get("pass_name", "")),
        str(candidate.get("metric_name_canonical", "")),
        str(candidate.get("period_end", "")),
        str(candidate.get("scope", "")),
        str(candidate.get("currency", "")),
        float(candidate.get("value", 0.0) or 0.0),
        str(provenance.get("table_id", "")),
    )


def _convert_back_to_row(candidate: Dict[str, object], *, reason: str = "", collision: bool = False) -> Dict[str, object]:
    raw = dict(candidate.get("_raw", {}))
    if not raw:
        raw = {
            "file": str(candidate.get("pdf_path", "")),
            "metric": str(candidate.get("metric_name_canonical", "")),
            "metric_base": str(candidate.get("metric_name_canonical", "")),
            "statement_period_end": str(candidate.get("period_end", "")),
            "statement_scope": str(candidate.get("scope", "")),
            "value": float(candidate.get("value", 0.0) or 0.0),
            "currency": str(candidate.get("currency", "")),
            "page_number": int(candidate.get("page", 0) or 0),
            "table_page": int(candidate.get("page", 0) or 0),
        }
    if str(candidate.get("metric_name_canonical", "")).strip():
        raw["metric"] = str(candidate.get("metric_name_canonical", "")).strip()
        raw["metric_base"] = str(candidate.get("metric_name_canonical", "")).strip()
    raw["statement_period_end"] = str(candidate.get("period_end", "")).strip()
    raw["currency"] = str(candidate.get("currency", "")).strip()
    raw["statement_scope"] = str(candidate.get("scope", "")).strip() or str(raw.get("statement_scope", ""))
    raw["statement_family"] = str(candidate.get("statement_type", "")).strip() or str(raw.get("statement_family", ""))
    raw["orchestrator_pass_name"] = str(candidate.get("pass_name", "")).strip()
    raw["orchestrator_collision"] = 1 if collision else 0
    raw["orchestrator_reason"] = reason
    raw["orchestrator_provenance_depth"] = int(
        PROV.provenance_depth_score(candidate.get("provenance", {}) if isinstance(candidate.get("provenance", {}), dict) else {})
    )
    raw["orchestrator_unit_evidence_score"] = int(_unit_evidence_score(candidate))
    raw["provenance_json"] = json.dumps(candidate.get("provenance", {}), sort_keys=True)
    return raw


def canonical_promotion_gate(
    candidate: Dict[str, object],
    *,
    require_currency: bool = True,
    min_confidence_by_pass: Dict[str, float] | None = None,
) -> Tuple[bool, List[str]]:
    issues: List[str] = []

    metric = str(candidate.get("metric_name_canonical", "")).strip()
    if not metric:
        issues.append("missing_canonical_metric")

    if not str(candidate.get("period_end", "")).strip():
        issues.append("missing_period_end")

    currency = str(candidate.get("currency", "")).strip().upper()
    if require_currency and (not currency or currency == "UNKNOWN"):
        issues.append("unknown_currency")

    pass_name = str(candidate.get("pass_name", "")).strip().lower() or "native_table"
    confidence_floor = float(
        (min_confidence_by_pass or {}).get(pass_name, PROV.pass_confidence_floor(pass_name))
    )
    confidence = float(candidate.get("confidence", 0.0) or 0.0)
    if confidence < confidence_floor:
        issues.append("low_confidence")

    return len(issues) == 0, issues


def normalize_candidates(rows: Sequence[Dict[str, object]], pass_name: str | None = None) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in rows:
        normalized_row = dict(row)
        METRIC_ONTOLOGY_MAPPER.canonicalize_metric_row(normalized_row)
        PERIOD_ONTOLOGY_MAPPER.normalize_period_row(normalized_row)
        FINANCIAL_NORMALIZATION.normalize_metric_rows([normalized_row])
        out.append(PROV.normalize_candidate_row(normalized_row, pass_name=pass_name))
    return out


def select_canonical_candidates(
    rows: Sequence[Dict[str, object]],
    *,
    pass_name: str | None = None,
    require_currency: bool = True,
    min_confidence_by_pass: Dict[str, float] | None = None,
) -> Dict[str, object]:
    normalized = normalize_candidates(rows, pass_name=pass_name)

    canonical_pool: List[Dict[str, object]] = []
    context_rows: List[Dict[str, object]] = []
    quarantined_rows: List[Dict[str, object]] = []

    for cand in normalized:
        ok_contract, contract_issues = PROV.validate_candidate_contract(cand)
        if not ok_contract:
            quarantined_rows.append(_convert_back_to_row(cand, reason="contract_invalid:" + "|".join(contract_issues)))
            continue

        ok_gate, gate_issues = canonical_promotion_gate(
            cand,
            require_currency=require_currency,
            min_confidence_by_pass=min_confidence_by_pass,
        )
        if not ok_gate:
            context_rows.append(_convert_back_to_row(cand, reason="gate_blocked:" + "|".join(gate_issues)))
            continue

        canonical_pool.append(cand)

    grouped: Dict[Tuple[str, str, str], List[Dict[str, object]]] = defaultdict(list)
    for cand in canonical_pool:
        grouped[_candidate_group_key(cand)].append(cand)

    canonical_rows: List[Dict[str, object]] = []
    collision_rows: List[Dict[str, object]] = []

    for key in sorted(grouped.keys()):
        raw_members = list(grouped[key])
        deduped_members: List[Dict[str, object]] = []
        seen_fingerprints = set()
        for member in raw_members:
            fp = _candidate_fingerprint(member)
            if fp in seen_fingerprints:
                context_rows.append(_convert_back_to_row(member, reason="duplicate_equivalent_candidate"))
                continue
            seen_fingerprints.add(fp)
            deduped_members.append(member)

        members = sorted(deduped_members, key=_winner_sort_key)
        if not members:
            continue

        winner = members[0]
        if len(members) == 1:
            canonical_rows.append(_convert_back_to_row(winner))
            continue

        # Collision if top-ranked members are indistinguishable by deterministic sort factors.
        top_score = _winner_sort_key(winner)
        tied = [m for m in members if _winner_sort_key(m) == top_score]
        if len(tied) > 1:
            tie_unit_scores = [_unit_evidence_score(m) for m in tied]
            best_unit_score = max(tie_unit_scores)
            if tie_unit_scores.count(best_unit_score) == 1 and best_unit_score > min(tie_unit_scores):
                winner_idx = tie_unit_scores.index(best_unit_score)
                resolved_winner = tied[winner_idx]
                canonical_rows.append(
                    _convert_back_to_row(
                        resolved_winner,
                        reason="collision_resolved_unit_evidence",
                        collision=True,
                    )
                )
                for idx, item in enumerate(tied):
                    if idx == winner_idx:
                        continue
                    context_rows.append(_convert_back_to_row(item, reason="collision_unit_evidence_rejected"))
                for item in members[len(tied):]:
                    context_rows.append(_convert_back_to_row(item, reason="lower_ranked_candidate"))
                continue

            tied_values = {round(float(m.get("value", 0.0) or 0.0), 6) for m in tied}
            tied_currencies = {str(m.get("currency", "")).strip().upper() for m in tied}
            if len(tied_values) == 1 and len(tied_currencies) == 1:
                canonical_rows.append(_convert_back_to_row(winner, reason="collision_reconciled_equivalent", collision=True))
                for item in tied[1:]:
                    context_rows.append(_convert_back_to_row(item, reason="collision_equivalent_duplicate"))
                for item in members[len(tied):]:
                    context_rows.append(_convert_back_to_row(item, reason="lower_ranked_candidate"))
                continue
            for item in members:
                q = _convert_back_to_row(item, reason="collision_unresolved", collision=True)
                quarantined_rows.append(q)
                collision_rows.append(q)
            continue

        canonical_rows.append(_convert_back_to_row(winner))
        for item in members[1:]:
            context_rows.append(_convert_back_to_row(item, reason="lower_ranked_candidate"))

    stats = {
        "rows_input": int(len(rows)),
        "rows_normalized": int(len(normalized)),
        "rows_canonical": int(len(canonical_rows)),
        "rows_context": int(len(context_rows)),
        "rows_quarantined": int(len(quarantined_rows)),
        "rows_collision_quarantined": int(len(collision_rows)),
    }
    consistency_report = FINANCIAL_CONSISTENCY_ENGINE.evaluate_financial_consistency(canonical_rows)
    stats["consistency_checks_evaluated"] = int(consistency_report.get("checks_evaluated", 0) or 0)
    stats["consistency_checks_failed"] = int(len(consistency_report.get("failed_checks", [])))

    return {
        "canonical_rows": canonical_rows,
        "context_rows": context_rows,
        "quarantined_rows": quarantined_rows,
        "collision_rows": collision_rows,
        "stats": stats,
        "consistency_report": consistency_report,
    }


def _run_cli(pdf: Path, source_kind: str, out_dir: Path) -> int:
    extract_mod = _load_module(ROOT / "scripts" / "extract_financial_metrics.py", "extract_financial_metrics")

    rows, blocks, split = extract_mod.extract_table_metrics(
        pdf,
        strict_metric_rows_only=False,
        source_kind=source_kind,
        review_scope="all",
        include_blocks=True,
    )

    selected = select_canonical_candidates(rows)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "orchestrator_input_rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out_dir / "orchestrator_blocks.json").write_text(json.dumps(blocks, indent=2), encoding="utf-8")
    (out_dir / "orchestrator_scope_split.json").write_text(json.dumps(split, indent=2), encoding="utf-8")
    (out_dir / "orchestrator_canonical_rows.json").write_text(
        json.dumps(selected["canonical_rows"], indent=2), encoding="utf-8"
    )
    (out_dir / "orchestrator_context_rows.json").write_text(
        json.dumps(selected["context_rows"], indent=2), encoding="utf-8"
    )
    (out_dir / "orchestrator_quarantined_rows.json").write_text(
        json.dumps(selected["quarantined_rows"], indent=2), encoding="utf-8"
    )
    (out_dir / "orchestrator_stats.json").write_text(
        json.dumps(selected["stats"], indent=2), encoding="utf-8"
    )

    print(f"Input rows: {len(rows)}")
    print(f"Canonical rows: {selected['stats']['rows_canonical']}")
    print(f"Context rows: {selected['stats']['rows_context']}")
    print(f"Quarantined rows: {selected['stats']['rows_quarantined']}")
    print(f"Output dir: {out_dir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run extraction pass orchestrator on a single PDF.")
    ap.add_argument("--pdf", required=True, help="Path to input PDF.")
    ap.add_argument("--source-kind", default="", help="Optional source kind override.")
    ap.add_argument(
        "--out-dir",
        default="reports/orchestrator_single_doc",
        help="Output directory for orchestrator artifacts.",
    )
    args = ap.parse_args()

    pdf = Path(args.pdf).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")

    source_kind = str(args.source_kind or "").strip()
    if not source_kind:
        extract_mod = _load_module(ROOT / "scripts" / "extract_financial_metrics.py", "extract_financial_metrics")
        source_kind = str(extract_mod.classify_pdf_source_kind(pdf))

    return _run_cli(pdf=pdf, source_kind=source_kind, out_dir=out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
