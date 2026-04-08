from __future__ import annotations
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
_SKILL_PATH = Path(__file__).parent / "extraction_skill.md"

def should_review(runs_since_last_review: int, review_interval: int = 5) -> bool:
    return runs_since_last_review >= review_interval > 0

def parse_skill_frontmatter(skill_path: Path) -> dict[str, Any]:
    content = skill_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    frontmatter: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        try:
            frontmatter[key.strip()] = int(value)
        except ValueError:
            try:
                frontmatter[key.strip()] = float(value)
            except ValueError:
                frontmatter[key.strip()] = value
    return frontmatter

def skill_patch(skill_path: Path, old_string: str, new_string: str) -> bool:
    content = skill_path.read_text(encoding="utf-8")
    if old_string not in content:
        logger.warning("skill_patch: old_string not found in %s", skill_path)
        return False
    updated = content.replace(old_string, new_string, 1)
    fd, tmp_path = tempfile.mkstemp(dir=str(skill_path.parent), prefix=".skill_", suffix=".md")
    try:
        os.write(fd, updated.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(skill_path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return True

def snapshot_skill(skill_path: Path) -> Path | None:
    if not skill_path.exists():
        return None
    prev_path = skill_path.with_suffix(".prev.md")
    content = skill_path.read_text(encoding="utf-8")
    fd, tmp_path = tempfile.mkstemp(dir=str(skill_path.parent), prefix=".prev_", suffix=".md")
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(prev_path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return prev_path

def restore_skill_snapshot(skill_path: Path) -> bool:
    prev_path = skill_path.with_suffix(".prev.md")
    if not prev_path.exists():
        return False
    os.replace(str(prev_path), str(skill_path))
    return True

def read_skill(skill_path: Path | None = None) -> str:
    path = skill_path or _SKILL_PATH
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
