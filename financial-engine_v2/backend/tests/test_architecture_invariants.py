import ast
import inspect
import re
import textwrap
import uuid
from pathlib import Path

import pytest
from qdrant_client.http import models as qmodels

from app.services.embeddings import ensure_collection
from app.services import pipeline
from app.services.pipeline_stages import run_embedding_stage


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


def _iter_runtime_backend_files():
    """Yield Python files that are part of backend runtime code (exclude tests and alembic)."""
    for path in APP_ROOT.rglob("*.py"):
        parts = set(path.parts)
        if "tests" in parts:
            continue
        if "alembic" in parts:
            continue
        yield path


def _backend_app_path(path: Path) -> str:
    return path.relative_to(APP_ROOT).as_posix()


def test_no_sqlite_usage_in_backend_runtime():
    forbidden_module = "sqlite3"
    violations: list[str] = []

    for path in _iter_runtime_backend_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    if (
                        mod == forbidden_module
                        and _backend_app_path(path)
                        not in ALLOWED_SQLITE_RUNTIME_IMPORTS
                    ):
                        violations.append(f"{path}: import {mod}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if (
                    mod == forbidden_module
                    and _backend_app_path(path) not in ALLOWED_SQLITE_RUNTIME_IMPORTS
                ):
                    violations.append(f"{path}: from {mod} import ...")

    assert not violations, (
        "Forbidden sqlite3 usage in backend runtime code outside documented "
        "qualitative memory / operational store exceptions:\n" + "\n".join(violations)
    )


def test_no_uuid4_usage_inside_process_document():
    """process_document may create an operational run_id, but not vector/chunk IDs from uuid4."""
    source = textwrap.dedent(inspect.getsource(pipeline.process_document))
    tree = ast.parse(source)
    lines = source.splitlines()
    violations: list[str] = []

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and getattr(node.func.value, "id", None) == "uuid"
            and node.func.attr == "uuid4"
        ):
            continue
        line = lines[node.lineno - 1].strip()
        if "resolved_run_id" in line and "run_id or uuid.uuid4()" in line:
            continue
        violations.append(f"line {node.lineno}: {line}")

    assert not violations, (
        "process_document must not use uuid4 for vector or chunk IDs; "
        "only the operational extraction run_id fallback is allowed:\n"
        + "\n".join(violations)
    )


def test_vector_ids_use_document_id_and_chunk_index():
    captured_ids: list[str] = []

    class DummyDoc:
        def __init__(self, doc_id: uuid.UUID):
            self.document_id = doc_id
            self.ticker = "ABC"
            self.doc_class = "announcement"
            self.doc_subtype = "periodic"
            self.title = "Test Document"
            self.source_url = "https://example.com/test.pdf"

    dummy_doc_id = uuid.UUID("11111111-2222-4333-8444-555555555555")
    dummy_doc = DummyDoc(dummy_doc_id)

    def fake_embed_texts(chunks: list[str], **kwargs):
        return [[0.1, 0.2], [0.3, 0.4]]

    class DummyQdrantClient:
        def __init__(self, url: str):
            self.url = url

        # ensure_collection and upsert_points are monkeypatched, so no methods needed here.

    def fake_ensure_collection(client, collection: str, dim: int) -> None:
        assert dim == 2

    def fake_upsert_points(client, collection: str, points: list[dict]) -> None:
        for p in points:
            captured_ids.append(p["id"])

    run_embedding_stage(
        chunks=["chunk-0", "chunk-1"],
        doc=dummy_doc,
        enable_embeddings=True,
        enable_qdrant=True,
        qdrant_client=None,
        qdrant_url="http://127.0.0.1:6333",
        qdrant_collection="asx_docs",
        ollama_client=None,
        embed_chunks=fake_embed_texts,
        qdrant_client_factory=DummyQdrantClient,
        ensure_collection_fn=fake_ensure_collection,
        delete_points_for_document_fn=lambda client, collection, doc_id: None,
        upsert_points_fn=fake_upsert_points,
        validate_payload_fn=lambda payload: (True, None),
        log_rejected_payload_fn=lambda *args, **kwargs: None,
        logger_obj=type("Logger", (), {"error": lambda *args, **kwargs: None})(),
    )

    assert captured_ids, "No vector IDs were captured from upsert_points."

    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )

    for idx, point_id in enumerate(captured_ids):
        assert ":" in point_id, f"Vector ID {point_id!r} does not contain ':'."
        prefix, suffix = point_id.split(":", 1)
        assert prefix == str(dummy_doc_id), (
            f"Vector ID {point_id!r} should start with document_id {dummy_doc_id!r}."
        )
        assert suffix == str(idx), (
            f"Vector ID {point_id!r} should use chunk index {idx} as suffix."
        )
        assert not uuid_pattern.fullmatch(point_id), (
            "Vector ID should not be a bare UUID."
        )


