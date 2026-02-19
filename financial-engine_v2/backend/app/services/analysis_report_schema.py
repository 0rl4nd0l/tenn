from __future__ import annotations

from typing import Any


ALLOWED_SOURCE_TYPES = {"financial_statement", "asx_announcement", "news", "macro"}
ALLOWED_ACTION_LABELS = {"watch", "accumulate", "reduce", "no_action"}
REQUIRED_REPORT_FIELDS = {
    "thesis_summary",
    "bull_case",
    "bear_case",
    "financial_health_score",
    "news_sentiment_score",
    "key_risks",
    "near_term_catalysts",
    "valuation_view",
    "action_label",
    "citations",
}


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_non_empty_str(item) for item in value)


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def validate_evidence_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(bundle, dict):
        return {"ok": False, "errors": ["Evidence bundle must be a JSON object."], "warnings": [], "stats": {}}

    evidence = bundle.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("Evidence bundle must include a non-empty `evidence` list.")
        return {"ok": False, "errors": errors, "warnings": warnings, "stats": {"evidence_count": 0}}

    seen_ids: set[str] = set()
    source_counts: dict[str, int] = {}
    for idx, item in enumerate(evidence):
        prefix = f"evidence[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        evidence_id = item.get("evidence_id")
        if not _is_non_empty_str(evidence_id):
            errors.append(f"{prefix}.evidence_id is required.")
        elif evidence_id in seen_ids:
            errors.append(f"{prefix}.evidence_id must be unique (`{evidence_id}`).")
        else:
            seen_ids.add(str(evidence_id))
        source_type = item.get("source_type")
        if source_type not in ALLOWED_SOURCE_TYPES:
            errors.append(
                f"{prefix}.source_type must be one of {sorted(ALLOWED_SOURCE_TYPES)}."
            )
        else:
            source_counts[source_type] = source_counts.get(source_type, 0) + 1
        if not _is_non_empty_str(item.get("source_id")) and not _is_non_empty_str(item.get("source_url")):
            errors.append(f"{prefix} requires `source_id` or `source_url`.")
        confidence = _to_float(item.get("confidence"))
        if confidence is None:
            errors.append(f"{prefix}.confidence must be numeric in [0, 1].")
        elif confidence < 0 or confidence > 1:
            errors.append(f"{prefix}.confidence must be in [0, 1].")
        if not _is_non_empty_str(item.get("content")):
            errors.append(f"{prefix}.content is required.")

    for required in ("financial_statement", "asx_announcement", "news"):
        if source_counts.get(required, 0) == 0:
            warnings.append(f"Evidence bundle has no `{required}` entries.")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "evidence_count": len(evidence),
            "source_counts": source_counts,
            "evidence_ids": sorted(seen_ids),
        },
    }


def _collect_nontrivial_claims(report: dict[str, Any]) -> list[str]:
    claims: list[str] = []
    for field in ("thesis_summary", "bull_case", "bear_case", "valuation_view"):
        value = report.get(field)
        if _is_non_empty_str(value):
            claims.append(value.strip())
    for field in ("key_risks", "near_term_catalysts"):
        value = report.get(field)
        if isinstance(value, list):
            claims.extend([item.strip() for item in value if _is_non_empty_str(item)])
    return claims


def validate_analysis_report(
    report: dict[str, Any],
    evidence_bundle: dict[str, Any] | None = None,
    min_citation_coverage: float = 0.95,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(report, dict):
        return {"ok": False, "errors": ["Report must be a JSON object."], "warnings": [], "metrics": {}}

    missing = sorted(REQUIRED_REPORT_FIELDS.difference(report.keys()))
    if missing:
        errors.append(f"Missing required report fields: {missing}")

    for field in ("thesis_summary", "bull_case", "bear_case", "valuation_view"):
        if field in report and not _is_non_empty_str(report.get(field)):
            errors.append(f"`{field}` must be a non-empty string.")

    for field in ("key_risks", "near_term_catalysts"):
        if field in report and not _is_str_list(report.get(field)):
            errors.append(f"`{field}` must be a list of non-empty strings.")

    for field in ("financial_health_score", "news_sentiment_score"):
        if field in report:
            score = _to_float(report.get(field))
            if score is None:
                errors.append(f"`{field}` must be numeric in [0, 100].")
            elif score < 0 or score > 100:
                errors.append(f"`{field}` must be in [0, 100].")

    action_label = report.get("action_label")
    if action_label not in ALLOWED_ACTION_LABELS:
        errors.append(f"`action_label` must be one of {sorted(ALLOWED_ACTION_LABELS)}.")

    citations = report.get("citations")
    if not isinstance(citations, list) or not citations:
        errors.append("`citations` must be a non-empty list.")
        citations = []

    cited_claims = 0
    cited_evidence_ids: set[str] = set()
    for idx, citation in enumerate(citations):
        prefix = f"citations[{idx}]"
        if not isinstance(citation, dict):
            errors.append(f"{prefix} must be an object.")
            continue
        if not _is_non_empty_str(citation.get("claim")):
            errors.append(f"{prefix}.claim is required.")
        else:
            cited_claims += 1
        evidence_ids = citation.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids or not all(_is_non_empty_str(eid) for eid in evidence_ids):
            errors.append(f"{prefix}.evidence_ids must be a non-empty list of strings.")
        else:
            cited_evidence_ids.update(str(eid) for eid in evidence_ids)

    evidence_result: dict[str, Any] | None = None
    if evidence_bundle is not None:
        evidence_result = validate_evidence_bundle(evidence_bundle)
        if not evidence_result["ok"]:
            errors.append("Evidence bundle is invalid.")
            errors.extend([f"evidence: {msg}" for msg in evidence_result["errors"]])
        evidence_ids = set(evidence_result.get("stats", {}).get("evidence_ids", []))
        unknown_ids = sorted(cited_evidence_ids.difference(evidence_ids))
        if unknown_ids:
            errors.append(f"Citations reference unknown evidence_ids: {unknown_ids}")
        warnings.extend(evidence_result.get("warnings", []))

    nontrivial_claim_count = len(_collect_nontrivial_claims(report))
    coverage = 1.0 if nontrivial_claim_count == 0 else (cited_claims / nontrivial_claim_count)
    if coverage < min_citation_coverage:
        errors.append(
            f"Citation coverage gate failed: {coverage:.3f} < {min_citation_coverage:.3f}"
        )

    health = _to_float(report.get("financial_health_score")) or 0.0
    sentiment = _to_float(report.get("news_sentiment_score")) or 0.0
    if action_label == "accumulate" and health < 40:
        warnings.append("Action label `accumulate` with low financial_health_score (<40).")
    if action_label == "reduce" and health > 70 and sentiment > 70:
        warnings.append("Action label `reduce` with high health/sentiment scores (>70).")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "nontrivial_claim_count": nontrivial_claim_count,
            "cited_claim_count": cited_claims,
            "citation_coverage": coverage,
            "min_citation_coverage": min_citation_coverage,
        },
        "evidence_validation": evidence_result,
    }
