#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest and sync one ticker's announcement/doc pipeline.")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--process-documents", action="store_true")
    ap.add_argument("--no-process-documents", action="store_true")
    ap.add_argument("--report", default=str(REPO_ROOT / "reports" / "financial_update_report.json"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "update_ticker_financials.py"),
        "--ticker",
        str(args.ticker).strip().upper(),
        "--years",
        str(int(args.years)),
        "--report",
        str(Path(args.report).expanduser()),
    ]
    if args.process_documents and not args.no_process_documents:
        cmd.append("--process-documents")
    if args.no_process_documents:
        cmd.append("--no-process-documents")
    if args.dry_run:
        cmd.append("--dry-run")

    cp = subprocess.run(cmd)
    return int(cp.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
