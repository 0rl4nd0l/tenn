#!/usr/bin/env python3
"""Build a provisional exhaustive projection diagnostic artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.exhaustive_projection_diagnostic import (
    build_exhaustive_projection_diagnostic,
    load_canonical_family_presence,
    load_exhaustive_audit_summary,
    load_exhaustive_datapoints,
    write_exhaustive_projection_artifacts,
)


DEFAULT_EXHAUSTIVE_JSONL = (
    REPO_ROOT
    / "docs"
    / "extraction_gold_real_exhaustive_run"
    / "all_exhaustive_datapoints.jsonl"
)
DEFAULT_EXHAUSTIVE_AUDIT = (
    REPO_ROOT
    / "docs"
    / "extraction_gold_real_exhaustive_run"
    / "gold_corpus_exhaustive_audit_summary.json"
)
DEFAULT_CANONICAL_FIXTURES = (
    REPO_ROOT / "financial-engine_v2" / "data" / "extraction_gold_real"
)
DEFAULT_OUT_DIR = (
    REPO_ROOT / "reports" / "exhaustive_eval" / "projection_diagnostic_latest"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a read-only diagnostic projection scorecard from the "
            "existing exhaustive real-gold corpus."
        )
    )
    parser.add_argument(
        "--exhaustive-jsonl",
        type=Path,
        default=DEFAULT_EXHAUSTIVE_JSONL,
        help="Path to all_exhaustive_datapoints.jsonl.",
    )
    parser.add_argument(
        "--audit-summary-json",
        type=Path,
        default=DEFAULT_EXHAUSTIVE_AUDIT,
        help="Path to gold_corpus_exhaustive_audit_summary.json.",
    )
    parser.add_argument(
        "--canonical-fixtures-dir",
        type=Path,
        default=DEFAULT_CANONICAL_FIXTURES,
        help="Canonical real-gold fixture directory for coarse family comparison.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for diagnostic artifacts.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=25,
        help="Maximum suspicious-case samples to retain per bucket.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    datapoints = load_exhaustive_datapoints(args.exhaustive_jsonl)
    audit_summary = load_exhaustive_audit_summary(args.audit_summary_json)
    canonical_presence = load_canonical_family_presence(args.canonical_fixtures_dir)

    scorecard = build_exhaustive_projection_diagnostic(
        datapoints,
        canonical_family_presence_by_document=canonical_presence,
        exhaustive_audit_summary=audit_summary,
        sample_limit=max(int(args.sample_limit), 1),
    )
    artifact_paths = write_exhaustive_projection_artifacts(scorecard, args.out_dir)

    print("Exhaustive projection diagnostic written:")
    for name, path in sorted(artifact_paths.items()):
        print(f"- {name}: {path}")
    print("- canonical release gate: canonical real-gold scoring only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
