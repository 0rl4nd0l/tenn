#!/usr/bin/env python3
"""Validate AGENTS.md runtime functionality proof instructions."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_SECTION_TITLE = "### Runtime Functionality Proof"

REQUIRED_PHRASES = [
    "For daemon, runtime, ingestion, extraction, automation, collector, scheduler",
    "agents must not equate activity with functionality",
    "A running service is not proof.",
    "A timer is not proof.",
    "Fresh logs are not proof.",
    "Fresh artifacts are not proof.",
    "Passing unit tests are not proof.",
    "A report bundle is not proof.",
    "A merged PR is not proof.",
    "Functionality requires proving that the intended live output changed",
    "If the intended output is stale, zero, missing, or unverified",
]

REQUIRED_FIELDS = [
    "intended output",
    "live output location",
    "pre-run max timestamp or count",
    "post-run max timestamp or count",
    "rows/files inserted or updated after run start",
    "readiness/gate status",
    "exact command/query used",
    "result: WORKING / PARTIAL / BROKEN / DATA_MISSING",
    "remaining blocker",
]


def extract_section(text: str) -> str:
    start = text.find(REQUIRED_SECTION_TITLE)
    if start == -1:
        raise ValueError(f"missing section title: {REQUIRED_SECTION_TITLE}")
    next_match = re.search(r"\n###\s+", text[start + len(REQUIRED_SECTION_TITLE) :])
    if not next_match:
        return text[start:]
    end = start + len(REQUIRED_SECTION_TITLE) + next_match.start()
    return text[start:end]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    agents_path = repo_root / "AGENTS.md"
    text = agents_path.read_text(encoding="utf-8")
    section = extract_section(text)

    missing: list[str] = []
    for phrase in REQUIRED_PHRASES:
        if phrase not in section:
            missing.append(phrase)
    for field in REQUIRED_FIELDS:
        if field not in section:
            missing.append(field)

    if missing:
        print("runtime_functionality_proof_docs_failed")
        for item in missing:
            print(f"missing: {item}")
        return 1

    print("runtime_functionality_proof_docs_ok")
    print(f"checked: {agents_path.relative_to(repo_root)}")
    print(f"fields: {len(REQUIRED_FIELDS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
