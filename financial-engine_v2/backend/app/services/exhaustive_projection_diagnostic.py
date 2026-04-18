"""Read-only diagnostic scorecard for exhaustive ontology projections.

This module stays strictly on the evaluation sidecar:
    - reads the existing exhaustive corpus artifact
    - projects rows through metric_ontology_bridge
    - emits provisional diagnostic summaries only

It does NOT:
    - implement the exhaustive matcher
    - compare tuple-level facts
    - compute precision / recall / accuracy
    - alter canonical scoring or runtime behavior
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.services import metric_ontology_bridge as bridge
from app.services.extraction_gold_eval import REAL_GOLD_METRIC_ALIASES
from app.services.metric_ontology_bridge import (
    EXTRACTOR_TARGET_FAMILIES,
    MappingConfidence,
    OntologyProjection,
    project,
)


PROVISIONAL_LABEL = "PROVISIONAL DIAGNOSTIC ONLY"
CANONICAL_GATE_LABEL = "Canonical real-gold scoring remains the only release gate."
NON_GOALS = (
    "No tuple-level matcher is implemented.",
    "No precision/recall or production-accuracy metric is computed.",
    "No canonical truth or extractor behavior is replaced.",
)


def load_exhaustive_datapoints(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            record = json.loads(raw)
            if isinstance(record, dict):
                rows.append(record)
    return rows


def load_exhaustive_audit_summary(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected dict audit summary at {path}")
    return data


def load_canonical_family_presence(
    fixtures_dir: str | Path,
) -> dict[str, tuple[str, ...]]:
    output: dict[str, tuple[str, ...]] = {}
    for path in sorted(Path(fixtures_dir).glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        document_id = str(payload.get("document_id") or path.stem)
        raw_metrics = payload.get("metrics") or {}
        families: list[str] = []
        if isinstance(raw_metrics, dict):
            for metric, value in raw_metrics.items():
                if value is None:
                    continue
                family = REAL_GOLD_METRIC_ALIASES.get(str(metric), str(metric))
                families.append(family)
        output[document_id] = tuple(sorted(set(families)))
    return output


def build_exhaustive_projection_diagnostic(
    datapoints: Iterable[Mapping[str, Any]],
    *,
    canonical_family_presence_by_document: Mapping[str, Iterable[str]] | None = None,
    exhaustive_audit_summary: Mapping[str, Any] | None = None,
    sample_limit: int = 25,
) -> dict[str, Any]:
    family_distribution: Counter[str] = Counter()
    unit_type_distribution: Counter[str] = Counter()
    confidence_distribution: Counter[str] = Counter()
    auto_collapse_distribution: Counter[str] = Counter()

    unsupported_rows = 0
    weak_mappings = 0
    medium_mappings = 0
    supplemental_rows = 0
    unit_conflict_rows = 0
    coherence_rejected_rows = 0
    collapse_blocked_rows = 0
    qualifier_blocked_rows = 0
    period_disambiguation_rows = 0

    documents_seen: set[str] = set()
    projected_target_row_counts: dict[str, Counter[str]] = defaultdict(Counter)
    projected_supported_target_row_counts: dict[str, Counter[str]] = defaultdict(
        Counter
    )
    projected_target_totals: Counter[str] = Counter()
    projected_supported_target_totals: Counter[str] = Counter()

    strong_signal_blocked_samples: list[dict[str, Any]] = []
    context_dependent_samples: list[dict[str, Any]] = []
    family_confusion_samples: list[dict[str, Any]] = []
    strong_signal_blocked_count = 0
    context_dependent_count = 0
    family_confusion_count = 0

    canonical_presence = {
        document_id: tuple(sorted(set(families)))
        for document_id, families in (
            canonical_family_presence_by_document or {}
        ).items()
    }

    for datapoint in datapoints:
        document_id = str(datapoint.get("document_id") or "")
        documents_seen.add(document_id)

        projection = project(datapoint)
        family_key = projection.canonical_family or "__none__"
        family_distribution[family_key] += 1
        unit_type_distribution[projection.unit_type.value] += 1
        confidence_distribution[projection.mapping_confidence.value] += 1
        auto_collapse_distribution[str(projection.auto_collapse_safe).lower()] += 1

        if projection.mapping_confidence == MappingConfidence.UNSUPPORTED:
            unsupported_rows += 1
        elif projection.mapping_confidence == MappingConfidence.WEAK:
            weak_mappings += 1
        elif projection.mapping_confidence == MappingConfidence.MEDIUM:
            medium_mappings += 1
        elif projection.mapping_confidence == MappingConfidence.SUPPLEMENTAL:
            supplemental_rows += 1

        if any("unit_type_conflict" in note for note in projection.notes):
            unit_conflict_rows += 1
        if projection.mapping_basis.startswith("rejected_unit_type_conflict"):
            coherence_rejected_rows += 1
        if (
            projection.canonical_family is not None
            and not projection.auto_collapse_safe
        ):
            collapse_blocked_rows += 1
        if "collapse_blocker_qualifier" in projection.notes:
            qualifier_blocked_rows += 1
        if "period_disambiguation_suffix" in projection.notes:
            period_disambiguation_rows += 1

        if (
            projection.canonical_family in EXTRACTOR_TARGET_FAMILIES
            and projection.mapping_confidence == MappingConfidence.STRONG
        ):
            projected_target_row_counts[document_id][projection.canonical_family] += 1
            projected_target_totals[projection.canonical_family] += 1

        if (
            projection.canonical_family in EXTRACTOR_TARGET_FAMILIES
            and projection.mapping_confidence != MappingConfidence.UNSUPPORTED
        ):
            projected_supported_target_row_counts[document_id][
                projection.canonical_family
            ] += 1
            projected_supported_target_totals[projection.canonical_family] += 1

        if (
            projection.canonical_family in EXTRACTOR_TARGET_FAMILIES
            and not projection.auto_collapse_safe
            and projection.mapping_confidence
            in (MappingConfidence.STRONG, MappingConfidence.MEDIUM)
        ):
            strong_signal_blocked_count += 1
            _append_sample(
                strong_signal_blocked_samples,
                sample_limit,
                datapoint,
                projection,
            )

        if projection.mapping_basis.startswith("context_leading_section"):
            context_dependent_count += 1
            _append_sample(
                context_dependent_samples,
                sample_limit,
                datapoint,
                projection,
            )

        candidate_families = _candidate_families(str(datapoint.get("row_label") or ""))
        if len(candidate_families) > 1:
            family_confusion_count += 1
            _append_sample(
                family_confusion_samples,
                sample_limit,
                datapoint,
                projection,
                extra={"candidate_families": list(candidate_families)},
            )

    coverage_by_document = []
    all_documents = sorted(documents_seen | set(canonical_presence))
    for document_id in all_documents:
        strong_counts = dict(
            sorted(projected_target_row_counts.get(document_id, Counter()).items())
        )
        supported_counts = dict(
            sorted(
                projected_supported_target_row_counts.get(
                    document_id, Counter()
                ).items()
            )
        )
        coverage_by_document.append(
            {
                "document_id": document_id,
                "strong_target_row_count": int(sum(strong_counts.values())),
                "strong_target_row_counts": strong_counts,
                "supported_target_row_counts": supported_counts,
            }
        )

    coarse_comparison = _build_coarse_comparison(
        canonical_presence,
        projected_target_row_counts,
        projected_supported_target_row_counts,
    )

    audit_metadata = {
        "generated_at_utc": None,
        "documents_processed": None,
        "datapoints": None,
    }
    if exhaustive_audit_summary:
        audit_metadata["generated_at_utc"] = exhaustive_audit_summary.get(
            "generated_at_utc"
        )
        audit_metadata["documents_processed"] = exhaustive_audit_summary.get(
            "documents_processed"
        )
        audit_metadata["datapoints"] = exhaustive_audit_summary.get("datapoints")

    return {
        "artifact_kind": "exhaustive_projection_diagnostic_scorecard",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provisional_label": PROVISIONAL_LABEL,
        "canonical_release_gate": CANONICAL_GATE_LABEL,
        "non_goals": list(NON_GOALS),
        "matcher_like_comparison_performed": False,
        "run_summary": {
            "documents_processed": len(documents_seen),
            "datapoints_processed": int(sum(auto_collapse_distribution.values())),
            "family_distribution": dict(sorted(family_distribution.items())),
            "unit_type_distribution": dict(sorted(unit_type_distribution.items())),
            "confidence_distribution": dict(sorted(confidence_distribution.items())),
            "auto_collapse_safe_distribution": dict(
                sorted(auto_collapse_distribution.items())
            ),
            "projected_strong_target_rows": int(sum(projected_target_totals.values())),
            "projected_supplemental_rows": supplemental_rows,
            "unsupported_rows": unsupported_rows,
        },
        "ambiguity_summary": {
            "unsupported_rows": unsupported_rows,
            "weak_mappings": weak_mappings,
            "medium_mappings": medium_mappings,
            "supplemental_rows": supplemental_rows,
            "unit_conflict_rows": unit_conflict_rows,
            "collapse_blocked_rows": collapse_blocked_rows,
            "qualifier_blocked_rows": qualifier_blocked_rows,
            "period_disambiguation_rows": period_disambiguation_rows,
            "coherence_rejected_rows": coherence_rejected_rows,
        },
        "projected_canonical_like_coverage": {
            "label": (
                "Counts of strong bridge projections into extractor-target families. "
                "Diagnostic only; not a new truth claim."
            ),
            "totals_by_family": dict(sorted(projected_target_totals.items())),
            "counts_by_document": coverage_by_document,
        },
        "suspicious_cases": {
            "strong_signal_but_not_auto_collapse_safe": {
                "definition": (
                    "Extractor-target rows with a family signal (strong or medium) "
                    "that still fail the bridge collapse gate."
                ),
                "count": strong_signal_blocked_count,
                "samples": strong_signal_blocked_samples,
            },
            "context_text_appears_important_for_mapping": {
                "definition": (
                    "Rows whose family mapping depends on context-leading-section "
                    "borrowing rather than a direct row-label alias."
                ),
                "count": context_dependent_count,
                "samples": context_dependent_samples,
            },
            "could_be_confused_with_another_family": {
                "definition": (
                    "Rows whose row label matches alias phrases from multiple known "
                    "families, making family interpretation ambiguous."
                ),
                "count": family_confusion_count,
                "samples": family_confusion_samples,
            },
        },
        "coarse_canonical_comparison": coarse_comparison,
        "source_audit": audit_metadata,
    }


def render_exhaustive_projection_markdown(
    scorecard: Mapping[str, Any],
    *,
    artifact_paths: Mapping[str, str] | None = None,
) -> str:
    run_summary = scorecard["run_summary"]
    ambiguity = scorecard["ambiguity_summary"]
    coverage = scorecard["projected_canonical_like_coverage"]
    coarse = scorecard["coarse_canonical_comparison"]
    suspicious = scorecard["suspicious_cases"]

    lines: list[str] = [
        "# Exhaustive Projection Diagnostic Summary",
        "",
        f"> {scorecard['provisional_label']}",
        f"> {scorecard['canonical_release_gate']}",
        "> This report does not implement tuple matching, precision/recall, or production accuracy scoring.",
        "",
        "## Run Summary",
        "",
        f"- Datapoints processed: {run_summary['datapoints_processed']}",
        f"- Documents processed: {run_summary['documents_processed']}",
        f"- Projected strong target rows: {run_summary['projected_strong_target_rows']}",
        f"- Supplemental rows: {run_summary['projected_supplemental_rows']}",
        f"- Unsupported rows: {run_summary['unsupported_rows']}",
        "",
        "### Confidence Distribution",
        "",
        "| Confidence | Count |",
        "| --- | ---: |",
    ]
    for name, count in _sorted_items_by_count(run_summary["confidence_distribution"]):
        lines.append(f"| {name} | {count} |")

    lines.extend(
        [
            "",
            "### Unit Type Distribution",
            "",
            "| Unit type | Count |",
            "| --- | ---: |",
        ]
    )
    for name, count in _sorted_items_by_count(run_summary["unit_type_distribution"]):
        lines.append(f"| {name} | {count} |")

    lines.extend(
        [
            "",
            "## Ambiguity Summary",
            "",
            "| Counter | Count |",
            "| --- | ---: |",
        ]
    )
    for key, value in ambiguity.items():
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Projected Canonical-Like Coverage",
            "",
            f"- {coverage['label']}",
            "",
            "| Family | Strong projected rows |",
            "| --- | ---: |",
        ]
    )
    for family, count in _sorted_items_by_count(coverage["totals_by_family"]):
        lines.append(f"| {family} | {count} |")

    lines.extend(
        [
            "",
            "### By Document",
            "",
            "| Document | Strong target rows | Strong target families |",
            "| --- | ---: | --- |",
        ]
    )
    for row in coverage["counts_by_document"]:
        family_counts = row["strong_target_row_counts"]
        family_text = (
            ", ".join(f"{family}:{count}" for family, count in family_counts.items())
            if family_counts
            else "-"
        )
        lines.append(
            f"| {row['document_id']} | {row['strong_target_row_count']} | {family_text} |"
        )

    lines.extend(
        [
            "",
            "## Coarse Canonical Comparison",
            "",
            f"- {coarse['label']}",
            "",
            "| Document | Canonical families | Projected strong target families | Supported target rows |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in coarse["by_document"]:
        lines.append(
            "| "
            f"{row['document_id']} | "
            f"{', '.join(row['canonical_families_present']) or '-'} | "
            f"{', '.join(row['projected_strong_target_families_present']) or '-'} | "
            f"{_format_count_map(row['projected_supported_target_row_counts'])} |"
        )

    lines.extend(["", "## Suspicious Cases", ""])
    for key in (
        "strong_signal_but_not_auto_collapse_safe",
        "context_text_appears_important_for_mapping",
        "could_be_confused_with_another_family",
    ):
        block = suspicious[key]
        lines.append(f"### {key.replace('_', ' ').title()}")
        lines.append("")
        lines.append(f"- Count: {block['count']}")
        lines.append(f"- {block['definition']}")
        lines.append("")
        lines.append("| Document | Datapoint | Label | Family | Confidence | Basis |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        samples = block["samples"][:10]
        if samples:
            for sample in samples:
                lines.append(
                    "| "
                    f"{sample['document_id']} | "
                    f"{sample['datapoint_id']} | "
                    f"{sample['row_label'] or '-'} | "
                    f"{sample['canonical_family'] or '-'} | "
                    f"{sample['mapping_confidence']} | "
                    f"{sample['mapping_basis']} |"
                )
        else:
            lines.append("| - | - | - | - | - | - |")
        lines.append("")

    if artifact_paths:
        lines.extend(
            [
                "## Artifact Paths",
                "",
                "| Artifact | Path |",
                "| --- | --- |",
            ]
        )
        for name, path in sorted(artifact_paths.items()):
            lines.append(f"| {name} | `{path}` |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_exhaustive_projection_artifacts(
    scorecard: Mapping[str, Any],
    out_dir: str | Path,
) -> dict[str, Path]:
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    scorecard_json = target_dir / "projection_scorecard.json"
    summary_markdown = target_dir / "projection_summary.md"
    artifact_paths = {
        "scorecard_json": scorecard_json,
        "summary_markdown": summary_markdown,
    }
    artifact_path_strings = {key: str(path) for key, path in artifact_paths.items()}
    payload = dict(scorecard)
    payload["artifact_paths"] = artifact_path_strings

    scorecard_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary_markdown.write_text(
        render_exhaustive_projection_markdown(
            payload,
            artifact_paths=artifact_path_strings,
        ),
        encoding="utf-8",
    )
    return artifact_paths


def _build_coarse_comparison(
    canonical_presence: Mapping[str, tuple[str, ...]],
    projected_target_row_counts: Mapping[str, Counter[str]],
    projected_supported_target_row_counts: Mapping[str, Counter[str]],
) -> dict[str, Any]:
    by_document: list[dict[str, Any]] = []
    canonical_doc_presence: Counter[str] = Counter()
    projected_strong_doc_presence: Counter[str] = Counter()
    projected_strong_row_totals: Counter[str] = Counter()
    projected_supported_row_totals: Counter[str] = Counter()

    all_documents = sorted(
        set(canonical_presence)
        | set(projected_target_row_counts)
        | set(projected_supported_target_row_counts)
    )
    for document_id in all_documents:
        canonical_families = tuple(sorted(canonical_presence.get(document_id, ())))
        strong_counts = projected_target_row_counts.get(document_id, Counter())
        supported_counts = projected_supported_target_row_counts.get(
            document_id, Counter()
        )

        for family in canonical_families:
            canonical_doc_presence[family] += 1
        for family, count in strong_counts.items():
            projected_strong_doc_presence[family] += 1
            projected_strong_row_totals[family] += count
        for family, count in supported_counts.items():
            projected_supported_row_totals[family] += count

        by_document.append(
            {
                "document_id": document_id,
                "canonical_families_present": list(canonical_families),
                "canonical_family_count": len(canonical_families),
                "projected_strong_target_families_present": sorted(strong_counts),
                "projected_strong_target_family_count": len(strong_counts),
                "projected_strong_target_row_counts": dict(
                    sorted(strong_counts.items())
                ),
                "projected_supported_target_row_counts": dict(
                    sorted(supported_counts.items())
                ),
            }
        )

    by_family = []
    all_families = sorted(
        set(canonical_doc_presence)
        | set(projected_strong_doc_presence)
        | set(projected_supported_row_totals)
    )
    for family in all_families:
        by_family.append(
            {
                "family": family,
                "canonical_doc_presence_count": canonical_doc_presence[family],
                "projected_strong_doc_presence_count": projected_strong_doc_presence[
                    family
                ],
                "projected_strong_row_count": projected_strong_row_totals[family],
                "projected_supported_row_count": projected_supported_row_totals[family],
            }
        )

    return {
        "available": bool(canonical_presence),
        "label": (
            "Coarse comparison only. No tuple matching, no precision/recall, "
            "and no correctness inference from family presence alone."
        ),
        "documents_with_both_surfaces": sum(
            1
            for document_id in all_documents
            if document_id in canonical_presence
            and (
                document_id in projected_target_row_counts
                or document_id in projected_supported_target_row_counts
            )
        ),
        "canonical_only_documents": sorted(
            document_id
            for document_id in canonical_presence
            if document_id not in projected_supported_target_row_counts
            and document_id not in projected_target_row_counts
        ),
        "projection_only_documents": sorted(
            document_id
            for document_id in projected_supported_target_row_counts
            if document_id not in canonical_presence
        ),
        "by_document": by_document,
        "by_family": by_family,
    }


def _append_sample(
    bucket: list[dict[str, Any]],
    sample_limit: int,
    datapoint: Mapping[str, Any],
    projection: OntologyProjection,
    *,
    extra: Mapping[str, Any] | None = None,
) -> None:
    if len(bucket) >= sample_limit:
        return
    item = {
        "document_id": str(datapoint.get("document_id") or ""),
        "datapoint_id": str(datapoint.get("datapoint_id") or ""),
        "row_label": str(datapoint.get("row_label") or ""),
        "context_text": str(datapoint.get("context_text") or ""),
        "raw_value": datapoint.get("raw_value"),
        "canonical_family": projection.canonical_family,
        "mapping_confidence": projection.mapping_confidence.value,
        "mapping_basis": projection.mapping_basis,
        "unit_type": projection.unit_type.value,
        "auto_collapse_safe": projection.auto_collapse_safe,
        "notes": list(projection.notes),
    }
    if extra:
        item.update(extra)
    bucket.append(item)


def _candidate_families(text: str) -> tuple[str, ...]:
    normalized = bridge._normalize_label(text)
    if not normalized:
        return ()
    candidates: set[str] = set()
    for family, phrases in bridge._FAMILY_CORE_PHRASES.items():
        for phrase in phrases:
            norm_phrase = bridge._normalize_label(phrase)
            if norm_phrase and norm_phrase in normalized:
                candidates.add(family)
                break
    return tuple(sorted(candidates))


def _sorted_items_by_count(counts: Mapping[str, int]) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _format_count_map(counts: Mapping[str, int]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"{key}:{value}" for key, value in counts.items())


__all__ = [
    "CANONICAL_GATE_LABEL",
    "NON_GOALS",
    "PROVISIONAL_LABEL",
    "build_exhaustive_projection_diagnostic",
    "load_canonical_family_presence",
    "load_exhaustive_audit_summary",
    "load_exhaustive_datapoints",
    "render_exhaustive_projection_markdown",
    "write_exhaustive_projection_artifacts",
]
