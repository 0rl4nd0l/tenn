#!/usr/bin/env python3
"""run_analysis.py — CLI entrypoint for per-ticker LLM analysis reports.

Usage:
    python scripts/run_analysis.py --ticker BHP
    python scripts/run_analysis.py --ticker CBA --period-type H --max-periods 3

Writes:
    reports/analysis/<TICKER>/analysis_<timestamp>.json

Exit codes:
    0 — report generated and validated
    1 — LLM call failed, validation failed, or no DB data found
"""
from __future__ import annotations

import argparse
import json
import logging
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
from app.core.db import SessionLocal  # noqa: E402
from app.services.analysis.context_assembler import assemble  # noqa: E402
from app.services.analysis.report_generator import generate  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("run_analysis")


# ---------------------------------------------------------------------------
# Thin LLM client — plain chat completion, returns raw string
# ---------------------------------------------------------------------------

class LlamaCppChatClient:
    """Minimal chat client for llama.cpp /v1/chat/completions."""

    def __init__(self, base_url: str, model: str = "local", api_key: str = "") -> None:
        self._url = base_url.rstrip("/") + "/v1/chat/completions"
        self._model = model
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def chat(self, prompt: str, *, timeout: float = 120.0) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1024,
        }
        resp = httpx.post(self._url, json=payload, headers=self._headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an LLM-driven analysis report for one ASX ticker."
    )
    parser.add_argument("--ticker", required=True, help="ASX ticker, e.g. BHP.")
    parser.add_argument(
        "--period-type",
        default="A",
        choices=["A", "H", "Q"],
        help="Period type to use for financial metrics (default: A = annual).",
    )
    parser.add_argument(
        "--max-periods",
        type=int,
        default=5,
        help="Number of historical periods to include (default: 5).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="LLM call timeout in seconds (default: 120).",
    )
    parser.add_argument(
        "--llm-url",
        default=None,
        help="llama.cpp base URL (default: LLAMACPP_URL from config).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "reports" / "analysis"),
        help="Directory to write report JSON files.",
    )
    return parser.parse_args()


def _utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> None:
    args = parse_args()
    ticker = args.ticker.strip().upper()
    if not ticker:
        raise SystemExit("--ticker is required")

    llm_url = args.llm_url or settings.llamacpp_url
    llm_client = LlamaCppChatClient(base_url=llm_url, api_key=settings.local_api_key)

    logger.info("run_analysis ticker=%s period_type=%s max_periods=%s llm_url=%s",
                ticker, args.period_type, args.max_periods, llm_url)

    # --- Assemble context from DB ---
    db = SessionLocal()
    try:
        context = assemble(
            ticker,
            db,
            period_type=args.period_type,
            max_periods=args.max_periods,
        )
    finally:
        db.close()

    period_count = (context.get("metrics") or {}).get("period_count", 0)
    warnings = context.get("warnings") or []
    logger.info("context assembled: periods=%s warnings=%s", period_count, warnings)

    if period_count == 0:
        logger.error("No financial periods found for %s — cannot generate report.", ticker)
        for w in warnings:
            logger.warning("  %s", w)
        raise SystemExit(1)

    # --- Generate report via LLM ---
    result = generate(context, llm_client, timeout=args.timeout)

    # --- Write artifact ---
    timestamp = _utc_now_str()
    out_dir = Path(args.output_dir) / ticker
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"analysis_{timestamp}.json"

    artifact: dict[str, Any] = {
        "run_metadata": {
            "script": "scripts/run_analysis.py",
            "ticker": ticker,
            "period_type": args.period_type,
            "max_periods": args.max_periods,
            "llm_url": llm_url,
            "generated_at": timestamp,
            "ok": result["ok"],
        },
        "context_warnings": warnings,
        "metrics_summary": context.get("metrics"),
        "report": result.get("report"),
        "validation": result.get("validation"),
        "raw_response": result.get("raw_response"),
        "error": result.get("error"),
    }
    out_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")

    if result["ok"]:
        report = result["report"] or {}
        logger.info(
            "report generated: health_score=%s action=%s sentiment=%s path=%s",
            report.get("financial_health_score"),
            report.get("action_label"),
            report.get("news_sentiment_score"),
            out_path,
        )
        print(
            f"[run_analysis] ok ticker={ticker} "
            f"health={report.get('financial_health_score')} "
            f"action={report.get('action_label')} "
            f"report={out_path}",
            flush=True,
        )
    else:
        logger.error("report generation failed: %s", result.get("error"))
        print(
            f"[run_analysis] FAILED ticker={ticker} error={result.get('error')} "
            f"artifact={out_path}",
            flush=True,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
