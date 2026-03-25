"""ExtractionController — validation gateway between agent tool calls and extraction pipeline.

The agent tool interface is strictly: metric_extraction(document_id, ticker) -> job_id.
No free-form prompts. No instructions. No direct pipeline access.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Callable, Set

_DOCUMENT_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")
_TICKER_RE = re.compile(r"^[A-Z0-9]{1,6}$")


@dataclass
class ExtractionRequest:
    """Validated extraction request parameters."""
    document_id: str
    ticker: str


class ExtractionController:
    """Validation gateway that enforces strict input constraints before calling the pipeline.

    Args:
        pipeline_fn: Callable accepting (document_id, ticker) and returning a job_id string.
        max_concurrent: Maximum number of simultaneously active jobs. Exceeding this raises
                        RuntimeError.
    """

    def __init__(self, pipeline_fn: Callable[[str, str], str], max_concurrent: int = 4) -> None:
        self._pipeline_fn = pipeline_fn
        self._max_concurrent = max_concurrent
        self._active_jobs: Set[str] = set()
        self._seen_hashes: Set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, document_id: str, ticker: str) -> str:
        """Validate inputs and submit an extraction job.

        Returns:
            job_id string from the pipeline, or "duplicate:skipped" if the
            document_id/ticker pair was already submitted.

        Raises:
            ValueError: If document_id or ticker fails validation.
            RuntimeError: If max_concurrent active jobs is already reached.
        """
        self._validate_document_id(document_id)
        self._validate_ticker(ticker)

        pair_hash = self._pair_hash(document_id, ticker)
        if pair_hash in self._seen_hashes:
            return "duplicate:skipped"

        if len(self._active_jobs) >= self._max_concurrent:
            raise RuntimeError(
                f"rate limit exceeded: {self._max_concurrent} concurrent jobs already active"
            )

        self._seen_hashes.add(pair_hash)
        job_id = self._pipeline_fn(document_id, ticker)
        self._active_jobs.add(job_id)
        return job_id

    def complete(self, job_id: str) -> None:
        """Mark a job as finished, freeing a concurrency slot."""
        self._active_jobs.discard(job_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_document_id(document_id: str) -> None:
        if not _DOCUMENT_ID_RE.match(document_id):
            raise ValueError(
                f"document_id must match ^[a-zA-Z0-9_\\-]{{1,128}}$, got: {document_id!r}"
            )

    @staticmethod
    def _validate_ticker(ticker: str) -> None:
        if not _TICKER_RE.match(ticker):
            raise ValueError(
                f"ticker must match ^[A-Z0-9]{{1,6}}$ (ASX format), got: {ticker!r}"
            )

    @staticmethod
    def _pair_hash(document_id: str, ticker: str) -> str:
        return hashlib.sha256(f"{document_id}:{ticker}".encode()).hexdigest()
