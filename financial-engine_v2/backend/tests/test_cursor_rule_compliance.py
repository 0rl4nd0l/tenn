"""
Mirror .cursor/rules/backend_architecture.md in CI.

Ensures architecture rules are enforced even when Cursor is not used.
Walks backend runtime files and fails on forbidden patterns.
"""

import ast
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_ROOT / "app"

# Paths considered "pipeline" for the uuid rule (vector IDs must be deterministic, not UUID).
PIPELINE_PATH_SUBSTRINGS = ("pipeline.py", "pipeline_service.py")


def _iter_runtime_backend_files():
    """Yield Python files that are part of backend runtime (exclude tests and alembic)."""
    for path in APP_ROOT.rglob("*.py"):
        parts = set(path.parts)
        if "tests" in parts:
            continue
        if "alembic" in parts:
            continue
        yield path


def _is_pipeline_file(path: Path) -> bool:
    return any(s in path.name for s in PIPELINE_PATH_SUBSTRINGS)


def test_no_fallback_in_embedding_context():
    """Rule: MUST NOT introduce fallback embedding backends."""
    violations: list[str] = []
    for path in _iter_runtime_backend_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            lower = line.lower()
            if "fallback" in lower and "embed" in lower:
                violations.append(f"{path}:{lineno}: {line.strip()}")
    assert not violations, (
        "'fallback' must not appear in embedding context in backend runtime "
        "(see .cursor/rules/backend_architecture.md):\n"
        + "\n".join(violations)
    )


def test_no_sqlite3_in_runtime():
    """Rule: MUST NOT use SQLite as vector store or reintroduce SQLite in runtime code paths."""
    violations: list[str] = []
    for path in _iter_runtime_backend_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "sqlite3":
                        violations.append(f"{path}: import sqlite3")
            elif isinstance(node, ast.ImportFrom) and node.module == "sqlite3":
                violations.append(f"{path}: from sqlite3 import ...")
    assert not violations, (
        "sqlite3 must not appear in backend runtime (see .cursor/rules/backend_architecture.md):\n"
        + "\n".join(violations)
    )


# Allowed context for uuid.uuid4(): creating new document primary key at insert time only.
# Forbidden in process_document and anywhere that builds vector/chunk IDs.
_UUID4_ALLOWED_IN_FUNCTION = "insert_discovered_documents"


class _Uuid4Checker(ast.NodeVisitor):
    """Track enclosing function and report uuid.uuid4() only when not in allowed context."""

    def __init__(self, path: Path):
        self.path = path
        self.violations: list[str] = []
        self._function_stack: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute):
            if (
                getattr(node.func.value, "id", None) == "uuid"
                and node.func.attr == "uuid4"
            ):
                in_allowed = (
                    self._function_stack
                    and self._function_stack[-1] == _UUID4_ALLOWED_IN_FUNCTION
                )
                if not in_allowed:
                    self.violations.append(
                        f"{self.path}:{node.lineno}: uuid.uuid4() is forbidden "
                        "(allowed only in insert_discovered_documents for document primary key)"
                    )
        self.generic_visit(node)


def test_no_random_uuid_generation_in_pipeline():
    """
    Enforce that random UUID generation is not used in pipeline ingestion
    or vector ID construction. Exception: insert_discovered_documents may use
    uuid4 for new document primary keys (per backend_architecture.md).
    """
    backend_root = Path(__file__).resolve().parents[1]
    app_dir = backend_root / "app"

    violations: list[str] = []

    for path in app_dir.rglob("*.py"):
        if "tests" in path.parts or "alembic" in path.parts:
            continue

        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        checker = _Uuid4Checker(path)
        checker.visit(tree)
        violations.extend(checker.violations)

    assert not violations, (
        "Random UUID generation is forbidden in ingestion/vector logic "
        "(except document primary key in insert_discovered_documents).\n"
        + "\n".join(violations)
    )
