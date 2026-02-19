#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.analysis_report_schema import validate_analysis_report  # noqa: E402


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"JSON file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Failed to parse JSON at {path}: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate analysis report schema and citation gates.")
    parser.add_argument("--report", required=True, help="Path to report JSON.")
    parser.add_argument("--evidence", default="", help="Optional evidence bundle JSON path.")
    parser.add_argument(
        "--min-citation-coverage",
        type=float,
        default=0.95,
        help="Minimum required citation coverage (0..1).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.min_citation_coverage < 0 or args.min_citation_coverage > 1:
        raise SystemExit("--min-citation-coverage must be in [0, 1].")

    report = _load_json(Path(args.report))
    evidence = _load_json(Path(args.evidence)) if args.evidence else None

    result = validate_analysis_report(
        report=report,
        evidence_bundle=evidence,
        min_citation_coverage=args.min_citation_coverage,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
