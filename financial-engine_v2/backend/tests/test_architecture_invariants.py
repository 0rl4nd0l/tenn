import ast
import inspect
import re
import uuid
from pathlib import Path

import pytest
from qdrant_client.http import models as qmodels

from app.services.embeddings import ensure_collection
from app.services import pipeline


BACKEND_ROOT = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_ROOT / "app"


def _iter_runtime_backend_files():
    """Yield Python files that are part of backend runtime code (exclude tests and alembic)."""
    for path in APP_ROOT.rglob("*.py"):
        parts = set(path.parts)
        if "tests" in parts:
            continue
        if "alembic" in parts:
            continue
        yield path


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
                    if mod == forbidden_module:
                        violations.append(f"{path}: import {mod}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if mod == forbidden_module:
                    violations.append(f"{path}: from {mod} import ...")

    assert not violations, (
        "Forbidden sqlite3 usage in backend runtime code:\n" + "\n".join(violations)
    )


def test_no_uuid4_usage_inside_process_document():
    """process_document must not use uuid.uuid4() for vector or chunk IDs; uuid.UUID() for validation is allowed."""
    code = pipeline.process_document.__code__
    names = set(code.co_names)
    forbidden = {"uuid4"}
    found = forbidden & names
    assert not found, (
        "process_document must not reference uuid4 (deterministic vector IDs only; uuid.UUID for validation is allowed); "
        f"found: {sorted(found)}, all names: {sorted(names)}"
    )


def test_vector_ids_use_document_id_and_chunk_index(monkeypatch):
    captured_ids: list[str] = []

    class DummyDoc:
        def __init__(self, doc_id: uuid.UUID):
            self.document_id = doc_id
            self.ticker = "ABC"
            self.doc_class = "announcement"
            self.doc_subtype = "periodic"
            self.title = "Test Document"
            self.pdf_path = "/tmp/test.pdf"
            self.announcement_type = None

    dummy_doc_id = uuid.uuid4()
    dummy_doc = DummyDoc(dummy_doc_id)

    class DummyQuery:
        def __init__(self, result):
            self._result = result

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self._result

    class DummySession:
        def __init__(self, result):
            self._result = result

        def query(self, model):
            assert model is pipeline.Document
            return DummyQuery(self._result)

        def add(self, obj):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    def fake_session_local():
        return DummySession(dummy_doc)

    def fake_extract_text_from_pdf(path: str) -> str:
        return "This is a test document."

    def fake_simple_chunk(text: str, max_chars: int):
        return ["chunk-0", "chunk-1"]

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

    monkeypatch.setattr(pipeline, "SessionLocal", fake_session_local)
    monkeypatch.setattr(pipeline, "chunk_prose_sections", lambda doc: ["chunk-0", "chunk-1"])
    monkeypatch.setattr(pipeline, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(pipeline, "QdrantClient", DummyQdrantClient)
    monkeypatch.setattr(pipeline, "ensure_collection", fake_ensure_collection)
    monkeypatch.setattr(pipeline, "delete_points_for_document", lambda client, collection, doc_id: None)
    monkeypatch.setattr(pipeline, "upsert_points", fake_upsert_points)

    # Ensure embeddings path is enabled but extraction path is disabled for test simplicity.
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", False, raising=False)

    pipeline.process_document(str(dummy_doc_id))

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
        assert not uuid_pattern.fullmatch(
            point_id
        ), "Vector ID should not be a bare UUID."


def test_process_document_integration_vector_id_and_payload(monkeypatch):
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
        pdf_path = "/tmp/integration_test.pdf"
        announcement_type = None

    class DummyQuery:
        def __init__(self, result):
            self._result = result

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self._result

    class DummySession:
        def __init__(self):
            self._result = DummyDoc()

        def query(self, model):
            return DummyQuery(self._result)

        def add(self, obj):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    def fake_session_local():
        return DummySession()

    def fake_upsert_points(client, collection: str, points: list[dict]) -> None:
        for p in points:
            captured_points.append({"id": p["id"], "payload": dict(p["payload"])})

    monkeypatch.setattr(pipeline, "SessionLocal", fake_session_local)
    monkeypatch.setattr(pipeline, "chunk_prose_sections", lambda doc: ["chunk0", "chunk1"])
    monkeypatch.setattr(pipeline, "embed_texts", lambda chunks, **kwargs: [[0.0] * 2, [0.0] * 2])
    monkeypatch.setattr(pipeline, "QdrantClient", lambda url: None)
    monkeypatch.setattr(pipeline, "ensure_collection", lambda c, col, dim: None)
    monkeypatch.setattr(pipeline, "delete_points_for_document", lambda client, collection, doc_id: None)
    monkeypatch.setattr(pipeline, "upsert_points", fake_upsert_points)
    monkeypatch.setattr(pipeline.settings, "enable_embeddings", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_qdrant", True, raising=False)
    monkeypatch.setattr(pipeline.settings, "enable_extraction", False, raising=False)

    pipeline.process_document(str(doc_id))

    assert len(captured_points) == 2, "Expected two points (two chunks)."
    expected_doc_id_str = str(doc_id).lower()
    required_payload_keys = {"document_id", "ticker", "doc_class", "doc_subtype", "chunk_index", "title"}

    for idx, pt in enumerate(captured_points):
        point_id = pt["id"]
        assert ":" in point_id, f"Vector ID {point_id!r} must be document_id:chunk_index."
        prefix, suffix = point_id.split(":", 1)
        assert prefix == expected_doc_id_str, f"Vector ID prefix must be lowercase document_id; got {prefix!r}."
        assert suffix == str(idx), f"Chunk index must be {idx}; got {suffix!r}."
        payload = pt["payload"]
        for key in required_payload_keys:
            assert key in payload, f"Payload missing required key {key!r}."
        assert payload["document_id"] == expected_doc_id_str
        assert payload["ticker"] == "XYZ"
        assert payload["chunk_index"] == idx


def test_vector_id_format_matches_document_id_contract(monkeypatch):
    """
    Ensure vector IDs follow: document_id:chunk_index
    and document_id is canonical lowercase UUID.
    """
    sample_id = str(uuid.uuid4()).lower()
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
            self.config = type("Config", (), {"params": type("Params", (), {"vectors": vectors})()})()

    class DummyClient:
        def __init__(self, vectors):
            self._vectors = vectors

        def get_collections(self):
            return DummyCollections("test_collection")

        def get_collection(self, collection_name: str):
            assert collection_name == "test_collection"
            return DummyInfo(self._vectors)

        def create_collection(self, *args, **kwargs):
            raise AssertionError("create_collection should not be called for existing collection")

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
            self.config = type("Config", (), {"params": type("Params", (), {"vectors": vectors})()})()

    class DummyClient:
        def __init__(self, vectors):
            self._vectors = vectors

        def get_collections(self):
            return DummyCollections("test_collection")

        def get_collection(self, collection_name: str):
            assert collection_name == "test_collection"
            return DummyInfo(self._vectors)

        def create_collection(self, *args, **kwargs):
            raise AssertionError("create_collection should not be called for existing collection")

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
            raise AssertionError("get_collection should not be called when collection does not exist")

        def create_collection(self, collection_name: str, vectors_config):
            created["name"] = collection_name
            created["vectors_config"] = vectors_config

    client = DummyClient()
    ensure_collection(client, "new_collection", dim=128)

    assert created, "ensure_collection did not call create_collection for missing collection."
    assert created["name"] == "new_collection"
    vc = created["vectors_config"]
    assert int(vc.size) == 128
    assert vc.distance == qmodels.Distance.COSINE


ALEMBIC_VERSION_NUM_MAX_LEN = 32  # Alembic hardcodes VARCHAR(32) for alembic_version.version_num


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
