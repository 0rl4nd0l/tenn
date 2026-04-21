#!/usr/bin/env python3
"""run_analysis_action.py — execute backend analysis endpoint for one ticker.

Usage:
    python scripts/run_analysis_action.py --ticker NST
    python scripts/run_analysis_action.py --ticker BHP --modules balance_sheet,valuation
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run backend analysis pipeline for a ticker and persist JSON artifact."
    )
    parser.add_argument("--ticker", required=True, help="ASX ticker, e.g. NST")
    parser.add_argument(
        "--modules",
        default="",
        help="Optional comma-separated module list",
    )
    parser.add_argument(
        "--backend-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=300.0,
        help="HTTP timeout in seconds (default: 300)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ticker = str(args.ticker or "").strip().upper()
    if not ticker:
        raise SystemExit("--ticker is required")

    backend_url = str(args.backend_url or "").strip().rstrip("/")
    if not backend_url:
        raise SystemExit("--backend-url is required")

    modules = str(args.modules or "").strip()
    headers: dict[str, str] = {}
    if settings.local_api_key:
        headers["X-API-Key"] = settings.local_api_key

    params: dict[str, str] = {}
    if modules:
        params["modules"] = modules

    url = f"{backend_url}/api/analysis/{ticker}"

    try:
        response = httpx.post(
            url,
            params=params,
            headers=headers,
            timeout=float(args.timeout_seconds),
        )
    except Exception as exc:  # pragma: no cover - network exceptions vary by env
        print(f"[run_analysis_action] FAILED ticker={ticker} error={exc}", flush=True)
        raise SystemExit(1) from exc

    if response.status_code >= 400:
        detail = response.text.strip()[:800]
        print(
            f"[run_analysis_action] FAILED ticker={ticker} http={response.status_code} detail={detail}",
            flush=True,
        )
        raise SystemExit(1)

    payload: dict[str, Any] = response.json() if response.content else {}

    out_dir = REPO_ROOT / "reports" / "analysis" / ticker
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"analysis_api_{_utc_stamp()}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    modules_run = int(payload.get("modules_run") or 0)
    print(
        f"[run_analysis_action] ok ticker={ticker} modules_run={modules_run} artifact={out_path}",
        flush=True,
    )
    print(json.dumps(payload), flush=True)


if __name__ == "__main__":
    main()
