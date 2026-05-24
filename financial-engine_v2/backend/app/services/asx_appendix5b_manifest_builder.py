"""Build Appendix 5B candidate manifests from Docling structured output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


DATA_MISSING = "DATA_MISSING"


@dataclass(frozen=True)
class StructuredSource:
    path: Path
    source_type: str


def build_manifest_from_gold_fixtures(
    *,
    gold_fixture_paths: list[Path],
    repo_root: Path,
    structured_sources: dict[str, Path] | None = None,
    run_id: str = "appendix5b_real_table_manifest",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Create an Appendix 5B manifest from existing Docling structured JSON.

    This function is read-only. It does not run Docling and does not mutate
    caches. Missing source PDFs/caches are recorded as DATA_MISSING blockers.
    """

    structured_sources = structured_sources or {}
    documents: list[dict[str, Any]] = []
    skipped_documents: list[dict[str, Any]] = []

    for fixture_path in gold_fixture_paths:
        fixture_path = _resolve_path(fixture_path, repo_root=repo_root)
        gold = _load_json(fixture_path)
        document_id = str(gold.get("document_id") or fixture_path.stem)
        source = _resolve_structured_source(
            gold=gold,
            document_id=document_id,
            repo_root=repo_root,
            structured_sources=structured_sources,
        )
        if source is None:
            skipped_documents.append(
                _missing_document_payload(
                    document_id=document_id,
                    gold=gold,
                    fixture_path=fixture_path,
                    repo_root=repo_root,
                )
            )
            continue

        structured = _load_json(source.path)
        documents.append(
            {
                "document_id": document_id,
                "ticker": gold.get("ticker"),
                "period_type": gold.get("period_type"),
                "period_end": gold.get("period_end"),
                "gold_fixture_path": _repo_relative(fixture_path, repo_root),
                "structured_source_path": _repo_relative(source.path, repo_root),
                "structured_source_type": source.source_type,
                "tables": _manifest_tables(structured),
            }
        )

    return {
        "run_id": run_id,
        "manifest_type": "appendix5b_docling_table_manifest_v1",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "canonical_write": False,
        "documents": documents,
        "skipped_documents": skipped_documents,
        "summary": {
            "documents_requested": len(gold_fixture_paths),
            "documents_ready": len(documents),
            "documents_skipped": len(skipped_documents),
            "tables_ready": sum(len(document["tables"]) for document in documents),
        },
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def write_data_missing_artifact(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    artifact = {
        "artifact_type": "appendix5b_candidate_eval_v1",
        "run_id": manifest.get("run_id"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_write": False,
        "runtime": "read_only_manifest",
        "status": DATA_MISSING,
        "summary": {
            "documents_requested": manifest.get("summary", {}).get("documents_requested", 0),
            "documents_ready": manifest.get("summary", {}).get("documents_ready", 0),
            "documents_skipped": manifest.get("summary", {}).get("documents_skipped", 0),
        },
        "skipped_documents": manifest.get("skipped_documents", []),
        "documents": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    return artifact


def parse_structured_source_args(values: list[str]) -> dict[str, Path]:
    """Parse repeated document_id=path CLI arguments."""

    parsed: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"structured source must be document_id=path: {value}")
        document_id, path = value.split("=", 1)
        document_id = document_id.strip()
        if not document_id:
            raise ValueError(f"structured source document_id is empty: {value}")
        parsed[document_id] = Path(path)
    return parsed


def _resolve_structured_source(
    *,
    gold: dict[str, Any],
    document_id: str,
    repo_root: Path,
    structured_sources: dict[str, Path],
) -> StructuredSource | None:
    explicit = structured_sources.get(document_id)
    if explicit is not None:
        path = _resolve_path(explicit, repo_root=repo_root)
        if path.exists():
            return StructuredSource(path=path, source_type="explicit_structured_json")
        return None

    pdf_path_value = gold.get("pdf_path")
    if not pdf_path_value:
        return None
    for pdf_path in _candidate_pdf_paths(str(pdf_path_value), repo_root=repo_root):
        cache_path = Path(str(pdf_path) + ".docling.json")
        if cache_path.exists():
            return StructuredSource(path=cache_path, source_type="docling_cache")
    return None


def _manifest_tables(structured: dict[str, Any]) -> list[dict[str, Any]]:
    tables = structured.get("tables")
    if not isinstance(tables, list):
        return []
    manifest_tables: list[dict[str, Any]] = []
    for table in tables:
        if not isinstance(table, dict):
            continue
        rows = table.get("rows") or []
        headers = table.get("headers") or (rows[0] if rows else [])
        manifest_tables.append(
            {
                "page_number": int(table.get("page_number") or 0),
                "caption": str(table.get("caption") or ""),
                "headers": [str(cell or "") for cell in headers],
                "rows": [
                    [str(cell or "") for cell in row]
                    for row in rows
                    if isinstance(row, list)
                ],
            }
        )
    return manifest_tables


def _missing_document_payload(
    *,
    document_id: str,
    gold: dict[str, Any],
    fixture_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    pdf_path = str(gold.get("pdf_path") or "")
    checked_paths = [
        str(path)
        for candidate in _candidate_pdf_paths(pdf_path, repo_root=repo_root)
        for path in (candidate, Path(str(candidate) + ".docling.json"))
    ] if pdf_path else []
    return {
        "document_id": document_id,
        "ticker": gold.get("ticker"),
        "period_type": gold.get("period_type"),
        "period_end": gold.get("period_end"),
        "gold_fixture_path": _repo_relative(fixture_path, repo_root),
        "status": DATA_MISSING,
        "failure_reason": "DATA_MISSING: no explicit structured JSON or existing Docling cache found",
        "pdf_path": pdf_path,
        "checked_paths": checked_paths,
    }


def _candidate_pdf_paths(pdf_path: str, *, repo_root: Path) -> list[Path]:
    raw = Path(pdf_path)
    if raw.is_absolute():
        return [raw]
    return [
        repo_root / raw,
        repo_root / "financial-engine_v2" / raw,
    ]


def _resolve_path(path: Path, *, repo_root: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return loaded


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)
