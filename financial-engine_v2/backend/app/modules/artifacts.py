"""artifacts.py — Artifact writer for analysis modules.

Handles atomic writes to reports/analysis/{ticker}/, includes run_metadata,
and returns the written path.

Design decisions:
  - Atomic writes (write to temp, rename) to prevent partial artifacts.
  - Deterministic file naming: {module_name}.json.
  - run_metadata includes timestamp, module version, git info where available.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.modules.base import ArtifactSet


def _git_info() -> dict[str, str]:
    """Best-effort git metadata. Returns empty dict on failure."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode().strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).decode().strip()
        return {"git_commit": commit, "git_branch": branch}
    except Exception:
        return {}


def artifact_path(
    ticker: str,
    module_name: str,
    reports_root: str | None = None,
) -> Path:
    """Canonical artifact path: {reports_root}/analysis/{ticker}/{module}.json"""
    root = Path(reports_root) if reports_root else _default_reports_root()
    return root / "analysis" / ticker / f"{module_name}.json"


def _default_reports_root() -> Path:
    """Derive reports root from DATA_ROOT or fall back to project default."""
    data_root = os.environ.get("DATA_ROOT")
    if data_root:
        return Path(data_root) / "reports"
    # Fall back to project-relative path
    return Path(__file__).resolve().parents[3] / "reports"


def write_artifact(
    result: ArtifactSet,
    *,
    module_version: str = "1.0.0",
    reports_root: str | None = None,
) -> Path:
    """Write an ArtifactSet as a JSON file with metadata. Returns the path.

    Uses atomic write (temp file + rename) to prevent partial artifacts.
    """
    path = artifact_path(result.ticker, result.module_name, reports_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = _serialize(result, module_version)

    # Atomic write
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, str(path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return path


def _serialize(result: ArtifactSet, module_version: str) -> dict[str, Any]:
    """Convert ArtifactSet to a JSON-serializable dict with metadata."""
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "ticker": result.ticker,
        "module": result.module_name,
        "completeness": result.completeness.value,
        "generated_at": result.computed_at,
        **result.structured,
    }

    if result.narrative is not None:
        payload["narrative"] = {
            "summary": result.narrative.summary,
            "detail": result.narrative.detail,
            "model_id": result.narrative.model_id,
            "prompt_hash": result.narrative.prompt_hash,
            "cached": result.narrative.cached,
        }

    if result.evidence:
        payload["evidence"] = [
            {
                "evidence_id": e.evidence_id,
                "source_type": e.source_type,
                "content": e.content,
                "source_id": e.source_id,
                "confidence": e.confidence,
            }
            for e in result.evidence
        ]

    if result.warnings:
        payload["warnings"] = list(result.warnings)

    payload["metadata"] = {
        "module_version": module_version,
        **_git_info(),
    }

    return payload


def read_artifact(
    ticker: str,
    module_name: str,
    reports_root: str | None = None,
) -> dict[str, Any] | None:
    """Read a previously written artifact. Returns None if not found."""
    path = artifact_path(ticker, module_name, reports_root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