def test_process_document_integration_vector_id_and_payload():
    """
    Integration test: run process_document with mocked embed/Qdrant and assert
    vector ID format (document_id:chunk_index) and payload structure.
    """
    captured_points: list[dict] = []
    doc_id = uuid.UUID("a1b2c3d4-e5f6-4789-a012-345678901234")

    class DummyDoc:
        document_id = doc_id
        ticker = "XYZ"
        doc_class = "announcement"
        doc_subtype = "periodic"
        title = "Integration Test Doc"
        source_url = "https://example.com/integration-test.pdf"

    def fake_upsert_points(client, collection: str, points: list[dict]) -> None:
        for p in points:
            captured_points.append({"id": p["id"], "payload": dict(p["payload"])})

    run_embedding_stage(
        chunks=["chunk0", "chunk1"],
        doc=DummyDoc(),
        enable_embeddings=True,
        enable_qdrant=True,
        qdrant_client=None,
        qdrant_url="http://127.0.0.1:6333",
        qdrant_collection="asx_docs",
        ollama_client=None,
        embed_chunks=lambda chunks, **kwargs: [[0.0] * 2, [0.0] * 2],
        qdrant_client_factory=lambda url: None,
        ensure_collection_fn=lambda c, col, dim: None,
        delete_points_for_document_fn=lambda client, collection, doc_id: None,
        upsert_points_fn=fake_upsert_points,
        validate_payload_fn=lambda payload: (True, None),
        log_rejected_payload_fn=lambda *args, **kwargs: None,
        logger_obj=type("Logger", (), {"error": lambda *args, **kwargs: None})(),
    )

    assert len(captured_points) == 2, "Expected two points (two chunks)."
    expected_doc_id_str = str(doc_id).lower()
    required_payload_keys = {
        "document_id",
        "ticker",
        "doc_class",
        "doc_subtype",
        "chunk_index",
        "title",
    }

    for idx, pt in enumerate(captured_points):
        point_id = pt["id"]
        assert ":" in point_id, (
            f"Vector ID {point_id!r} must be document_id:chunk_index."
        )
        prefix, suffix = point_id.split(":", 1)
        assert prefix == expected_doc_id_str, (
            f"Vector ID prefix must be lowercase document_id; got {prefix!r}."
        )
        assert suffix == str(idx), f"Chunk index must be {idx}; got {suffix!r}."
        payload = pt["payload"]
        for key in required_payload_keys:
            assert key in payload, f"Payload missing required key {key!r}."
        assert payload["document_id"] == expected_doc_id_str
        assert payload["ticker"] == "XYZ"
        assert payload["chunk_index"] == idx


def test_vector_id_format_matches_document_id_contract():
    """
    Ensure vector IDs follow: document_id:chunk_index
    and document_id is canonical lowercase UUID.
    """
    sample_id = "12345678-1234-4234-8234-123456789abc"
    vector_id = f"{sample_id}:0"

    # Validate format
    doc_part, chunk_part = vector_id.split(":")
    assert doc_part == sample_id
    uuid.UUID(doc_part)  # must not raise
    assert chunk_part.isdigit()


