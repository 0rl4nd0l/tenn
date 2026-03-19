#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.evaluation.calibration import DEFAULT_CALIBRATION_PATH, calibrate_thresholds


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate extraction routing thresholds from benchmark output JSON.")
    parser.add_argument(
        "--benchmark-json",
        required=True,
        help="Path to benchmark JSON (e.g. batch_benchmark_report.json).",
    )
    parser.add_argument(
        "--out-json",
        default=str(DEFAULT_CALIBRATION_PATH),
        help="Output path for calibration JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    calibration = calibrate_thresholds(args.benchmark_json)

    out_json = Path(args.out_json).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(calibration, indent=2), encoding="utf-8")

    canonical_path = DEFAULT_CALIBRATION_PATH.expanduser().resolve()
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_text(json.dumps(calibration, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "benchmark_json": str(Path(args.benchmark_json).expanduser().resolve()),
                "out_json": str(out_json),
                "persisted_calibration": str(canonical_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
