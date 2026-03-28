#!/usr/bin/env python3
"""List, approve, or reject staged hot-source commentary chunks (staging → Qdrant).

See docs/ops/commentary_staging_to_qdrant.md for the operator runbook.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_paths() -> None:
    fe_root = Path(__file__).resolve().parents[1]
    backend = fe_root / "backend"
    for p in (backend, fe_root):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)


def main() -> int:
    _bootstrap_paths()

    from cockpit.integrations.transcript_review import TranscriptReviewService

    parser = argparse.ArgumentParser(
        description="Promote staged commentary to Qdrant or reject pending staging."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="Print pending staged sources as JSON")
    p_list.add_argument(
        "--qdrant-url",
        default=None,
        help="Optional Qdrant base URL override (else backend config/env)",
    )

    p_app = sub.add_parser("approve", help="Upsert staged points to Qdrant and clear staging")
    p_app.add_argument("--source-id", required=True, help="Staged source_id from list")
    p_app.add_argument("--qdrant-url", default=None, help="Optional Qdrant base URL override")

    p_rej = sub.add_parser("reject", help="Discard staged file and index entry")
    p_rej.add_argument("--source-id", required=True, help="Staged source_id from list")

    args = parser.parse_args()
    svc = TranscriptReviewService()

    if args.cmd == "list":
        pending = svc.list_pending()
        print(json.dumps(pending, indent=2))
        return 0

    if args.cmd == "approve":
        result = svc.approve(args.source_id, qdrant_url=args.qdrant_url)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    if args.cmd == "reject":
        result = svc.reject(args.source_id)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
