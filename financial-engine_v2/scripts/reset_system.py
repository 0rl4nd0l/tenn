#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
RUNTIME_EMBEDDING_MODEL_FILE = REPO_ROOT / "reports" / "runtime_embedding_model.txt"


def _project_db_files() -> list[Path]:
    files = sorted(path for path in DATA_ROOT.glob("*.db") if path.is_file())
    return files


def _count_sqlite_rows(path: Path) -> dict[str, int]:
    counts = {
        "documents": 0,
        "extraction_runs": 0,
        "asx_periodic_financials": 0,
        "asx_risk_notes": 0,
    }
    if not path.exists():
        return counts
    conn = sqlite3.connect(str(path))
    try:
        for table_name in counts:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            except sqlite3.DatabaseError:
                row = None
            counts[table_name] = int((row or [0])[0] or 0)
    finally:
        conn.close()
    return counts


def _qdrant_state(client: QdrantClient, collection_name: str) -> dict[str, Any]:
    collections = client.get_collections()
    existing = {item.name for item in collections.collections}
    if collection_name not in existing:
        return {
            "collection": collection_name,
            "collection_exists": False,
            "points_count": 0,
            "deleted": False,
        }
    info = client.get_collection(collection_name=collection_name)
    points_count = getattr(info, "points_count", None)
    if points_count is None:
        points_count = getattr(info, "vectors_count", None)
    return {
        "collection": collection_name,
        "collection_exists": True,
        "points_count": int(points_count or 0),
        "deleted": False,
    }


def run_reset(
    *,
    dry_run: bool = True,
    confirm: bool = False,
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "asx_docs",
    db_files: list[Path] | None = None,
    qdrant_client_factory=None,
) -> dict[str, Any]:
    files = [Path(path) for path in (db_files or _project_db_files())]
    db_report = {
        "files": [],
        "deleted_files": [],
    }
    for path in files:
        db_report["files"].append(
            {
                "path": str(path),
                "exists": path.exists(),
                "rows": _count_sqlite_rows(path),
            }
        )

    client_factory = qdrant_client_factory or (lambda: QdrantClient(url=qdrant_url))
    client = client_factory()
    qdrant_report = _qdrant_state(client, collection_name)
    qdrant_report["deleted_vectors"] = int(qdrant_report["points_count"])

    report = {
        "ok": True,
        "dry_run": bool(dry_run),
        "confirmed": bool(confirm),
        "db": db_report,
        "qdrant": qdrant_report,
        "runtime_embedding_model_file": str(RUNTIME_EMBEDDING_MODEL_FILE),
        "error": "",
    }

    if dry_run:
        qdrant_report["deleted_vectors"] = 0
        return report
    if not confirm:
        report["ok"] = False
        report["error"] = "confirm flag required for destructive reset"
        qdrant_report["deleted_vectors"] = 0
        return report

    if qdrant_report["collection_exists"]:
        client.delete_collection(collection_name=collection_name)
        qdrant_report["deleted"] = True

    for path in files:
        if not path.exists():
            continue
        path.unlink()
        db_report["deleted_files"].append(str(path))

    if RUNTIME_EMBEDDING_MODEL_FILE.exists():
        RUNTIME_EMBEDDING_MODEL_FILE.unlink()

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset local Financial Engine state.")
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--collection", default="asx_docs")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required to delete the configured Qdrant collection and local sqlite files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_reset(
        dry_run=not bool(args.confirm),
        confirm=bool(args.confirm),
        qdrant_url=str(args.qdrant_url),
        collection_name=str(args.collection),
    )
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
