"""
structured_chunking.py — Prose-section chunking for Qdrant embedding.

Tables are excluded — they go to the metric extraction path.
Only non-table text sections are chunked here.
"""
from __future__ import annotations

from app.services.docling_extract import StructuredDocument

MAX_CHARS = 2000  # nomic-embed-text context is 2048 tokens; ~2000 chars fits safely
OVERLAP_CHARS = 150


def chunk_prose_sections(doc: StructuredDocument, max_chars: int = MAX_CHARS) -> list[dict]:
    """
    Returns a list of chunk dicts from the document's prose sections.
    Tables are excluded. Chunks respect max_chars with simple overlap.

    Each dict: {"text": str, "section_heading": str | None}
    The section_heading is the most recent heading that preceded the chunk.
    """
    # Build a list of (char_offset, heading_text) for heading lookups,
    # and the concatenated prose string.
    parts: list[str] = []
    heading_offsets: list[tuple[int, str]] = []
    current_heading: str | None = None
    offset = 0

    for s in doc.sections:
        text = s.get("text", "").strip()
        if not text:
            continue
        if s.get("heading", False):
            current_heading = text
        # Record the heading that is active at this character offset
        if current_heading is not None:
            # Only record when heading changes or first time
            if not heading_offsets or heading_offsets[-1][1] != current_heading:
                heading_offsets.append((offset, current_heading))
        if parts:
            offset += 1  # for the joining space
        parts.append(text)
        offset += len(text)

    prose = " ".join(parts)
    if not prose.strip():
        return []

    def _heading_at(char_pos: int) -> str | None:
        """Return the most recent heading at or before char_pos."""
        result = None
        for ho, ht in heading_offsets:
            if ho <= char_pos:
                result = ht
            else:
                break
        return result

    chunks: list[dict] = []
    start = 0
    while start < len(prose):
        end = min(start + max_chars, len(prose))
        # Snap to the last sentence boundary (". ") before the hard limit,
        # but only if we're not at the end of the text. This avoids
        # mid-sentence breaks without needing nltk.
        if end < len(prose):
            # Look for last ". " or ".\n" in the candidate chunk
            snap = prose.rfind(". ", start, end)
            if snap == -1:
                snap = prose.rfind(".\n", start, end)
            # Only snap if it doesn't produce a tiny chunk (<400 chars)
            if snap != -1 and (snap + 2 - start) >= 400:
                end = snap + 2  # include the period and space
        chunk_text = prose[start:end]
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "section_heading": _heading_at(start),
            })
        start = end

    return chunks


def simple_chunk(text: str, max_chars: int = 4500) -> list[str]:
    """
    Simple fixed-size text chunker (no overlap).
    Retained for backward compatibility.
    """
    text = (text or "").strip()
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)] if text else []


def simple_chunk_overlap(text: str, max_chars: int = 1400, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Fixed-size text chunker with overlap for commentary/transcript chunks."""
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else end
    return [c for c in chunks if c.strip()]
