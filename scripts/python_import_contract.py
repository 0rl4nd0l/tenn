#!/usr/bin/env python3
"""Single source of truth for Tenn dev/test Python import roots."""

from __future__ import annotations

import configparser
import os
from pathlib import Path
import sys
from typing import Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTEST_INI = REPO_ROOT / "pytest.ini"
_RELATIVE_IMPORT_ROOTS = (
    ".",
    "financial-engine_v2",
    "financial-engine_v2/backend",
    "scripts",
)


def resolve_repo_root(repo_root: str | Path | None = None) -> Path:
    """Return the absolute repo root used for dev/test imports."""
    if repo_root is None:
        return REPO_ROOT
    return Path(repo_root).expanduser().resolve()


def relative_import_roots() -> tuple[str, ...]:
    """Return repo-relative roots expected in pytest.ini."""
    return _RELATIVE_IMPORT_ROOTS


def import_roots(repo_root: str | Path | None = None) -> tuple[Path, ...]:
    """Return absolute repo roots required by tests and repo-level scripts."""
    root = resolve_repo_root(repo_root)
    return tuple(root if relative == "." else root / relative for relative in _RELATIVE_IMPORT_ROOTS)


def _path_text(path: str | Path) -> str:
    return str(path)


def dedupe_path_entries(paths: Iterable[str | Path]) -> list[str]:
    """Return path strings in first-seen order, dropping blanks and duplicates."""
    entries: list[str] = []
    seen: set[str] = set()
    for path in paths:
        text = _path_text(path)
        if not text or text in seen:
            continue
        entries.append(text)
        seen.add(text)
    return entries


def merge_pythonpath_entries(paths: Sequence[str | Path], existing: str | None = None) -> list[str]:
    """Merge path entries with an existing PYTHONPATH string without duplicates."""
    merged: list[str | Path] = list(paths)
    if existing:
        merged.extend(item for item in existing.split(os.pathsep) if item)
    return dedupe_path_entries(merged)


def merge_pythonpath(paths: Sequence[str | Path], existing: str | None = None) -> str:
    """Return a PYTHONPATH string from merged path entries."""
    return os.pathsep.join(merge_pythonpath_entries(paths, existing))


def dev_pythonpath_entries(
    *,
    repo_root: str | Path | None = None,
    extra_paths: Sequence[str | Path] = (),
    existing: str | None = None,
) -> list[str]:
    """Return PYTHONPATH entries for repo dev/test commands."""
    return merge_pythonpath_entries([*import_roots(repo_root), *extra_paths], existing)


def dev_pythonpath(
    *,
    repo_root: str | Path | None = None,
    extra_paths: Sequence[str | Path] = (),
    existing: str | None = None,
) -> str:
    """Return a PYTHONPATH string for repo dev/test commands."""
    return os.pathsep.join(dev_pythonpath_entries(repo_root=repo_root, extra_paths=extra_paths, existing=existing))


def install_import_roots(
    *,
    repo_root: str | Path | None = None,
    sys_path: list[str] | None = None,
) -> list[str]:
    """Prepend contract roots to sys.path in deterministic order."""
    target = sys.path if sys_path is None else sys_path
    roots = [str(path) for path in import_roots(repo_root)]
    for root in roots:
        while root in target:
            target.remove(root)
    target[:0] = roots
    return target


def read_pytest_ini_pythonpath(pytest_ini: str | Path | None = None) -> tuple[str, ...]:
    """Read the declarative pytest.ini pythonpath entries."""
    path = Path(pytest_ini) if pytest_ini is not None else PYTEST_INI
    parser = configparser.ConfigParser(interpolation=None)
    with path.open("r", encoding="utf-8") as handle:
        parser.read_file(handle)
    raw = parser.get("pytest", "pythonpath", fallback="")
    return tuple(line.strip() for line in raw.splitlines() if line.strip())


def check_pytest_ini_pythonpath(pytest_ini: str | Path | None = None) -> dict[str, object]:
    """Check pytest.ini against the import contract."""
    expected = relative_import_roots()
    actual = read_pytest_ini_pythonpath(pytest_ini)
    missing = tuple(item for item in expected if item not in actual)
    unexpected = tuple(item for item in actual if item not in expected)
    return {
        "ok": actual == expected,
        "expected": expected,
        "actual": actual,
        "missing": missing,
        "unexpected": unexpected,
    }
