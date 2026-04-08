from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def load_preferences(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("routing_preferences: malformed file at %s", path)
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != SCHEMA_VERSION:
        logger.warning("routing_preferences: unsupported schema_version in %s", path)
        return None
    return data


def save_preferences(path: Path, data: dict[str, Any]) -> None:
    content = json.dumps(data, indent=2, sort_keys=False)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=".prefs_", suffix=".json"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def snapshot_preferences(path: Path) -> Path | None:
    if not path.exists():
        return None
    prev_path = path.with_suffix(".prev.json")
    content = path.read_text(encoding="utf-8")
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=".prev_", suffix=".json"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(prev_path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return prev_path


def restore_snapshot(path: Path) -> bool:
    prev_path = path.with_suffix(".prev.json")
    if not prev_path.exists():
        return False
    os.replace(str(prev_path), str(path))
    return True
