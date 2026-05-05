#!/usr/bin/env python3
"""Build read-only extraction scorecard profile JSON artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FINANCIAL_ENGINE_ROOT = REPO_ROOT / "financial-engine_v2"
BACKEND_ROOT = FINANCIAL_ENGINE_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.extraction_gold_eval import build_real_gold_scorecard
from app.services.extraction_gold_eval_scorecard import (
    CANONICAL_CORE_DOC_IDS,
    build_confirmed_metric_coverage_scorecard,
    get_scorecard_profiles,
)


DEFAULT_FIXTURES_DIR = FINANCIAL_ENGINE_ROOT / "data" / "extraction_gold_real"
DEFAULT_COVERAGE_FIXTURES_DIR = BACKEND_ROOT / "tests" / "eval_fixtures"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only extraction scorecard profile artifact.",
    )
    parser.add_argument(
        "--profile",
        choices=["canonical_core", "expanded_required", "confirmed_metric_coverage"],
        default="expanded_required",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=None,
        help="Fixture directory override for the selected profile.",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "reports" / "extraction_gold_eval_scorecard.json",
    )
    return parser.parse_args()


def _build_profile(profile: str, fixtures_dir: Path | None) -> dict:
    profiles = get_scorecard_profiles()
    if profile == "confirmed_metric_coverage":
        return build_confirmed_metric_coverage_scorecard(
            fixtures_dir or DEFAULT_COVERAGE_FIXTURES_DIR,
            financial_engine_root=FINANCIAL_ENGINE_ROOT,
        )

    dataset_dir = fixtures_dir or DEFAULT_FIXTURES_DIR
    scorecard = (
        _build_canonical_core_scorecard(dataset_dir)
        if profile == "canonical_core"
        else build_real_gold_scorecard(dataset_dir)
    )
    return {
        "profile": profile,
        "profile_definition": profiles[profile],
        "scorecard": scorecard,
    }


def _build_canonical_core_scorecard(dataset_dir: Path) -> dict:
    files_by_document_id: dict[str, Path] = {}
    for path in sorted(dataset_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            files_by_document_id[str(payload.get("document_id") or path.stem)] = path

    missing = [
        document_id
        for document_id in CANONICAL_CORE_DOC_IDS
        if document_id not in files_by_document_id
    ]
    if missing:
        raise ValueError(f"canonical_core fixture(s) missing: {', '.join(missing)}")

    with tempfile.TemporaryDirectory(prefix="tenn-canonical-core-") as tmp:
        tmp_dir = Path(tmp)
        for document_id in CANONICAL_CORE_DOC_IDS:
            source = files_by_document_id[document_id]
            shutil.copy2(source, tmp_dir / source.name)
        return build_real_gold_scorecard(tmp_dir)


def main() -> int:
    args = _parse_args()
    payload = _build_profile(args.profile, args.fixtures_dir)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote scorecard profile JSON: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
