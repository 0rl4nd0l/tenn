#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.system_analyzer import DEFAULT_BACKEND_BASE_URL, DEFAULT_LOOP_MODE, run_analyzer_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the recommendation-first system analyzer loop.")
    parser.add_argument(
        "--mode",
        choices=("recommend", "prepare_patch", "apply_gated"),
        default=DEFAULT_LOOP_MODE,
        help="Loop mode. Default is recommendation-only.",
    )
    parser.add_argument(
        "--backend-base-url",
        default=DEFAULT_BACKEND_BASE_URL,
        help="Backend base URL used for health and status checks.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Per-check timeout budget in seconds.",
    )
    parser.add_argument(
        "--watchdog-seconds",
        type=float,
        default=45.0,
        help="Global loop watchdog in seconds.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not persist reports to /data; still emit JSON to stdout.",
    )
    parser.add_argument(
        "--allow-apply-gated",
        action="store_true",
        help="Explicitly acknowledge apply_gated mode. The analyzer still remains non-mutating.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_analyzer_loop(
        mode=args.mode,
        backend_base_url=args.backend_base_url,
        write_report=not args.no_write,
        timeout_seconds=args.timeout_seconds,
        watchdog_seconds=args.watchdog_seconds,
        allow_apply_gated=args.allow_apply_gated,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
