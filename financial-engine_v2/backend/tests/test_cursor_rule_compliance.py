"""
Mirror backend architecture invariants in CI.

Ensures architecture rules are enforced even when .cursor/rules files are absent.
Walks backend runtime files and fails on forbidden patterns.
"""

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_ROOT / "app"
ALLOWED_SQLITE_RUNTIME_IMPORTS = {
    "api/context.py",
    "routes/cockpit_api.py",
    "services/company_memory.py",
    "services/market_memory.py",
    "services/marketplace_price_intelligence.py",
    "services/ops_store.py",
    "services/response_feedback.py",
    "services/user_thesis_memory.py",
}
ALLOWED_UUID4_FUNCTIONS_BY_PATH = {
    "api/routes.py": {"process_single_document"},
    "routes/cockpit_api.py": {
        "_launch_action_job",
        "_launch_marketplace_calibration_job",
        "_launch_marketplace_ebay_sync_job",
        "_launch_marketplace_scan_job",
        "cockpit_chat",
        "cockpit_create_chat_session",
    },
    "services/cockpit_service.py": {
        "auto_flag_chat_response",
        "flag_chat_feedback",
        "record_verification_run",
    },
    "services/eval_task_registry.py": {"register"},
    "services/job_tracker.py": {"create_job"},
    "services/marketplace_benchmark_service.py": {"_new_id"},
    "services/marketplace_mission_service.py": {"_new_id"},
    "services/marketplace_price_intelligence.py": {"_new_id"},
    "services/memory_events.py": {"emit_memory_read_event", "emit_memory_write_event"},
    "services/ops_store.py": {"_new_id"},
    "services/pipeline.py": {"insert_discovered_documents", "process_document"},
    "services/response_feedback.py": {"insert"},
    "services/router_state.py": {"<module>", "register_extraction_activity"},
    "services/user_thesis_memory.py": {"create_alert", "create_proposal"},
}


def _iter_runtime_backend_files():
    """Yield Python files that are part of backend runtime (exclude tests and alembic)."""
    for path in APP_ROOT.rglob("*.py"):
        parts = set(path.parts)
        if "tests" in parts:
            continue
        if "alembic" in parts:
            continue
        yield path


def _backend_app_path(path: Path) -> str:
    return path.relative_to(APP_ROOT).as_posix()


def test_no_fallback_in_embedding_context():
    """Rule: MUST NOT introduce fallback embedding backends."""
    violations: list[str] = []
    for path in _iter_runtime_backend_files():
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            lower = line.lower()
            if "fallback" in lower and "embed" in lower:
                violations.append(f"{path}:{lineno}: {line.strip()}")
    assert not violations, (
        "'fallback' must not appear in embedding context in backend runtime "
        "(see docs/architecture/06_embeddings_and_vector_store.md):\n"
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
                    if (
                        alias.name == "sqlite3"
                        and _backend_app_path(path)
                        not in ALLOWED_SQLITE_RUNTIME_IMPORTS
                    ):
                        violations.append(f"{path}: import sqlite3")
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module == "sqlite3"
                and _backend_app_path(path) not in ALLOWED_SQLITE_RUNTIME_IMPORTS
            ):
                violations.append(f"{path}: from sqlite3 import ...")
    assert not violations, (
        "sqlite3 must not appear in backend runtime outside documented "
        "qualitative memory / operational store exceptions "
        "(see docs/architecture/06_embeddings_and_vector_store.md and "
        "docs/architecture/22_memory_ownership_map.md):\n" + "\n".join(violations)
    )


class _Uuid4Checker(ast.NodeVisitor):
    """Track enclosing function and report uuid4 outside allowed operational contexts."""

    def __init__(self, path: Path):
        self.path = path
        self.violations: list[str] = []
        self._function_stack: list[str] = []
        self._source_lines = path.read_text(encoding="utf-8").splitlines()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        is_uuid4 = (
            isinstance(node.func, ast.Attribute)
            and getattr(node.func.value, "id", None) == "uuid"
            and node.func.attr == "uuid4"
        ) or (isinstance(node.func, ast.Name) and node.func.id == "uuid4")
        if is_uuid4 and not self._is_allowed_uuid4_call(node):
            self.violations.append(
                f"{self.path}:{node.lineno}: uuid4 is forbidden for vector, chunk, "
                "canonical artifact, or reproducibility IDs"
            )
        self.generic_visit(node)

    def _is_allowed_uuid4_call(self, node: ast.Call) -> bool:
        path_key = _backend_app_path(self.path)
        function_name = self._function_stack[-1] if self._function_stack else "<module>"
        allowed_functions = ALLOWED_UUID4_FUNCTIONS_BY_PATH.get(path_key, set())
        if function_name not in allowed_functions:
            return False

        line = self._source_lines[node.lineno - 1].strip()
        if path_key == "services/pipeline.py" and function_name == "process_document":
            return "resolved_run_id" in line and "run_id or uuid.uuid4()" in line
        return True


def test_no_random_uuid_generation_in_pipeline():
    """
    Enforce that random UUID generation is not used for vector, chunk,
    canonical artifact, or reproducibility IDs. Document primary keys and
    operational task/session/feedback/event IDs remain explicit exceptions.
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
        "Random UUID generation is forbidden for vector, chunk, canonical "
        "artifact, or reproducibility IDs. Operational task/session/feedback "
        "IDs and document primary key insertion are documented exceptions.\n"
        + "\n".join(violations)
    )
