#!/usr/bin/env python3
"""Build Appendix 5B candidate manifests from existing Docling structured JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.asx_appendix5b_candidate_artifacts import run_manifest_to_artifact
from app.services.asx_appendix5b_manifest_builder import (
    build_manifest_from_gold_fixtures,
    parse_structured_source_args,
    write_data_missing_artifact,
    write_manifest,
)


DEFAULT_FIXTURES = [
    Path("financial-engine_v2/backend/tests/eval_fixtures/GRE_Q_2024-12-31.json"),
    Path("financial-engine_v2/backend/tests/eval_fixtures/EQR_Q_2025-12-31.json"),
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an Appendix 5B manifest from existing Docling caches or "
            "explicit structured JSON files."
        )
    )
    parser.add_argument(
        "--gold-fixture",
        action="append",
        type=Path,
        default=[],
        help="Gold/eval fixture JSON. Defaults to GRE and EQR quarterly fixtures.",
    )
    parser.add_argument(
        "--structured-source",
        action="append",
        default=[],
        help="Explicit structured source as document_id=path.",
    )
    parser.add_argument("--output", required=True, type=Path, help="Output manifest JSON.")
    parser.add_argument(
        "--artifact-output",
        type=Path,
        help="Optional Appendix 5B candidate comparison artifact output.",
    )
    parser.add_argument(
        "--repo-root",
        default=ROOT,
        type=Path,
        help="Repository root for resolving relative paths.",
    )
    parser.add_argument(
        "--run-id",
        default="appendix5b_real_table_manifest_20260516",
        help="Run identifier written into the manifest.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    fixtures = args.gold_fixture or DEFAULT_FIXTURES
    manifest = build_manifest_from_gold_fixtures(
        gold_fixture_paths=fixtures,
        repo_root=args.repo_root,
        structured_sources=parse_structured_source_args(args.structured_source),
        run_id=args.run_id,
    )
    write_manifest(args.output, manifest)

    artifact_summary = None
    if args.artifact_output:
        if manifest["documents"]:
            artifact = run_manifest_to_artifact(
                manifest_path=args.output,
                output_path=args.artifact_output,
                repo_root=args.repo_root,
            )
        else:
            artifact = write_data_missing_artifact(args.artifact_output, manifest)
        artifact_summary = artifact.get("summary")

    print(
        json.dumps(
            {
                "status": "SUCCESS" if manifest["documents"] else "DATA_MISSING",
                "output": str(args.output),
                "artifact_output": str(args.artifact_output) if args.artifact_output else None,
                "summary": manifest["summary"],
                "artifact_summary": artifact_summary,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