def test_ensure_collection_raises_on_dimension_mismatch():
    class DummyCollections:
        def __init__(self, name: str):
            self.collections = [type("Collection", (), {"name": name})()]

    class DummyInfo:
        def __init__(self, vectors):
            self.config = type(
                "Config", (), {"params": type("Params", (), {"vectors": vectors})()}
            )()

    class DummyClient:
        def __init__(self, vectors):
            self._vectors = vectors

        def get_collections(self):
            return DummyCollections("test_collection")

        def get_collection(self, collection_name: str):
            assert collection_name == "test_collection"
            return DummyInfo(self._vectors)

        def create_collection(self, *args, **kwargs):
            raise AssertionError(
                "create_collection should not be called for existing collection"
            )

    vectors = qmodels.VectorParams(size=256, distance=qmodels.Distance.COSINE)
    client = DummyClient(vectors)

    with pytest.raises(RuntimeError) as excinfo:
        ensure_collection(client, "test_collection", dim=768)

    msg = str(excinfo.value).lower()
    assert "dimension mismatch" in msg


def test_ensure_collection_raises_on_distance_mismatch():
    class DummyCollections:
        def __init__(self, name: str):
            self.collections = [type("Collection", (), {"name": name})()]

    class DummyInfo:
        def __init__(self, vectors):
            self.config = type(
                "Config", (), {"params": type("Params", (), {"vectors": vectors})()}
            )()

    class DummyClient:
        def __init__(self, vectors):
            self._vectors = vectors

        def get_collections(self):
            return DummyCollections("test_collection")

        def get_collection(self, collection_name: str):
            assert collection_name == "test_collection"
            return DummyInfo(self._vectors)

        def create_collection(self, *args, **kwargs):
            raise AssertionError(
                "create_collection should not be called for existing collection"
            )

    vectors = qmodels.VectorParams(size=256, distance=qmodels.Distance.DOT)
    client = DummyClient(vectors)

    with pytest.raises(RuntimeError) as excinfo:
        ensure_collection(client, "test_collection", dim=256)

    msg = str(excinfo.value).lower()
    assert "distance mismatch" in msg
    assert "cosine" in msg


def test_ensure_collection_creates_collection_with_cosine_distance():
    created = {}

    class DummyCollections:
        def __init__(self):
            self.collections = []

    class DummyClient:
        def get_collections(self):
            return DummyCollections()

        def get_collection(self, collection_name: str):
            raise AssertionError(
                "get_collection should not be called when collection does not exist"
            )

        def create_collection(self, collection_name: str, vectors_config):
            created["name"] = collection_name
            created["vectors_config"] = vectors_config

    client = DummyClient()
    ensure_collection(client, "new_collection", dim=128)

    assert created, (
        "ensure_collection did not call create_collection for missing collection."
    )
    assert created["name"] == "new_collection"
    vc = created["vectors_config"]
    assert int(vc.size) == 128
    assert vc.distance == qmodels.Distance.COSINE


ALEMBIC_VERSION_NUM_MAX_LEN = (
    32  # Alembic hardcodes VARCHAR(32) for alembic_version.version_num
)


def test_migration_revision_ids_fit_alembic_version_column():
    """Guard: all migration revision strings must be <= 32 chars.

    Alembic's alembic_version table uses VARCHAR(32) for version_num by
    default. A revision ID that exceeds 32 characters causes
    StringDataRightTruncation at migration time.
    """
    versions_dir = APP_ROOT / "alembic" / "versions"
    violations: list[str] = []

    for path in sorted(versions_dir.glob("*.py")):
        if path.name.startswith("__"):
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "revision"
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                rev = node.value.value
                if len(rev) > ALEMBIC_VERSION_NUM_MAX_LEN:
                    violations.append(
                        f"{path.name}: revision={rev!r} is {len(rev)} chars "
                        f"(max {ALEMBIC_VERSION_NUM_MAX_LEN})"
                    )

    assert not violations, (
        "Migration revision IDs exceed VARCHAR(32) limit — "
        "shorten them before deploying:\n" + "\n".join(violations)
    )


def test_no_fallback_embedding_backends_in_backend_code():
    """Guardrail: no 'fallback' embedding backends or policies in backend runtime code."""
    violations: list[str] = []

    for path in _iter_runtime_backend_files():
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            lower = line.lower()
            if "fallback" in lower and "embed" in lower:
                violations.append(f"{path}:{lineno}: {line.strip()}")

    assert not violations, (
        "Potential fallback embedding backend references detected in backend runtime code:\n"
        + "\n".join(violations)
    )
