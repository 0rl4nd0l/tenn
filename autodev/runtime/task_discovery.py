"""Deterministic repository scan to propose AutoDev tasks."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import time

from autodev.runtime.task_scoring import rank_tasks, score_task
from autodev.runtime.task_queue import load_milestones


PY_FILES = (".py",)
MAX_FUNCTION_LINES = 150
MAX_FILE_LINES = 800
SLOW_FUNCTION_MAX_LOOP_DEPTH = 2
SLOW_FUNCTION_ITERATION_NODES = 6
TODO_PATTERN = re.compile(r"\b(TODO|FIXME)\b\s*[:\-]?\s*(.*)", re.IGNORECASE)
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    ".venv-autodev",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
TARGET_PREFIX = "autodev/"
STATE_FILE = "autodev/state/discovery_state.json"
MAX_DISCOVERED_TASKS = 20


TaskRecord = dict[str, object]


def _discovery_state_path(repo_path: Path | None = None) -> Path:
    root = repo_path.resolve() if repo_path is not None else Path(__file__).resolve().parents[2]
    return root / STATE_FILE


def should_run_discovery(interval_seconds: int, repo_path: Path | None = None) -> bool:
    """Return True when task discovery should run based on cached state."""
    if interval_seconds <= 0:
        return True
    state_path = _discovery_state_path(repo_path)
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        last_run = float(payload.get("last_run", 0))
    except Exception:
        return True
    return (time.time() - last_run) > interval_seconds


def mark_discovery_run(repo_path: Path | None = None) -> None:
    """Persist the timestamp of the most recent discovery run."""
    state_path = _discovery_state_path(repo_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"last_run": time.time()}, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_key(value: str, sep: str) -> str:
    out = re.sub(r"[^a-z0-9]+", sep, value.lower()).strip(sep)
    return out or "item"


def _task_line(kind: str, key: str, title: str, milestone_id: str, priority: int) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
    key_us = _safe_key(key, "_")
    key_dash = _safe_key(key, "-")
    task_id = f"T_auto_{kind}_{key_us[:28]}_{digest}"
    slug = f"auto-{kind}-{key_dash[:36]}-{digest}"
    clean_title = f"{title} (priority={priority})".replace("|", "/").strip()
    return f"- [ ] {task_id} | milestone:{milestone_id} | slug:{slug} | title:{clean_title}"


def _default_milestone_id(repo_path: Path) -> str:
    milestones_path = repo_path / "autodev" / "spec" / "MILESTONES.md"
    milestones = load_milestones(milestones_path)
    if milestones:
        return sorted(milestones.keys())[0]
    return "M1"


def _relative_path(repo_path: Path, path: Path) -> str:
    return path.relative_to(repo_path).as_posix()


def _is_target_path(repo_path: Path, path: Path) -> bool:
    rel = _relative_path(repo_path, path)
    return rel.startswith(TARGET_PREFIX)


def scan_repository(repo_path: Path) -> list[Path]:
    """Return all Python files under repo_path, excluding ignored directories."""
    if not repo_path.exists():
        return []
    found: list[Path] = []
    for walk_root, dir_names, file_names in os.walk(repo_path):
        dir_names[:] = sorted(
            d for d in dir_names if d not in SKIP_DIR_NAMES and not d.startswith(".venv")
        )
        for file_name in sorted(file_names):
            if file_name.endswith(PY_FILES):
                found.append(Path(walk_root) / file_name)
    return sorted(found)


def _iter_python_files(repo_path: Path) -> list[Path]:
    return [path for path in scan_repository(repo_path) if _is_target_path(repo_path, path)]


def _source_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _function_nodes(tree: ast.AST) -> list[tuple[ast.AST, str]]:
    nodes: list[tuple[ast.AST, str]] = []

    def visit(node: ast.AST, parents: list[str]) -> None:
        child_parents = parents[:]
        if isinstance(node, ast.ClassDef):
            child_parents.append(node.name)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualname = ".".join([*parents, node.name]) if parents else node.name
            nodes.append((node, qualname))
            child_parents = [*parents, node.name]
        for child in ast.iter_child_nodes(node):
            visit(child, child_parents)

    visit(tree, [])
    return nodes


def _has_test_for_module(repo_path: Path, module_path: Path) -> bool:
    autodev_root = repo_path / "autodev"
    tests_root = autodev_root / "tests"
    module_rel = module_path.relative_to(autodev_root)
    stem = module_rel.stem
    candidates = [
        tests_root / f"test_{stem}.py",
        tests_root / module_rel.parent / f"test_{stem}.py",
    ]
    return any(path.exists() for path in candidates)


def _parse_tree(path: Path, rel: str, lines: list[str]) -> ast.AST | None:
    try:
        return ast.parse("\n".join(lines), filename=rel)
    except SyntaxError:
        return None


def _imported_names(tree: ast.AST) -> list[tuple[str, str, int]]:
    imported: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".")[0]
                display_name = alias.asname or alias.name
                imported.append((local_name, display_name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                if node.module:
                    display_name = f"{node.module}.{alias.name}"
                else:
                    display_name = alias.name
                imported.append((local_name, display_name, node.lineno))
    return imported


def _used_names(tree: ast.AST) -> set[str]:
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
    return used


class _SlowFunctionVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.loop_depth = 0
        self.max_loop_depth = 0
        self.iteration_nodes = 0

    def _visit_loop(self, node: ast.AST) -> None:
        self.iteration_nodes += 1
        self.loop_depth += 1
        self.max_loop_depth = max(self.max_loop_depth, self.loop_depth)
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        self._visit_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:  # noqa: N802
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        self._visit_loop(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:  # noqa: N802
        self.iteration_nodes += len(node.generators)
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:  # noqa: N802
        self.iteration_nodes += len(node.generators)
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:  # noqa: N802
        self.iteration_nodes += len(node.generators)
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:  # noqa: N802
        self.iteration_nodes += len(node.generators)
        self.generic_visit(node)


def _slow_function_reason(node: ast.AST) -> str | None:
    visitor = _SlowFunctionVisitor()
    visitor.visit(node)
    if visitor.max_loop_depth >= SLOW_FUNCTION_MAX_LOOP_DEPTH:
        return f"nested loops depth {visitor.max_loop_depth}"
    if visitor.iteration_nodes >= SLOW_FUNCTION_ITERATION_NODES:
        return f"{visitor.iteration_nodes} iteration constructs"
    return None


def discover_todo_tasks(repo_path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    for path in _iter_python_files(repo_path):
        rel = _relative_path(repo_path, path)
        for line_num, line in enumerate(_source_lines(path), start=1):
            comment_idx = line.find("#")
            if comment_idx < 0:
                continue
            comment_text = line[comment_idx + 1 :]
            match = TODO_PATTERN.search(comment_text)
            if not match:
                continue
            description = match.group(2).strip() or "Resolve TODO/FIXME"
            tasks.append(
                {
                    "type": "todo",
                    "file": rel,
                    "line": line_num,
                    "description": description,
                }
            )
    return tasks


def discover_large_files(repo_path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    for path in _iter_python_files(repo_path):
        rel = _relative_path(repo_path, path)
        lines = _source_lines(path)
        if len(lines) > MAX_FILE_LINES:
            tasks.append(
                {
                    "type": "refactor_large_file",
                    "file": rel,
                    "line": 1,
                    "lines": len(lines),
                    "description": f"File exceeds {MAX_FILE_LINES} lines",
                }
            )
    return tasks


def discover_large_functions(repo_path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    for path in _iter_python_files(repo_path):
        rel = _relative_path(repo_path, path)
        lines = _source_lines(path)
        tree = _parse_tree(path, rel, lines)
        if tree is None:
            continue
        for node, qualname in _function_nodes(tree):
            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)
            if start is None or end is None:
                continue
            fn_lines = end - start + 1
            if fn_lines > MAX_FUNCTION_LINES:
                tasks.append(
                    {
                        "type": "refactor_large_function",
                        "file": rel,
                        "line": start,
                        "lines": fn_lines,
                        "function": qualname,
                        "description": f"Function exceeds {MAX_FUNCTION_LINES} lines",
                    }
                )
    return tasks


def discover_slow_functions(repo_path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    for path in _iter_python_files(repo_path):
        rel = _relative_path(repo_path, path)
        lines = _source_lines(path)
        tree = _parse_tree(path, rel, lines)
        if tree is None:
            continue
        for node, qualname in _function_nodes(tree):
            reason = _slow_function_reason(node)
            if reason is None:
                continue
            tasks.append(
                {
                    "type": "slow_function",
                    "file": rel,
                    "line": getattr(node, "lineno", 1),
                    "function": qualname,
                    "description": reason,
                }
            )
    return tasks


def discover_missing_tests(repo_path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    autodev_root = repo_path / "autodev"
    for path in _iter_python_files(repo_path):
        rel = _relative_path(repo_path, path)
        if not rel.startswith("autodev/"):
            continue
        if path.parent.name == "tests" or "/tests/" in rel or path.name == "__init__.py":
            continue
        if _has_test_for_module(repo_path, path):
            continue
        module_rel = path.relative_to(autodev_root).as_posix()
        tasks.append(
            {
                "type": "missing_tests",
                "file": rel,
                "line": 1,
                "description": f"Add tests for module autodev/{module_rel}",
            }
        )
    return tasks


def discover_dead_imports(repo_path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    for path in _iter_python_files(repo_path):
        rel = _relative_path(repo_path, path)
        lines = _source_lines(path)
        tree = _parse_tree(path, rel, lines)
        if tree is None:
            continue
        used_names = _used_names(tree)
        for local_name, import_name, line_no in _imported_names(tree):
            if local_name in used_names:
                continue
            tasks.append(
                {
                    "type": "dead_import",
                    "file": rel,
                    "line": line_no,
                    "description": f"Remove unused import {import_name}",
                }
            )
    return tasks


def discover_missing_docstrings(repo_path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    for path in _iter_python_files(repo_path):
        rel = _relative_path(repo_path, path)
        lines = _source_lines(path)
        tree = _parse_tree(path, rel, lines)
        if tree is None:
            continue
        for node, qualname in _function_nodes(tree):
            if ast.get_docstring(node) is not None:
                continue
            tasks.append(
                {
                    "type": "docstring",
                    "file": rel,
                    "line": getattr(node, "lineno", 1),
                    "function": qualname,
                    "description": f"Add docstring to function {qualname} in {rel}",
                }
            )
    return tasks


def discover_tasks(repo_path: Path) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    tasks.extend(discover_todo_tasks(repo_path))
    tasks.extend(discover_large_files(repo_path))
    tasks.extend(discover_large_functions(repo_path))
    tasks.extend(discover_slow_functions(repo_path))
    tasks.extend(discover_missing_tests(repo_path))
    tasks.extend(discover_dead_imports(repo_path))
    tasks.extend(discover_missing_docstrings(repo_path))

    deduped: list[TaskRecord] = []
    seen: set[tuple[str, str, int, str]] = set()
    for task in tasks:
        file_value = str(task.get("file", ""))
        line_value = int(task.get("line", 0) or 0)
        key = (
            str(task.get("type", "")),
            file_value,
            line_value,
            str(task.get("description", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(task)
    deduped_sorted = sorted(
        deduped,
        key=lambda item: (
            str(item.get("file", "")),
            int(item.get("line", 0) or 0),
            str(item.get("type", "")),
            str(item.get("description", "")),
        ),
    )
    return rank_tasks(deduped_sorted)


def _task_components(task: TaskRecord) -> tuple[str, str, str, int]:
    task_type = str(task.get("type", "maintenance"))
    file_path = str(task.get("file", "autodev/unknown.py"))
    line = int(task.get("line", 0) or 0)
    description = str(task.get("description", "")).strip()
    priority = score_task(task)

    if task_type == "todo":
        kind = "todo"
        title = f"Resolve TODO/FIXME in {file_path} at line {line}"
    elif task_type == "refactor_large_file":
        kind = "modularize"
        line_count = int(task.get("lines", 0) or 0)
        title = f"Modularize large Python file {file_path} ({line_count} lines)"
    elif task_type == "refactor_large_function":
        kind = "refactor"
        fn_name = str(task.get("function", "function"))
        line_count = int(task.get("lines", 0) or 0)
        title = f"Refactor large function {fn_name} in {file_path} ({line_count} lines)"
    elif task_type == "slow_function":
        kind = "perf"
        fn_name = str(task.get("function", "function"))
        title = f"Optimize potentially slow function {fn_name} in {file_path} ({description})"
    elif task_type == "missing_tests":
        kind = "tests"
        title = description or f"Add tests for module {file_path}"
    elif task_type == "dead_import":
        kind = "deadcode"
        title = f"{description} in {file_path}"
    elif task_type == "docstring":
        kind = "docstring"
        title = description or f"Add docstring to function in {file_path}"
    else:
        kind = "maintenance"
        title = description or f"Review maintenance item in {file_path}"

    key = f"{task_type}:{file_path}:{line}:{description}"
    return kind, key, title, priority


def scan_repo(repo_path: Path) -> list[str]:
    milestone_id = _default_milestone_id(repo_path)
    tasks: list[str] = []
    discovered = discover_tasks(repo_path)[:MAX_DISCOVERED_TASKS]
    for record in discovered:
        kind, key, title, priority = _task_components(record)
        tasks.append(_task_line(kind, key, title, milestone_id, priority))

    deduped: list[str] = []
    seen: set[str] = set()
    for task in tasks:
        if task not in seen:
            seen.add(task)
            deduped.append(task)
    return deduped


def append_tasks_to_queue(repo_path: Path, tasks: list[str]) -> int:
    tasks_path = repo_path / "autodev" / "spec" / "TASKS.md"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)

    if tasks_path.exists():
        lines = tasks_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["# TASKS"]

    if not lines:
        lines = ["# TASKS"]

    existing = {line.strip() for line in lines if line.strip()}
    to_add = [task.rstrip() for task in tasks if task.strip() and task.strip() not in existing]
    if not to_add:
        return 0

    out_lines = lines[:]
    if out_lines[-1].strip():
        out_lines.append("")
    out_lines.extend(to_add)
    tasks_path.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")
    return len(to_add)
