#!/usr/bin/env python3
"""
One-command production runner.

Usage:
  python3 run.py

Edit the hardcoded CONFIG values below to control what runs.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent

# Hardcoded runtime profile.
CONFIG = {
    # "both" | "full_history" | "daily_marketindex"
    "workflow": "both",

    # Full-history ticker gathering config
    "full_history": {
        "use_asx10": False,
        "tickers": ["BHP"],
        "years": 10,
        "process_documents": False,
        "max_backfill_retries": 3,
        "resume_max_retries": 5,
        "resume_retry_delay_seconds": 2.0,
    },

    # Daily MarketIndex config
    "daily_marketindex": {
        "download_limit": 0,
        "overwrite_pdfs": False,
        "min_download_count": 5,
        "min_success_ratio": 0.35,
        "null_retry_delay_seconds": 15,
    },
}


def _set_default_env() -> dict:
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "sqlite:///./data/fe_local.db")
    env.setdefault("TASK_MODE", "sync")
    env.setdefault("AUTO_CREATE_TABLES", "true")
    env.setdefault("ENABLE_EMBEDDINGS", "false")
    env.setdefault("ENABLE_QDRANT", "false")
    env.setdefault("ENABLE_EXTRACTION", "false")
    env.setdefault("ENABLE_MARKETINDEX_FALLBACK", "true")
    env.setdefault("MARKETINDEX_ANNOUNCEMENTS_FILE", "../data/raw/marketindex_announcements.json")
    return env


def _run_step(name: str, cmd: list[str], env: dict) -> int:
    print(f"\n[{name}] {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, check=False)
    print(f"[{name}] exit_code={completed.returncode}")
    return completed.returncode


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _build_full_history_cmd() -> list[str]:
    cfg = CONFIG["full_history"]
    cmd = [
        sys.executable,
        "scripts/full_history_ticker_sync.py",
        "--years",
        str(cfg["years"]),
        "--max-backfill-retries",
        str(cfg["max_backfill_retries"]),
        "--resume-max-retries",
        str(cfg["resume_max_retries"]),
        "--resume-retry-delay-seconds",
        str(cfg["resume_retry_delay_seconds"]),
        "--report",
        f"reports/full_history_run_{_timestamp()}.json",
    ]
    if cfg.get("process_documents"):
        cmd.append("--process-documents")
    if cfg.get("use_asx10"):
        cmd.append("--asx10")
    else:
        tickers = [t.strip().upper() for t in cfg.get("tickers", []) if str(t).strip()]
        if not tickers:
            raise ValueError("CONFIG.full_history.tickers cannot be empty when use_asx10=false")
        cmd.extend(["--ticker", ",".join(tickers)])
    return cmd


def _build_daily_cmd() -> list[str]:
    cfg = CONFIG["daily_marketindex"]
    cmd = [
        sys.executable,
        "scripts/daily_marketindex_action.py",
        "--download-limit",
        str(cfg["download_limit"]),
        "--min-download-count",
        str(cfg["min_download_count"]),
        "--min-success-ratio",
        str(cfg["min_success_ratio"]),
        "--null-retry-delay-seconds",
        str(cfg["null_retry_delay_seconds"]),
        "--daily-report",
        f"reports/marketindex/daily_marketindex_action_report_{_timestamp()}.json",
        "--download-report",
        f"reports/marketindex/pdf_download_report_{_timestamp()}.json",
    ]
    if cfg.get("overwrite_pdfs"):
        cmd.append("--overwrite-pdfs")
    return cmd


def main() -> int:
    workflow = str(CONFIG.get("workflow", "both")).strip().lower()
    env = _set_default_env()

    if workflow not in {"both", "full_history", "daily_marketindex"}:
        raise ValueError("CONFIG.workflow must be one of: both, full_history, daily_marketindex")

    results = []
    if workflow in {"both", "full_history"}:
        results.append(_run_step("full_history", _build_full_history_cmd(), env))
    if workflow in {"both", "daily_marketindex"}:
        results.append(_run_step("daily_marketindex", _build_daily_cmd(), env))

    # Fail overall if any step failed.
    return 0 if all(code == 0 for code in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
