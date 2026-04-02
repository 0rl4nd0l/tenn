"""
structured_chunking.py — Prose-section chunking for Qdrant embedding.

Tables are excluded — they go to the metric extraction path.
Only non-table text sections are chunked here.
"""
from __future__ import annotations

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
