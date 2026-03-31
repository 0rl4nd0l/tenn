"""
speaker_turn_detector.py — Regex-based speaker-turn detection for transcripts.

Detects common earnings-call and interview speaker markers (e.g. "Operator:",
"John Smith - CEO:", "Q:", "A:") and annotates text chunks with speaker metadata.
"""
from __future__ import annotations

import re

# Compiled pattern matching common speaker-turn markers at the start of a line.
# Order matters: more specific patterns first to avoid partial matches.
_SPEAKER_TURN_RE = re.compile(
    r"^(?:"
    # 1. Explicit Q&A labels
    r"(?P<qa>(?:Question|Answer|Q|A))\s*:"
    r"|"
    # 2. "Name - Role:" (e.g. "John Smith - CEO:", "Jane Doe - Chief Financial Officer:")
    r"(?P<name_role>(?:[A-Z][a-zA-Z.''-]+(?:\s+[A-Z][a-zA-Z.''-]+)*)\s*[-\u2013\u2014]\s*(?P<role>[A-Za-z ]+?))\s*:"
    r"|"
    # 3. Known functional roles on their own (Operator, Moderator)
    r"(?P<func_role>Operator|Moderator)\s*:"
    r"|"
    # 4. Generic capitalized name at start of line followed by colon
    #    At least two words to reduce false positives (single words caught by func_role above)
    r"(?P<generic_name>[A-Z][a-zA-Z.''-]+(?:\s+[A-Z][a-zA-Z.''-]+)+)\s*:"
    r")",
    re.MULTILINE,
)


def detect_speaker_turns(text: str) -> list[dict]:
    """Detect speaker turn markers in transcript text.

    Returns a list of dicts sorted by offset:
        [{"offset": int, "speaker": str, "role": str | None}, ...]

    ``speaker`` is the full name or label (e.g. "John Smith", "Operator", "Q").
    ``role`` is extracted when a "Name - Role:" pattern is matched, otherwise None.
    """
    turns: list[dict] = []
    for m in _SPEAKER_TURN_RE.finditer(text):
        if m.group("qa"):
            speaker = m.group("qa")
            role = None
        elif m.group("name_role"):
            # Split "Name - Role" to get clean speaker name
            full = m.group("name_role")
            sep_idx = full.find("-")
            if sep_idx == -1:
                # Try en-dash / em-dash
                for sep in ("\u2013", "\u2014"):
                    sep_idx = full.find(sep)
                    if sep_idx != -1:
                        break
            speaker = full[:sep_idx].strip() if sep_idx != -1 else full.strip()
            role = m.group("role").strip() if m.group("role") else None
        elif m.group("func_role"):
            speaker = m.group("func_role")
            role = None
        elif m.group("generic_name"):
            speaker = m.group("generic_name").strip()
            role = None
        else:
            continue  # pragma: no cover

        turns.append({"offset": m.start(), "speaker": speaker, "role": role})

    return turns


def annotate_chunks_with_speakers(
    chunks: list[str],
    full_text: str,
) -> list[dict]:
    """Annotate each chunk with speaker information from the full transcript.

    For each chunk, finds which speaker turns fall within its boundaries in
    *full_text* and determines the primary speaker (the one with the most
    text in that chunk).

    Returns:
        [{"text": str, "speakers": list[str], "primary_speaker": str | None}, ...]
    """
    turns = detect_speaker_turns(full_text)
    if not turns:
        return [
            {"text": chunk, "speakers": [], "primary_speaker": None}
            for chunk in chunks
        ]

    # Build a position index for each chunk in full_text.
    chunk_positions: list[tuple[int, int]] = []
    search_from = 0
    for chunk in chunks:
        pos = full_text.find(chunk, search_from)
        start = max(pos, 0)
        end = start + len(chunk)
        chunk_positions.append((start, end))
        if pos >= 0:
            search_from = pos + 1

    results: list[dict] = []
    for chunk, (c_start, c_end) in zip(chunks, chunk_positions):
        # Find the active speaker at chunk start (latest turn at-or-before c_start).
        active_speaker: str | None = None
        for turn in turns:
            if turn["offset"] <= c_start:
                active_speaker = turn["speaker"]
            else:
                break

        # Collect all speakers whose turns start within this chunk.
        chunk_speakers: list[str] = []
        if active_speaker:
            chunk_speakers.append(active_speaker)

        for turn in turns:
            if turn["offset"] > c_start and turn["offset"] < c_end:
                if turn["speaker"] not in chunk_speakers:
                    chunk_speakers.append(turn["speaker"])

        # Determine primary speaker: the one with the most text in this chunk.
        # Approximate by measuring distance to next turn or chunk end.
        primary: str | None = None
        if len(chunk_speakers) <= 1:
            primary = chunk_speakers[0] if chunk_speakers else None
        else:
            # Build (speaker, char_count) for the chunk region.
            relevant_offsets: list[tuple[str, int]] = []
            if active_speaker:
                relevant_offsets.append((active_speaker, c_start))
            for turn in turns:
                if turn["offset"] > c_start and turn["offset"] < c_end:
                    relevant_offsets.append((turn["speaker"], turn["offset"]))

            speaker_chars: dict[str, int] = {}
            for i, (spk, off) in enumerate(relevant_offsets):
                if i + 1 < len(relevant_offsets):
                    length = relevant_offsets[i + 1][1] - off
                else:
                    length = c_end - off
                speaker_chars[spk] = speaker_chars.get(spk, 0) + length

            if speaker_chars:
                primary = max(speaker_chars, key=lambda s: speaker_chars[s])

        results.append({
            "text": chunk,
            "speakers": chunk_speakers,
            "primary_speaker": primary,
        })

    return results
