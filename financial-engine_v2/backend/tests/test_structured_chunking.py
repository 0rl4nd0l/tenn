from __future__ import annotations

from app.services.structured_chunking import chunk_commentary_text


def test_chunk_commentary_text_preserves_line_boundaries() -> None:
    transcript = "\n".join(
        f"Segment {index} discusses market risk and price action."
        for index in range(1, 80)
    )

    chunks = chunk_commentary_text(transcript, max_chars=320, min_chars=180)

    assert len(chunks) > 1
    assert all(chunk.startswith("Segment ") for chunk in chunks)
    assert all(len(chunk) <= 320 for chunk in chunks)


def test_chunk_commentary_text_splits_long_unit_on_words() -> None:
    transcript = " ".join(f"word{index}" for index in range(120))

    chunks = chunk_commentary_text(transcript, max_chars=120, min_chars=60)

    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)
    assert all(not chunk.startswith(" ") and not chunk.endswith(" ") for chunk in chunks)
    assert "word1" in chunks[0]


def test_chunk_commentary_text_returns_empty_for_blank_input() -> None:
    assert chunk_commentary_text(" \n \t ") == []
