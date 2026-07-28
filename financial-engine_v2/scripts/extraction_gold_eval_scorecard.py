#!/usr/bin/env python3
"""Run a minimal real-document gold evaluation scorecard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.extraction_gold_eval import build_real_gold_scorecard


DEFAULT_FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "extraction_gold_real"
)


def _coerce_payload_map(path: Path) -> dict[str, dict[str, Any]]:
    payloads = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payloads, dict):
        raise ValueError("actuals JSON must be a JSON object")

    output: dict[str, dict[str, Any]] = {}
    for key, value in payloads.items():
        if not isinstance(value, dict):
            raise ValueError(
                f"payload for document '{key}' must be an object, got {type(value)}"
            )
        output[str(key)] = value
    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic scorecard from real-gold fixtures.",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=DEFAULT_FIXTURES_DIR,
        help="Directory containing real-gold fixture JSON files.",
    )
    parser.add_argument(
        "--actuals-json",
        type=Path,
        required=True,
        help="JSON object mapping document_id -> extracted payload.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation for stdout output (0 = compact)",
    )
    parser.add_argument(
        "--corpus-classification",
        choices=["non_holdout", "holdout"],
        required=True,
    )
    parser.add_argument(
        "--access-mode",
        choices=["development", "protected"],
        required=True,
    )
    parser.add_argument("--development-aggregate-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    payloads = _coerce_payload_map(args.actuals_json)
    development_aggregate = (
        json.loads(args.development_aggregate_json.read_text(encoding="utf-8"))
        if args.development_aggregate_json is not None
        else None
    )
    scorecard = build_real_gold_scorecard(
        args.fixtures_dir,
        payloads,
        corpus_classification=args.corpus_classification,
        access_mode=args.access_mode,
        development_aggregate=development_aggregate,
    )

    indent = None if args.indent <= 0 else args.indent
    print(json.dumps(scorecard, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
