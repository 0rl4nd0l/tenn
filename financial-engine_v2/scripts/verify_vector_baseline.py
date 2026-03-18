#!/usr/bin/env python3
"""
Verify current Qdrant vector count against the baseline written by rebuild_rag_qdrant_index.
Read-only: no writes to Qdrant or DB.
Exits with code 1 if the difference exceeds 5%.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from qdrant_client import QdrantClient

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402

BASELINE_PATH = REPO_ROOT / "reports" / "vector_baseline.json"
TOLERANCE_FRACTION = 0.05  # 5%


def main() -> int:
    if not BASELINE_PATH.exists():
        print(f"[verify_vector_baseline] Baseline not found: {BASELINE_PATH}", file=sys.stderr)
        return 1

    baseline_data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    baseline_count = baseline_data.get("vector_count")
    if baseline_count is None or not isinstance(baseline_count, (int, float)):
        print(
            f"[verify_vector_baseline] Invalid baseline: missing or non-numeric vector_count",
            file=sys.stderr,
        )
        return 1
    baseline_count = int(baseline_count)
    if baseline_count < 0:
        print(f"[verify_vector_baseline] Invalid baseline: vector_count < 0", file=sys.stderr)
        return 1

    client = QdrantClient(url=settings.qdrant_url)
    try:
        count_result = client.count(
            collection_name=settings.qdrant_collection,
            exact=True,
        )
        current_count = int(getattr(count_result, "count", 0))
    except Exception as exc:
        print(f"[verify_vector_baseline] Qdrant count failed: {exc}", file=sys.stderr)
        return 1

    diff = abs(current_count - baseline_count)
    if baseline_count == 0:
        allowed_diff = 0
        ok = current_count == 0
    else:
        allowed_diff = baseline_count * TOLERANCE_FRACTION
        ok = diff <= allowed_diff

    print(
        f"[verify_vector_baseline] baseline={baseline_count} current={current_count} "
        f"diff={diff} tolerance=±{TOLERANCE_FRACTION*100:.0f}% (max ±{int(allowed_diff)})",
        flush=True,
    )
    if not ok:
        print(
            f"[verify_vector_baseline] FAIL: difference {diff} exceeds {TOLERANCE_FRACTION*100:.0f}% of baseline",
            file=sys.stderr,
        )
        return 1
    print("[verify_vector_baseline] OK: within tolerance", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
