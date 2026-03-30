from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BLOCKED_PREFIX = "blocked_"


def _fetch_verification_from_backend(backend_api_client, ticker: str | None) -> tuple[list, list, list] | None:
    """Try loading verification data from backend API. Returns (docs, failures, low_conf) or None."""
    if not backend_api_client:
        return None
    try:
        docs = []
        if ticker:
            ctx = backend_api_client.get_ticker_context(ticker, docs_limit=500)
            docs = ctx.get("docs", [])
        verif = backend_api_client.get_verification_context(
            ticker=ticker,
            failures_limit=100,
            low_confidence_limit=100,
        )
        return docs, verif.get("extraction_failures", []), verif.get("low_confidence_financials", [])
    except Exception as exc:
        logger.warning("Backend verification fetch failed, falling back to DbReader: %s", exc)
        return None


def run_verification(db_reader, ticker: str | None = None, *, backend_api_client=None) -> dict[str, Any]:
    tick = ticker.upper() if ticker else None

    backend_data = _fetch_verification_from_backend(backend_api_client, tick)
    if backend_data is not None:
        docs, extraction_failures, low_confidence = backend_data
    else:
        docs = db_reader.get_docs(tick, limit=500) if tick else []
        extraction_failures = db_reader.get_extraction_failures(limit=100)
        low_confidence = db_reader.get_low_confidence_financials(limit=100)

    missing_files: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []

    for row in docs:
        marker = (row.get("pdf_sha256") or "").strip()
        if marker.startswith(BLOCKED_PREFIX):
            blocked.append(row)
        elif not marker:
            pending.append(row)

        path = row.get("pdf_path")
        if path and marker and not marker.startswith(BLOCKED_PREFIX):
            if not Path(path).exists():
                missing_files.append(row)

    remediation = []
    if pending:
        remediation.append("Run resume_pending for this ticker.")
    if blocked:
        remediation.append("Run recover_headed to recover blocked MarketIndex downloads.")
    if extraction_failures:
        remediation.append("Re-run with process_documents=true or inspect model/OLLAMA status.")
    if low_confidence:
        remediation.append("Review low confidence rows and source docs before downstream use.")

    return {
        "ticker": tick,
        "checks": {
            "missing_pdf_files": len(missing_files),
            "blocked_documents": len(blocked),
            "pending_downloads": len(pending),
            "extraction_failures": len(extraction_failures),
            "low_confidence_financials": len(low_confidence),
        },
        "samples": {
            "missing_pdf_files": missing_files[:10],
            "blocked_documents": blocked[:10],
            "pending_downloads": pending[:10],
            "extraction_failures": extraction_failures[:10],
            "low_confidence_financials": low_confidence[:10],
        },
        "remediation": remediation,
    }
