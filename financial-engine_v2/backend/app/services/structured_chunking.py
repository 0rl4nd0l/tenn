"""
structured_chunking.py — Prose-section chunking for Qdrant embedding.

Tables are excluded — they go to the metric extraction path.
Only non-table text sections are chunked here.
"""
from __future__ import annotations

import re

from app.services.docling_extract import StructuredDocument

MAX_CHARS = 2000  # nomic-embed-text context is 2048 tokens; ~2000 chars fits safely
OVERLAP_CHARS = 150


def chunk_prose_sections(doc: StructuredDocument, max_chars: int = MAX_CHARS) -> list[str]:
    """
    Returns a list of text chunks from the document's prose sections.
    Tables are excluded. Chunks respect max_chars with simple overlap.
    """
    prose = " ".join(
        s["text"] for s in doc.sections
        if s.get("text", "").strip()
    ).strip()

    if not prose:
        return []

    chunks = []
    start = 0
    while start < len(prose):
        end = min(start + max_chars, len(prose))
        chunks.append(prose[start:end])
        start = end - OVERLAP_CHARS if end < len(prose) else end

    return [c for c in chunks if c.strip()]


def simple_chunk(text: str, max_chars: int = 4500) -> list[str]:
    """
    Simple fixed-size text chunker (no overlap).
    Retained for backward compatibility with commentary_ingest.
    """
    text = (text or "").strip()
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)] if text else []


def _split_long_text_unit(text: str, max_chars: int) -> list[str]:
    """Split a single oversized unit without cutting words."""
    words = re.findall(r"\S+", str(text or "").strip())
    if not words:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        word_len = len(word)
        separator = 1 if current else 0
        if current and current_len + separator + word_len > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_len = word_len
        else:
            current.append(word)
            current_len += separator + word_len
    if current:
        chunks.append(" ".join(current))
    return chunks


def _commentary_units(text: str, max_chars: int) -> list[str]:
    units: list[str] = []
    for raw_line in str(text or "").replace("\r", "\n").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if len(line) <= max_chars:
            units.append(line)
            continue

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", line)
            if sentence.strip()
        ]
        if len(sentences) <= 1:
            units.extend(_split_long_text_unit(line, max_chars))
        else:
            for sentence in sentences:
                if len(sentence) <= max_chars:
                    units.append(sentence)
                else:
                    units.extend(_split_long_text_unit(sentence, max_chars))
    return units


def chunk_commentary_text(
    text: str,
    *,
    max_chars: int = 1400,
    min_chars: int = 650,
) -> list[str]:
    """Chunk transcript/commentary text on line and sentence boundaries.

    YouTube transcript lines are timestamp-stripped before this function is
    called, so each line is already a caption segment. Keeping those segments
    intact prevents mid-word and mid-sentence review snippets.
    """
    resolved_max = max(120, int(max_chars))
    resolved_min = max(0, min(int(min_chars), resolved_max))
    units = _commentary_units(text, resolved_max)
    if not units:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for unit in units:
        separator = 1 if current else 0
        next_len = current_len + separator + len(unit)
        if current and next_len > resolved_max and current_len >= resolved_min:
            chunks.append("\n".join(current).strip())
            current = [unit]
            current_len = len(unit)
        elif current and next_len > resolved_max:
            chunks.append("\n".join(current).strip())
            current = [unit]
            current_len = len(unit)
        else:
            current.append(unit)
            current_len = next_len

    if current:
        chunks.append("\n".join(current).strip())
    return [chunk for chunk in chunks if chunk.strip()]
