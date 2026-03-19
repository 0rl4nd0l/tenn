#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from services.evaluation.normalizer import normalize_metric_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GROUND_TRUTH_DIR = REPO_ROOT / "data" / "ground_truth"
_DOC_ID_SUFFIX_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$", re.IGNORECASE)


@dataclass(frozen=True)
class GroundTruthRecord:
    pdf: str
    doc_id: str
    metrics: dict[str, float]
    source_file: str


def _doc_id_from_pdf(pdf_value: str) -> str:
    path = Path(str(pdf_value))
    stem = path.stem.lower()
    match = _DOC_ID_SUFFIX_RE.search(stem)
    if match:
        return str(match.group(1)).lower()
    return stem


def _record_from_payload(payload: Mapping[str, Any], source_file: Path) -> GroundTruthRecord | None:
    pdf = str(payload.get("pdf") or "").strip()
    if not pdf:
        return None
    raw_metrics = payload.get("metrics")
    if not isinstance(raw_metrics, Mapping):
        return None
    metrics = normalize_metric_payload(raw_metrics)
    return GroundTruthRecord(
        pdf=pdf,
        doc_id=_doc_id_from_pdf(pdf),
        metrics=metrics,
        source_file=str(source_file),
    )


def _iter_payload_documents(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping) and isinstance(payload.get("documents"), list):
        return [doc for doc in payload["documents"] if isinstance(doc, Mapping)]
    if isinstance(payload, list):
        return [doc for doc in payload if isinstance(doc, Mapping)]
    if isinstance(payload, Mapping):
        return [payload]
    return []


def _json_files_from_path(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".json":
        return [path]
    if path.is_dir():
        return sorted(candidate for candidate in path.rglob("*.json") if candidate.is_file())
    return []


def load_ground_truth_records(path: str | Path | None = None) -> list[GroundTruthRecord]:
    target = Path(path).expanduser().resolve() if path else DEFAULT_GROUND_TRUTH_DIR
    if not target.exists():
        return []
    records: list[GroundTruthRecord] = []
    for json_file in _json_files_from_path(target):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for document in _iter_payload_documents(payload):
            record = _record_from_payload(document, json_file)
            if record is not None:
                records.append(record)
    return records


def load_ground_truth_index(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for record in load_ground_truth_records(path):
        index[record.doc_id] = asdict(record)
    return index


def lookup_ground_truth_metrics(pdf_path: str | Path, ground_truth_index: Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    doc_id = _doc_id_from_pdf(str(pdf_path))
    payload = ground_truth_index.get(doc_id)
    if not isinstance(payload, Mapping):
        return {}
    metrics = payload.get("metrics")
    if not isinstance(metrics, Mapping):
        return {}
    return normalize_metric_payload(metrics)
