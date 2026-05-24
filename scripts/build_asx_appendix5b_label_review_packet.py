#!/usr/bin/env python3
"""Build manual-review packets from Appendix 5B candidate artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.asx_appendix5b_label_review_packet import (  # noqa: E402
    build_appendix5b_label_review_packet,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a manual-review packet from Appendix 5B candidate artifacts."
    )
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--labels-template", required=True, type=Path)
    parser.add_argument(
        "artifacts",
        nargs="+",
        type=Path,
        help="Appendix 5B candidate artifact JSON files.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    packet = build_appendix5b_label_review_packet(
        artifact_paths=args.artifacts,
        output_json_path=args.output_json,
        output_csv_path=args.output_csv,
        labels_template_path=args.labels_template,
    )
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "output_json": str(args.output_json),
                "output_csv": str(args.output_csv),
                "labels_template": str(args.labels_template),
                "summary": packet["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
