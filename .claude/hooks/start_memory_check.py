#!/usr/bin/env python3
"""SessionStart hook: surface relevant memories and flag stale ones.

1. Reads the current branch + recent commit subjects to infer session context.
2. Scans memory files for keyword overlap with that context.
3. Flags project memories whose dates are >14 days old as potentially stale.
4. Always surfaces feedback memories (behavioral rules Claude must follow).
"""
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

REPO = "/home/l4nd0/tenn"
MEMORY_DIR = Path(os.path.expanduser(
    "~/.claude/projects/-home-l4nd0-tenn/memory"
))
STALE_DAYS = 14


def get_session_context():
    """Gather branch name and recent commit subjects for keyword matching."""
    os.chdir(REPO)
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()

    log = subprocess.run(
        ["git", "log", "--oneline", "-10", "--format=%s"],
        capture_output=True, text=True,
    ).stdout.strip()

    # Also check uncommitted file paths for subsystem hints
    diff_files = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()

    context_blob = f"{branch} {log} {diff_files}".lower()
    return branch, context_blob


def parse_memory_file(path):
    """Extract frontmatter fields and body from a memory file."""
    try:
        text = path.read_text()
    except Exception:
        return None

    info = {"path": path.name, "type": "", "name": "", "description": "", "body": ""}

    # Parse YAML frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if fm_match:
        fm_block, body = fm_match.groups()
        info["body"] = body.strip()
        for line in fm_block.splitlines():
            for key in ("type", "name", "description"):
                if line.startswith(f"{key}:"):
                    info[key] = line.split(":", 1)[1].strip()
    else:
        info["body"] = text.strip()

    return info


def extract_dates(text):
    """Find YYYY-MM-DD dates in text."""
    return [
        datetime.strptime(d, "%Y-%m-%d")
        for d in re.findall(r"20\d{2}-\d{2}-\d{2}", text)
    ]


def check_staleness(memory):
    """Return True if the memory mentions only dates older than STALE_DAYS."""
    if memory["type"] != "project":
        return False
    full_text = f"{memory['description']} {memory['body']}"
    dates = extract_dates(full_text)
    if not dates:
        return False
    newest = max(dates)
    return (datetime.now() - newest) > timedelta(days=STALE_DAYS)


def keyword_relevance(memory, context_blob):
    """Score how relevant a memory is to the current session context."""
    searchable = f"{memory['name']} {memory['description']} {memory['body']}".lower()
    # Extract meaningful words (skip short ones)
    words = set(re.findall(r"[a-z_]{4,}", searchable))
    context_words = set(re.findall(r"[a-z_]{4,}", context_blob))
    overlap = words & context_words
    return len(overlap)


def main():
    if not MEMORY_DIR.exists():
        return

    branch, context_blob = get_session_context()

    memory_files = sorted(MEMORY_DIR.glob("*.md"))
    memory_files = [f for f in memory_files if f.name != "MEMORY.md"]

    if not memory_files:
        return

    memories = []
    for mf in memory_files:
        info = parse_memory_file(mf)
        if info:
            memories.append(info)

    if not memories:
        return

    parts = []

    # --- Feedback memories (always surface) ---
    feedback = [m for m in memories if m["type"] == "feedback"]
    if feedback:
        parts.append("ACTIVE FEEDBACK RULES (from prior sessions):")
        for m in feedback:
            parts.append(f"  • {m['description']}")
        parts.append("")

    # --- Context-relevant memories ---
    scored = [(m, keyword_relevance(m, context_blob)) for m in memories if m["type"] != "feedback"]
    relevant = [(m, s) for m, s in scored if s >= 2]
    relevant.sort(key=lambda x: -x[1])

    if relevant:
        parts.append("RELEVANT MEMORIES for this session context:")
        for m, score in relevant[:5]:
            tag = f"[{m['type']}]" if m["type"] else ""
            parts.append(f"  • {tag} {m['description']} ({m['path']})")
        parts.append("")

    # --- Stale project memories ---
    stale = [m for m in memories if check_staleness(m)]
    if stale:
        parts.append(f"POTENTIALLY STALE MEMORIES (>{STALE_DAYS} days):")
        for m in stale:
            parts.append(f"  • {m['description']} ({m['path']}) — verify or remove")
        parts.append("")

    if parts:
        msg = "\n".join(parts)
        print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    main()
