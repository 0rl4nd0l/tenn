#!/usr/bin/env python3
"""Generate ASX document-type sidecar artifacts from explicit fixture JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
DEFAULT_OUT_DIR = (
    REPO_ROOT
    / "reports"
    / "agent_jobs"
    / "asx_document_type_sidecar_artifact_v1_20260520"
    / "sidecars"
)
FIXTURE_CONTRACT = "asx_document_type_fixture_contract_v1"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.asx_document_type_sidecar import build_asx_document_type_sidecar  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures-dir",
        required=True,
        type=Path,
        help="Directory containing the ASX document-type fixture manifest and JSON files.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory where sidecar JSON files will be written.",
    )
    args = parser.parse_args(argv)

    try:
        fixtures_dir = _resolve_fixture_dir(args.fixtures_dir)
        out_dir = _resolve_out_dir(args.out_dir, fixtures_dir=fixtures_dir)
        fixtures = _load_fixtures(fixtures_dir)
        written = _write_sidecars(fixtures, out_dir=out_dir)
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "fixtures_dir": str(fixtures_dir),
                "out_dir": str(out_dir),
                "sidecar_count": len(written),
                "sidecars": [str(path) for path in written],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _resolve_fixture_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if not resolved.exists():
        raise ValueError(f"--fixtures-dir does not exist: {path}")
    if not resolved.is_dir():
        raise ValueError(f"--fixtures-dir must be a directory: {path}")

    manifest_path = resolved / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"--fixtures-dir is not an ASX fixture directory; missing manifest.json: {resolved}")

    manifest = _load_json(manifest_path)
    if manifest.get("contract") != FIXTURE_CONTRACT:
        raise ValueError(f"--fixtures-dir manifest has unsupported contract: {manifest.get('contract')!r}")
    if manifest.get("canonical_write") is not False:
        raise ValueError("--fixtures-dir manifest must set canonical_write=false")
    if not isinstance(manifest.get("fixture_files"), list):
        raise ValueError("--fixtures-dir manifest must list fixture_files")
    return resolved


def _resolve_out_dir(path: Path, *, fixtures_dir: Path) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if resolved == fixtures_dir or fixtures_dir in resolved.parents:
        raise ValueError("--out-dir must not be inside --fixtures-dir")
    return resolved


def _load_fixtures(fixtures_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    manifest = _load_json(fixtures_dir / "manifest.json")
    fixtures: list[tuple[Path, dict[str, Any]]] = []
    for name in manifest["fixture_files"]:
        if not isinstance(name, str) or "/" in name or name in {"", ".", ".."}:
            raise ValueError(f"unsafe fixture file name in manifest: {name!r}")
        path = fixtures_dir / name
        if not path.is_file():
            raise ValueError(f"fixture file listed in manifest is missing: {path}")
        loaded = _load_json(path)
        if loaded.get("canonical_write") is not False:
            raise ValueError(f"fixture must set canonical_write=false: {path.name}")
        fixtures.append((path, loaded))

    if not fixtures:
        raise ValueError("--fixtures-dir manifest lists no fixtures")
    return fixtures


def _write_sidecars(fixtures: list[tuple[Path, dict[str, Any]]], *, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fixture_path, fixture in fixtures:
        artifact = build_asx_document_type_sidecar(fixture, source="synthetic_fixture")
        if artifact.get("canonical_write") is not False:
            raise ValueError(f"sidecar canonical_write must be false: {fixture_path.name}")

        output_path = out_dir / f"{_artifact_stem(fixture, fixture_path)}.json"
        output_path.write_text(
            json.dumps(artifact, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(output_path)
    return written


def _artifact_stem(fixture: dict[str, Any], fixture_path: Path) -> str:
    raw = fixture.get("fixture_id")
    stem = raw if isinstance(raw, str) and raw.strip() else fixture_path.stem
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", stem.strip()) + ".sidecar"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError(f"JSON must contain an object: {path}")
    return loaded


if __name__ == "__main__":
    raise SystemExit(main())
