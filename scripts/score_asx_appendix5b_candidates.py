#!/usr/bin/env python3
"""Score Appendix 5B candidate artifacts against explicit labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.asx_appendix5b_candidate_scorer import (  # noqa: E402
    score_appendix5b_candidate_artifacts,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score read-only Appendix 5B candidate artifacts against labels."
    )
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "artifacts",
        nargs="+",
        type=Path,
        help="Appendix 5B candidate artifact JSON files.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = score_appendix5b_candidate_artifacts(
        artifact_paths=args.artifacts,
        labels_path=args.labels,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "output": str(args.output),
                "summary": report["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
