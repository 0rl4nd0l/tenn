from __future__ import annotations
import os
import textwrap
from pathlib import Path
import pytest
from services.extraction.skill_reviewer import (
    skill_patch, snapshot_skill, restore_skill_snapshot, should_review, parse_skill_frontmatter,
)

SEED_SKILL = textwrap.dedent("""\
    ---
    name: pdf-extraction-routing
    description: Learned patterns for PDF extraction method selection
    version: 1.0.0
    updated_at: "2026-04-08T00:00:00Z"
    review_count: 0
    ---

    # PDF Extraction Routing Skill

    ## Document Type Patterns
    No patterns learned yet.
    """)

def test_skill_patch_replaces_text(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text(SEED_SKILL, encoding="utf-8")
    result = skill_patch(skill_path=skill_file, old_string="No patterns learned yet.",
        new_string="- structured_financial_reports: prefer pdftotext (accuracy 0.91)")
    assert result is True
    content = skill_file.read_text(encoding="utf-8")
    assert "prefer pdftotext" in content
    assert "No patterns learned yet." not in content

def test_skill_patch_returns_false_when_old_string_not_found(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text(SEED_SKILL, encoding="utf-8")
    result = skill_patch(skill_path=skill_file, old_string="this string does not exist", new_string="replacement")
    assert result is False
    assert "replacement" not in skill_file.read_text(encoding="utf-8")

def test_skill_patch_atomic_write(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text(SEED_SKILL, encoding="utf-8")
    skill_patch(skill_path=skill_file, old_string="No patterns learned yet.", new_string="Updated pattern.")
    temp_files = [f for f in tmp_path.iterdir() if f.name.startswith(".skill_")]
    assert len(temp_files) == 0

def test_snapshot_and_restore(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text("original content", encoding="utf-8")
    prev = snapshot_skill(skill_file)
    assert prev is not None
    skill_file.write_text("modified content", encoding="utf-8")
    restore_skill_snapshot(skill_file)
    assert skill_file.read_text(encoding="utf-8") == "original content"

def test_should_review_true_at_interval():
    assert should_review(runs_since_last_review=5, review_interval=5) is True
    assert should_review(runs_since_last_review=10, review_interval=5) is True

def test_should_review_false_below_interval():
    assert should_review(runs_since_last_review=3, review_interval=5) is False
    assert should_review(runs_since_last_review=0, review_interval=5) is False

def test_parse_skill_frontmatter(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text(SEED_SKILL, encoding="utf-8")
    fm = parse_skill_frontmatter(skill_file)
    assert fm["name"] == "pdf-extraction-routing"
    assert fm["review_count"] == 0
