"""Lightweight repository RAG indexing/search utilities."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any


INDEX_FILE = "autodev/cache/repo_index.json"
MAX_FILE_LINES = 200
MAX_CONTEXT_CHARS = 20_000
SUPPORTED_SUFFIXES = {".py", ".md", ".yaml", ".json"}
SKIP_DIRS = {".venv", ".git", "__pycache__", "node_modules"}
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _repo_root(repo_path: Path | None = None) -> Path:
    if repo_path is not None:
        return repo_path.resolve()
    return Path(__file__).resolve().parents[2]


def _index_path(repo_path: Path | None = None) -> Path:
    return _repo_root(repo_path) / INDEX_FILE


def _tokenize(text: str) -> set[str]:
    return {item.lower() for item in TOKEN_RE.findall(text) if item}


def _is_allowed_file(path: str) -> bool:
    path_obj = Path(path)
    if path_obj.suffix not in SUPPORTED_SUFFIXES:
        return False
    return not any(part in SKIP_DIRS for part in path_obj.parts)


def _tracked_files(repo_path: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        files: list[str] = []
        for walk_root, dir_names, file_names in os.walk(repo_path):
            dir_names[:] = sorted([item for item in dir_names if item not in SKIP_DIRS])
            root = Path(walk_root)
            for file_name in sorted(file_names):
                rel = (root / file_name).relative_to(repo_path).as_posix()
                if _is_allowed_file(rel):
                    files.append(rel)
        return files
    tracked = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return sorted([item for item in tracked if _is_allowed_file(item)])


def _python_metadata(text: str) -> tuple[list[str], list[str], list[str], list[str]]:
    imports: list[str] = []
    functions: list[str] = []
    classes: list[str] = []
    docstrings: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return imports, functions, classes, docstrings

    def _first_nonempty_line(value: str | None) -> str | None:
        if value is None:
            return None
        for line in value.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return None

    module_doc = ast.get_docstring(tree)
    module_line = _first_nonempty_line(module_doc)
    if module_line:
        docstrings.append(module_line)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
            fn_doc = ast.get_docstring(node)
            fn_line = _first_nonempty_line(fn_doc)
            if fn_line:
                docstrings.append(fn_line)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
            cls_doc = ast.get_docstring(node)
            cls_line = _first_nonempty_line(cls_doc)
            if cls_line:
                docstrings.append(cls_line)

    return sorted(set(imports)), sorted(set(functions)), sorted(set(classes)), sorted(set(docstrings))


def _text_docstrings(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:5]


def index_repository(repo_path: Path) -> dict[str, Any]:
    """Scan repository files and write metadata index to autodev/cache/repo_index.json."""
    repo_root = _repo_root(repo_path)
    files = _tracked_files(repo_root)
    entries: list[dict[str, Any]] = []

    for rel_path in files:
        abs_path = repo_root / rel_path
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
            stat = abs_path.stat()
        except OSError:
            continue
        imports: list[str] = []
        functions: list[str] = []
        classes: list[str] = []
        docstrings: list[str] = []
        if abs_path.suffix == ".py":
            imports, functions, classes, docstrings = _python_metadata(text)
        else:
            docstrings = _text_docstrings(text)

        entries.append(
            {
                "file_path": rel_path,
                "imports": imports,
                "functions": functions,
                "classes": classes,
                "docstrings": docstrings,
                "file_size": int(stat.st_size),
                "last_modified": float(stat.st_mtime),
            }
        )

    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_path": str(repo_root),
        "indexed_file_count": len(entries),
        "files": sorted(entries, key=lambda item: str(item.get("file_path", ""))),
    }
    index_path = _index_path(repo_root)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _load_index(repo_path: Path) -> dict[str, Any]:
    index_path = _index_path(repo_path)
    if not index_path.exists():
        return index_repository(repo_path)
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return index_repository(repo_path)
    if not isinstance(payload, dict):
        return index_repository(repo_path)
    files = payload.get("files")
    if not isinstance(files, list):
        return index_repository(repo_path)
    return payload


def search_repository(query: str, top_k: int = 5, repo_path: Path | None = None) -> list[str]:
    """Return top-k relevant tracked files for the query."""
    repo_root = _repo_root(repo_path)
    payload = _load_index(repo_root)
    entries = payload.get("files", [])
    if not isinstance(entries, list):
        return []
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    ranked: list[tuple[int, str]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get("file_path", "")).strip()
        if not rel_path:
            continue
        filename = Path(rel_path).name.lower()
        score = 0

        if any(token in filename for token in query_tokens):
            score += 3

        fn_tokens = _tokenize(" ".join(str(x) for x in item.get("functions", [])))
        cls_tokens = _tokenize(" ".join(str(x) for x in item.get("classes", [])))
        if query_tokens.intersection(fn_tokens.union(cls_tokens)):
            score += 2

        doc_tokens = _tokenize(" ".join(str(x) for x in item.get("docstrings", [])))
        keyword_pool = set()
        keyword_pool.update(_tokenize(rel_path))
        keyword_pool.update(_tokenize(" ".join(str(x) for x in item.get("imports", []))))
        keyword_pool.update(doc_tokens)
        if query_tokens.intersection(keyword_pool):
            score += 1

        if score > 0:
            ranked.append((score, rel_path))

    ranked.sort(key=lambda entry: (-entry[0], entry[1]))
    limit = max(1, int(top_k))
    return [path for _, path in ranked[:limit]]


def _normalize_rel_path(path: str) -> str:
    path_obj = Path(path)
    if path_obj.is_absolute() or ".." in path_obj.parts:
        return ""
    return path_obj.as_posix().lstrip("./")


def load_context(files: list[str], repo_path: Path | None = None) -> str:
    """Load up to 200 lines per tracked file and cap total context at 20k chars."""
    repo_root = _repo_root(repo_path)
    tracked = set(_tracked_files(repo_root))
    sections: list[str] = []
    total = 0

    for path in files:
        rel_path = _normalize_rel_path(path)
        if not rel_path or rel_path not in tracked:
            continue
        abs_path = repo_root / rel_path
        if not abs_path.exists():
            continue
        try:
            lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        snippet = "\n".join(lines[:MAX_FILE_LINES])
        section = f"FILE: {rel_path}\n{snippet}\n"
        if total + len(section) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - total
            if remaining <= 0:
                break
            section = section[:remaining]
            sections.append(section)
            total += len(section)
            break
        sections.append(section)
        total += len(section)

    return "\n".join(sections).strip()
