#!/usr/bin/env python3
"""Generate a deterministic extraction scorecard from synthetic fixtures."""

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

from app.services.extraction_eval import build_fixture_scorecard, load_fixtures


DEFAULT_FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent
    / "backend"
    / "tests"
    / "fixtures"
    / "extraction_eval"
)


def _coerce_payload_map(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("actual payload map must be a JSON object")

    payloads: dict[str, dict[str, Any]] = {}
    for fixture_id, payload in data.items():
        if not isinstance(payload, dict):
            raise ValueError(
                f"payload for fixture '{fixture_id}' must be an object, got {type(payload)}"
            )
        payloads[str(fixture_id)] = payload
    return payloads


def _build_default_payloads(fixtures_dir: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for fixture in load_fixtures(fixtures_dir):
        payload: dict[str, Any] = {
            "period_end": fixture.context.period_end,
            "period_type": fixture.context.period_type,
            "currency": fixture.context.currency,
            "scale": fixture.context.scale,
            "metrics": {**fixture.metrics},
        }
        payloads[fixture.fixture_id] = payload
    return _inject_failure_modes(payloads)


def _inject_failure_modes(
    payloads: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Inject deterministic negative cases for scorecard coverage.

    Keep this deterministic so the scorecard baseline exercises wrong values,
    missing required metrics, and quarantine behavior without extra config.
    """

    if "wrong_value" in payloads:
        payloads["wrong_value"]["metrics"]["revenue"] = 1_200_000

    if "missing_metric" in payloads:
        payloads["missing_metric"]["metrics"] = {}

    if "scoring_mix" in payloads:
        payloads["scoring_mix"]["metrics"] = {
            "revenue": 1_000_000,
            "ebit": 50_000,
            "net_debt": 2_000,
        }

    if "context_mismatch" in payloads:
        payloads["context_mismatch"]["currency"] = "AUD"

    if "period_mismatch" in payloads:
        payloads["period_mismatch"]["period_end"] = "2024-12-31"

    if "scale_mismatch" in payloads:
        payloads["scale_mismatch"]["scale"] = "thousands"

    if "currency_mismatch" in payloads:
        payloads["currency_mismatch"]["currency"] = "AUD"

    if "quarantine_context_conflict" in payloads:
        payloads["quarantine_context_conflict"]["currency"] = "AUD"

    if "mixed_status" in payloads:
        payloads["mixed_status"]["metrics"] = {
            "revenue": 2_000_000,
            "ebit": 100_000,
            "net_debt": 500_000,
            "shares_outstanding": 4_500_000,
        }

    if "shares_fallback_disagreement" in payloads:
        payloads["shares_fallback_disagreement"]["metrics"]["shares_outstanding"] = (
            4_500_000
        )

    if "statutory_underlying_wrong_value" in payloads:
        payloads["statutory_underlying_wrong_value"]["metrics"]["np_attributable"] = (
            60_000
        )

    if "wrong_current_period_column" in payloads:
        payloads["wrong_current_period_column"]["metrics"]["revenue"] = 900_000

    return payloads


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic extraction scorecard from synthetic fixtures.",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=DEFAULT_FIXTURES_DIR,
        help="Directory containing extraction eval fixture JSON files.",
    )
    parser.add_argument(
        "--actuals-json",
        type=Path,
        default=None,
        help=(
            "Optional JSON mapping of fixture_id -> extracted payload."
            " If omitted, a deterministic injected-variation payload set is used "
            "to exercise negative-path scorecard behavior."
        ),
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation for stdout output (0 = compact)",
    )
    return parser.parse_args()


def _default_or_actual_payloads(
    fixtures_dir: Path,
    actuals_json: Path | None,
) -> dict[str, dict[str, Any]]:
    if actuals_json is None:
        return _build_default_payloads(fixtures_dir)
    return _coerce_payload_map(actuals_json)


def main() -> int:
    args = _parse_args()
    fixtures_dir = args.fixtures_dir
    payloads = _default_or_actual_payloads(fixtures_dir, args.actuals_json)
    scorecard = build_fixture_scorecard(fixtures_dir, payloads)

    indent = None if args.indent <= 0 else args.indent
    print(json.dumps(scorecard, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
