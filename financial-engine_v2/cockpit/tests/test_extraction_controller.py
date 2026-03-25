"""Tests for ExtractionController — validation gateway between agent and extraction pipeline."""
from __future__ import annotations

import pytest
from cockpit.core.agent.extraction_controller import ExtractionController, ExtractionRequest


def test_valid_request_is_accepted():
    ctrl = ExtractionController(pipeline_fn=lambda doc_id, ticker: "job-123")
    job_id = ctrl.submit(document_id="doc-abc", ticker="BHP")
    assert job_id == "job-123"


def test_free_text_in_document_id_is_rejected():
    ctrl = ExtractionController(pipeline_fn=lambda *a: "x")
    with pytest.raises(ValueError, match="document_id"):
        ctrl.submit(document_id="Please extract revenue from...", ticker="BHP")


def test_invalid_ticker_is_rejected():
    ctrl = ExtractionController(pipeline_fn=lambda *a: "x")
    with pytest.raises(ValueError, match="ticker"):
        ctrl.submit(document_id="doc-abc", ticker="")


def test_duplicate_hash_is_skipped():
    calls = []

    def fn(doc_id, ticker):
        calls.append(doc_id)
        return "job-x"

    ctrl = ExtractionController(pipeline_fn=fn)
    ctrl.submit("doc-abc", "BHP")
    ctrl.submit("doc-abc", "BHP")  # duplicate
    assert len(calls) == 1


def test_rate_limit_blocks_excess_jobs():
    ctrl = ExtractionController(pipeline_fn=lambda *a: "job", max_concurrent=2)
    ctrl._active_jobs.add("job-1")
    ctrl._active_jobs.add("job-2")
    with pytest.raises(RuntimeError, match="rate limit"):
        ctrl.submit("doc-new", "CSL")


def test_extraction_request_dataclass():
    r = ExtractionRequest(document_id="doc-x", ticker="CSL")
    assert r.document_id == "doc-x"
    assert r.ticker == "CSL"
