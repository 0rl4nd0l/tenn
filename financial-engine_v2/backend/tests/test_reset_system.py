from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "reset_system.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("reset_system", SCRIPT_PATH)
reset_system = importlib.util.module_from_spec(SCRIPT_SPEC)
assert SCRIPT_SPEC and SCRIPT_SPEC.loader
SCRIPT_SPEC.loader.exec_module(reset_system)


def test_run_reset_dry_run_reports_counts_without_mutation():
    deletes: list[tuple[str, str]] = []

    class DummyQuery:
        def __init__(self, count_value: int) -> None:
            self._count_value = count_value

        def count(self) -> int:
            return self._count_value

        def delete(self, synchronize_session=False) -> int:
            deletes.append(("delete", str(self._count_value)))
            return self._count_value

    class DummyDbSession:
        def query(self, model):
            counts = {
                "Document": 5,
                "ExtractionRun": 7,
            }
            return DummyQuery(counts[model.__name__])

        def commit(self) -> None:
            deletes.append(("commit", "db"))

        def rollback(self) -> None:
            deletes.append(("rollback", "db"))

        def close(self) -> None:
            deletes.append(("close", "db"))

    class DummyQdrantClient:
        def get_collections(self):
            return type("Collections", (), {"collections": [type("Collection", (), {"name": "asx_docs"})()]})()

        def get_collection(self, collection_name: str):
            assert collection_name == "asx_docs"
            return type("CollectionInfo", (), {"points_count": 13})()

        def delete_collection(self, collection_name: str) -> None:
            deletes.append(("delete_collection", collection_name))

    report = reset_system.run_reset(
        dry_run=True,
        confirm=False,
        db_session_factory=lambda: DummyDbSession(),
        qdrant_client_factory=lambda: DummyQdrantClient(),
    )

    assert report["dry_run"] is True
    assert report["db_rows"]["documents"] == 5
    assert report["db_rows"]["extraction_runs"] == 7
    assert report["qdrant"]["collection_exists"] is True
    assert report["qdrant"]["points_count"] == 13
    assert report["qdrant"]["deleted"] is False
    assert report["qdrant"]["deleted_vectors"] == 0
    assert ("delete_collection", "asx_docs") not in deletes
    assert ("commit", "db") not in deletes


def test_run_reset_requires_confirm_when_not_dry_run():
    report = reset_system.run_reset(
        dry_run=False,
        confirm=False,
        db_session_factory=lambda: None,
        qdrant_client_factory=lambda: None,
    )

    assert report["ok"] is False
    assert "confirm" in report["error"].lower()
