"""Tests for progress_parser — extracts structured stage info from action script output."""

from __future__ import annotations

import pytest

from app.services.progress_parser import ProgressInfo, parse_progress_line


class TestParseProgressLine:
    def test_ticker_index_line(self) -> None:
        line = "[progress] ticker_index=2/5 ticker=BHP"
        result = parse_progress_line(line)
        assert result == ProgressInfo(
            stage="progress",
            current=2,
            total=5,
            detail="ticker_index=2/5 ticker=BHP",
        )

    def test_ticker_index_first_of_one(self) -> None:
        line = "[progress] ticker_index=1/1 ticker=EOS"
        result = parse_progress_line(line)
        assert result is not None
        assert result.current == 1
        assert result.total == 1
        assert result.pct == pytest.approx(100.0)

    def test_backfill_done_line(self) -> None:
        line = "[backfill] BHP done found=12 inserted=8 processed=8 skipped=0 errors=0"
        result = parse_progress_line(line)
        assert result is not None
        assert result.stage == "backfill"
        assert result.detail.startswith("BHP done")

    def test_backfill_skipped_line(self) -> None:
        line = "[backfill] BHP skipped (already complete: 15 docs >= 10)"
        result = parse_progress_line(line)
        assert result is not None
        assert result.stage == "backfill"
        assert "skipped" in result.detail

    def test_backfill_failed_line(self) -> None:
        line = "[backfill] EOS failed: ConnectionError"
        result = parse_progress_line(line)
        assert result is not None
        assert result.stage == "backfill"

    def test_resume_line(self) -> None:
        line = "[resume] running: python resume_pending.py --ticker BHP"
        result = parse_progress_line(line)
        assert result is not None
        assert result.stage == "resume"

    def test_post_line(self) -> None:
        line = "[post] running: python audit_ticker_financials.py --ticker BHP"
        result = parse_progress_line(line)
        assert result is not None
        assert result.stage == "post"

    def test_unrecognized_line_returns_none(self) -> None:
        assert parse_progress_line("INFO: Starting backfill") is None
        assert parse_progress_line("") is None
        assert parse_progress_line("some random output") is None

    def test_malformed_progress_line_no_index(self) -> None:
        line = "[progress] ticker=BHP"
        result = parse_progress_line(line)
        assert result is not None
        assert result.stage == "progress"
        assert result.current is None
        assert result.total is None

    def test_pct_calculation(self) -> None:
        line = "[progress] ticker_index=3/10 ticker=CSL"
        result = parse_progress_line(line)
        assert result is not None
        assert result.pct == pytest.approx(30.0)

    def test_pct_zero_total_returns_none(self) -> None:
        line = "[progress] ticker_index=0/0 ticker=NONE"
        result = parse_progress_line(line)
        assert result is not None
        assert result.pct is None

    def test_whitespace_handling(self) -> None:
        line = "  [progress] ticker_index=1/3 ticker=BHP  \n"
        result = parse_progress_line(line)
        assert result is not None
        assert result.current == 1
