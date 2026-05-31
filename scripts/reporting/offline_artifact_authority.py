#!/usr/bin/env python3
"""Report-local authority metadata helpers for offline artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


AUTHORITY_VERSION = "offline_artifact_authority_v1"
REPORT_LOCAL_DO_NOT_OVERCLAIM = [
    "This artifact is report-local and is not canonical financial truth.",
    "This artifact does not authorize canonical database writes, Qdrant writes, production backfill, or canary execution.",
    "Backend services remain the sole authority for canonical extraction, storage, retrieval, and data correctness.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(path: Path | str, artifact_type: str, notes: str = "") -> dict[str, Any]:
    resolved = Path(path)
    return {
        "path": resolved.as_posix(),
        "artifact_type": artifact_type,
        "exists": resolved.exists(),
        "sha256": sha256_file(resolved),
        "notes": notes,
    }


def _coerce_artifacts(items: Sequence[Path | str | Mapping[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, Mapping):
            records.append(dict(item))
        else:
            records.append(artifact_record(item, "artifact"))
    return records


def build_authority_metadata(
    *,
    artifact_type: str,
    producer: str,
    lane: str = "Evaluation",
    source_artifacts: Sequence[Path | str | Mapping[str, Any]] = (),
    output_artifacts: Sequence[Path | str | Mapping[str, Any]] = (),
    generated_at: str | None = None,
    extra_do_not_overclaim: Sequence[str] = (),
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "artifact_authority_version": AUTHORITY_VERSION,
        "artifact_type": artifact_type,
        "producer": producer,
        "generated_at": generated_at or utc_now(),
        "lane": lane,
        "truth_status": "report_local_only",
        "canonical_financial_truth": False,
        "canonical_write_allowed": False,
        "broad_backfill_authorized": False,
        "runtime_mutation": False,
        "production_data_access": False,
        "source_artifacts": _coerce_artifacts(source_artifacts),
        "output_artifacts": _coerce_artifacts(output_artifacts),
        "do_not_overclaim": [
            *REPORT_LOCAL_DO_NOT_OVERCLAIM,
            *[str(item) for item in extra_do_not_overclaim],
        ],
    }
    if extra:
        metadata["extra"] = dict(extra)
    return metadata


def validate_authority_metadata(metadata: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    required_false_fields = (
        "canonical_financial_truth",
        "canonical_write_allowed",
        "broad_backfill_authorized",
        "runtime_mutation",
        "production_data_access",
    )
    if metadata.get("artifact_authority_version") != AUTHORITY_VERSION:
        issues.append("artifact_authority_version")
    if metadata.get("truth_status") != "report_local_only":
        issues.append("truth_status")
    for field in required_false_fields:
        if metadata.get(field) is not False:
            issues.append(field)
    if not isinstance(metadata.get("source_artifacts"), list) or not metadata.get("source_artifacts"):
        issues.append("source_artifacts")
    if not metadata.get("do_not_overclaim"):
        issues.append("do_not_overclaim")
    return issues


def write_authority_manifest(path: Path | str, metadata: Mapping[str, Any]) -> None:
    issues = validate_authority_metadata(metadata)
    if issues:
        raise ValueError("invalid authority metadata: " + ", ".join(issues))
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(dict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")
