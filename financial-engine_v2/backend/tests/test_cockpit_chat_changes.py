"""Tests for Cockpit ChatController changes: greeting detection, follow-up RE,
_detect_ticker, action ticker validation, and system prompt content."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure the cockpit package is importable.
FE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FE_ROOT))

from cockpit.core.chat import ChatController
from cockpit.core.actions import ActionRegistry
from cockpit.core.types import ActionSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def chat_controller():
    """Minimal ChatController with mocked dependencies."""
    ctrl = ChatController(
        ollama_client=MagicMock(),
        tool_router=MagicMock(),
        action_registry=MagicMock(),
    )
    return ctrl


@pytest.fixture()
def action_registry(tmp_path):
    return ActionRegistry(repo_root=tmp_path)


# ---------------------------------------------------------------------------
# 1. Greeting detection
# ---------------------------------------------------------------------------

class TestGreetingRegex:
    """_GREETING_RE should match pure greetings and reject non-greetings."""

    SHOULD_MATCH = [
        "hi",
        "hello",
        "hey",
        "g'day",
        "good morning",
        "what's up",
        "yo!",
        "  Hi  ",
        "Hello!",
        "GOOD MORNING",
        "sup",
        "howdy",
        "good afternoon",
        "good evening",
        "whats up",
    ]

    SHOULD_NOT_MATCH = [
        "hi there tell me about bhp",
        "history",
        "hit me with the news",
        "hello how is CSL doing",
        "hey what's the BHP price",
        "good morning can you check FMG",
    ]

    @pytest.mark.parametrize("text", SHOULD_MATCH)
    def test_greeting_matches(self, text):
        assert ChatController._GREETING_RE.match(text), f"Expected match for: {text!r}"

    @pytest.mark.parametrize("text", SHOULD_NOT_MATCH)
    def test_non_greeting_does_not_match(self, text):
        assert not ChatController._GREETING_RE.match(text), f"Should NOT match: {text!r}"


# ---------------------------------------------------------------------------
# 2. Follow-up ticker detection
# ---------------------------------------------------------------------------

class TestFollowUpRegex:
    """_FOLLOW_UP_RE matches pronoun/reference follow-ups but not fresh queries."""

    SHOULD_MATCH = [
        "what about their cashflow?",
        "how is it performing?",
        "tell me more about the company",
        "is the stock overvalued?",
        # Natural conversational follow-ups (previously missed).
        "sure tell me about 2024-2025 financial health",
        "okay",
        "yes",
        "go ahead",
        "tell me more",
        "elaborate on the revenue",
        "how about the earnings?",
        "and what about dividends?",
        "continue",
        "what about their financials?",
        "more detail please",
    ]

    SHOULD_NOT_MATCH = [
        "tell me about CSL",
        "bhp price",
        "show me FMG chart",
    ]

    @pytest.mark.parametrize("text", SHOULD_MATCH)
    def test_followup_matches(self, text):
        assert ChatController._FOLLOW_UP_RE.search(text), f"Expected match for: {text!r}"

    @pytest.mark.parametrize("text", SHOULD_NOT_MATCH)
    def test_fresh_query_does_not_match(self, text):
        assert not ChatController._FOLLOW_UP_RE.search(text), f"Should NOT match: {text!r}"


class TestTickerInheritance:
    """Prior ticker carries forward when no new ticker is detected."""

    def test_inherits_prior_on_followup(self, chat_controller):
        """'sure tell me about 2024-2025 financial health' should not lose BHP."""
        chat_controller.last_ticker = "BHP"
        # _detect_ticker with no prior should find no new ticker here.
        new = chat_controller._detect_ticker("sure tell me about 2024-2025 financial health", prior_ticker=None)
        assert new is None, "Should not detect a new ticker in this message"

    def test_inherits_prior_on_okay(self, chat_controller):
        """'okay' should not be detected as a ticker."""
        chat_controller.last_ticker = "BHP"
        new = chat_controller._detect_ticker("okay", prior_ticker=None)
        assert new is None

    def test_new_ticker_overrides_prior(self, chat_controller):
        """Explicit new ticker should override the prior."""
        chat_controller.last_ticker = "BHP"
        new = chat_controller._detect_ticker("what about CSL?", prior_ticker=None)
        assert new == "CSL"

    def test_stopword_only_message_returns_none(self, chat_controller):
        """All-stopword messages return None (no new ticker)."""
        new = chat_controller._detect_ticker("sure tell me more about the latest", prior_ticker=None)
        assert new is None


# ---------------------------------------------------------------------------
# 3. _detect_ticker with no prior
# ---------------------------------------------------------------------------

class TestDetectTicker:

    def test_detects_explicit_ticker(self, chat_controller):
        result = chat_controller._detect_ticker("tell me about CSL", prior_ticker=None)
        assert result == "CSL"

    def test_returns_none_for_greeting(self, chat_controller):
        result = chat_controller._detect_ticker("hi", prior_ticker=None)
        assert result is None

    def test_returns_prior_when_no_tokens(self, chat_controller):
        # A message with no alpha tokens at all returns the prior.
        result = chat_controller._detect_ticker("123 456", prior_ticker="BHP")
        assert result == "BHP"

    def test_dollar_prefix(self, chat_controller):
        result = chat_controller._detect_ticker("what about $FMG?", prior_ticker=None)
        assert result == "FMG"

    def test_asx_prefix(self, chat_controller):
        result = chat_controller._detect_ticker("check ASX:WBC", prior_ticker=None)
        assert result == "WBC"


# ---------------------------------------------------------------------------
# 4. Action ticker validation
# ---------------------------------------------------------------------------

class TestActionTickerValidation:

    def test_ticker_required_raises_for_backfill(self, action_registry):
        """single_ticker_announcement_backfill must raise ValueError without ticker."""
        with pytest.raises(ValueError, match="requires a ticker"):
            action_registry.build_command(
                "single_ticker_announcement_backfill", {}
            )

    def test_daily_news_ingest_no_ticker_ok(self, action_registry):
        """daily_news_ingest should NOT require a ticker."""
        # Should not raise — daily_news_ingest is market-wide.
        cmd = action_registry.build_command("daily_news_ingest", {})
        assert isinstance(cmd, list)


# ---------------------------------------------------------------------------
# 5. System prompt content
# ---------------------------------------------------------------------------

class TestSystemPrompt:

    def test_contains_conversational(self, chat_controller):
        result = chat_controller._build_system_instruction(
            mode="fast", ticker=None, local_payload={}
        )
        assert "conversational" in result.lower()

    def test_does_not_contain_old_persona(self, chat_controller):
        result = chat_controller._build_system_instruction(
            mode="fast", ticker=None, local_payload={}
        )
        assert "advanced ASX equity research analyst" not in result
