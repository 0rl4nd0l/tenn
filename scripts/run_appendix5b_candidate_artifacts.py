#!/usr/bin/env python3
"""Build read-only Appendix 5B candidate eval artifacts from a table manifest."""

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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic Appendix 5B candidate artifact generation."
    )
    parser.add_argument("--manifest", required=True, type=Path, help="Input manifest JSON.")
    parser.add_argument("--output", required=True, type=Path, help="Output artifact JSON.")
    parser.add_argument(
        "--repo-root",
        default=ROOT,
        type=Path,
        help="Repository root for resolving relative gold fixture paths.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    artifact = run_manifest_to_artifact(
        manifest_path=args.manifest,
        output_path=args.output,
        repo_root=args.repo_root,
    )
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "output": str(args.output),
                "document_count": artifact["document_count"],
                "summary": artifact["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
