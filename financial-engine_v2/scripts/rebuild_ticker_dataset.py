#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebuild ticker dataset from local documents.")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--since", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--with-embeddings", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "rebuild_ticker_financials_from_docs_report.json"),
    )
    args = ap.parse_args()

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "rebuild_ticker_financials_from_docs.py"),
        "--ticker",
        str(args.ticker).strip().upper(),
        "--limit",
        str(int(args.limit)),
        "--report",
        str(Path(args.report).expanduser()),
    ]
    if str(args.since).strip():
        cmd.extend(["--since", str(args.since).strip()])
    if args.force:
        cmd.append("--force")
    if args.with_embeddings:
        cmd.append("--with-embeddings")
    if args.dry_run:
        cmd.append("--dry-run")

    cp = subprocess.run(cmd)
    return int(cp.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
