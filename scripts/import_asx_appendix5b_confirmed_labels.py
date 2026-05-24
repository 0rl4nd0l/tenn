#!/usr/bin/env python3
"""Import confirmed Appendix 5B labels from eval fixtures into scorer format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.asx_appendix5b_confirmed_label_importer import (  # noqa: E402
    import_confirmed_appendix5b_labels,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import report-local Appendix 5B labels from confirmed eval fixtures."
    )
    parser.add_argument("--fixtures-dir", required=True, type=Path)
    parser.add_argument("--output-labels", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument(
        "artifacts",
        nargs="+",
        type=Path,
        help="Appendix 5B candidate artifact JSON files.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = import_confirmed_appendix5b_labels(
        artifact_paths=args.artifacts,
        fixtures_dir=args.fixtures_dir,
        output_labels_path=args.output_labels,
        output_report_path=args.output_report,
    )
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "output_labels": str(args.output_labels),
                "output_report": str(args.output_report),
                "summary": result["report"]["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
