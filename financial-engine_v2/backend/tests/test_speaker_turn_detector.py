"""Tests for speaker_turn_detector — regex-based transcript speaker detection."""
from __future__ import annotations

import pytest

from app.services.speaker_turn_detector import (
    annotate_chunks_with_speakers,
    detect_speaker_turns,
)


# ---------------------------------------------------------------------------
# detect_speaker_turns
# ---------------------------------------------------------------------------

class TestDetectSpeakerTurns:
    def test_operator_pattern(self) -> None:
        text = "Operator: Welcome to the call.\nThank you for joining."
        turns = detect_speaker_turns(text)
        assert len(turns) == 1
        assert turns[0]["speaker"] == "Operator"
        assert turns[0]["role"] is None
        assert turns[0]["offset"] == 0

    def test_moderator_pattern(self) -> None:
        text = "Moderator: We will now begin Q&A."
        turns = detect_speaker_turns(text)
        assert len(turns) == 1
        assert turns[0]["speaker"] == "Moderator"

    def test_name_role_pattern(self) -> None:
        text = "John Smith - CEO: Good morning everyone."
        turns = detect_speaker_turns(text)
        assert len(turns) == 1
        assert turns[0]["speaker"] == "John Smith"
        assert turns[0]["role"] == "CEO"

    def test_name_role_long_title(self) -> None:
        text = "Jane Doe - Chief Financial Officer: Revenue increased."
        turns = detect_speaker_turns(text)
        assert len(turns) == 1
        assert turns[0]["speaker"] == "Jane Doe"
        assert turns[0]["role"] == "Chief Financial Officer"

    def test_qa_patterns(self) -> None:
        text = "Q: What is the outlook?\nA: We expect growth."
        turns = detect_speaker_turns(text)
        assert len(turns) == 2
        assert turns[0]["speaker"] == "Q"
        assert turns[1]["speaker"] == "A"

    def test_question_answer_long_form(self) -> None:
        text = "Question: Can you elaborate?\nAnswer: Yes, certainly."
        turns = detect_speaker_turns(text)
        assert len(turns) == 2
        assert turns[0]["speaker"] == "Question"
        assert turns[1]["speaker"] == "Answer"

    def test_generic_name_pattern(self) -> None:
        text = "David Johnson: I have a question about margins."
        turns = detect_speaker_turns(text)
        assert len(turns) == 1
        assert turns[0]["speaker"] == "David Johnson"
        assert turns[0]["role"] is None

    def test_multiple_speakers(self) -> None:
        text = (
            "Operator: Welcome.\n"
            "John Smith - CEO: Thank you operator.\n"
            "Q: What about revenue?\n"
            "John Smith - CEO: Revenue grew 15%.\n"
        )
        turns = detect_speaker_turns(text)
        assert len(turns) == 4
        speakers = [t["speaker"] for t in turns]
        assert speakers == ["Operator", "John Smith", "Q", "John Smith"]

    def test_no_speakers(self) -> None:
        text = "This is just plain text with no speaker markers at all."
        turns = detect_speaker_turns(text)
        assert turns == []

    def test_empty_text(self) -> None:
        assert detect_speaker_turns("") == []

    def test_mid_line_colon_not_matched(self) -> None:
        """Colons mid-line (e.g. 'revenue: $5M') should not trigger detection."""
        text = "The revenue: $5M was higher than expected."
        turns = detect_speaker_turns(text)
        assert turns == []


# ---------------------------------------------------------------------------
# annotate_chunks_with_speakers
# ---------------------------------------------------------------------------

class TestAnnotateChunksWithSpeakers:
    def test_single_speaker_chunk(self) -> None:
        text = "John Smith - CEO: We had a great quarter with record revenue."
        chunks = ["We had a great quarter with record revenue."]
        result = annotate_chunks_with_speakers(chunks, text)
        assert len(result) == 1
        assert result[0]["primary_speaker"] == "John Smith"
        assert "John Smith" in result[0]["speakers"]

    def test_multiple_speakers_in_chunk(self) -> None:
        text = (
            "Q: What is the outlook?\n"
            "A: We expect strong growth in H2."
        )
        # Single chunk covering the full text
        chunks = [text]
        result = annotate_chunks_with_speakers(chunks, text)
        assert len(result) == 1
        assert "Q" in result[0]["speakers"]
        assert "A" in result[0]["speakers"]

    def test_primary_speaker_is_longest(self) -> None:
        # "A" has much more text than "Q"
        text = (
            "Q: Why?\n"
            "A: Because our strategy focused on long-term sustainable growth "
            "across multiple segments and we invested heavily in R&D."
        )
        chunks = [text]
        result = annotate_chunks_with_speakers(chunks, text)
        assert result[0]["primary_speaker"] == "A"

    def test_no_speakers_returns_none(self) -> None:
        text = "Plain text without any speaker markers."
        chunks = ["Plain text without any speaker markers."]
        result = annotate_chunks_with_speakers(chunks, text)
        assert len(result) == 1
        assert result[0]["speakers"] == []
        assert result[0]["primary_speaker"] is None

    def test_empty_chunks(self) -> None:
        result = annotate_chunks_with_speakers([], "Some text.")
        assert result == []

    def test_speaker_carries_over_to_next_chunk(self) -> None:
        text = (
            "John Smith - CEO: First part of speech. "
            "More content here that continues for a while."
        )
        # Split into two chunks
        chunks = [
            "John Smith - CEO: First part of speech.",
            "More content here that continues for a while.",
        ]
        result = annotate_chunks_with_speakers(chunks, text)
        # Second chunk should inherit John Smith as speaker
        assert result[1]["primary_speaker"] == "John Smith"
