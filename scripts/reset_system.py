from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable


LOGGER = logging.getLogger("reset_system")
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.asx_financials import ASXPeriodicFinancial, ASXRiskNote
from app.models.documents import Document
from app.models.extractions import ExtractionRun

if TYPE_CHECKING:
    from qdrant_client import QdrantClient


def _build_qdrant_client() -> "QdrantClient":
    from qdrant_client import QdrantClient

    return QdrantClient(url=settings.qdrant_url, timeout=60.0)


def _collection_exists(client: Any, collection_name: str) -> bool:
    collections = client.get_collections()
    return any(collection.name == collection_name for collection in collections.collections)


def _collection_points_count(client: Any, collection_name: str) -> int:
    try:
        info = client.get_collection(collection_name=collection_name)
    except Exception:
        return 0
    raw_points_count = getattr(info, "points_count", None)
    if raw_points_count is None:
        raw_points_count = getattr(info, "vectors_count", None)
    return int(raw_points_count or 0)


def _count_rows(db_session: Any) -> dict[str, int]:
    def _safe_count(model: Any) -> int:
        try:
            return int(db_session.query(model).count())
        except Exception:
            return 0

    return {
        "documents": _safe_count(Document),
        "extraction_runs": _safe_count(ExtractionRun),
        "financial_rows": _safe_count(ASXPeriodicFinancial),
        "risk_rows": _safe_count(ASXRiskNote),
    }


def run_reset(
    *,
    dry_run: bool,
    confirm: bool,
    collection_name: str = "asx_docs",
    db_session_factory: Callable[[], Any] = SessionLocal,
    qdrant_client_factory: Callable[[], Any] = _build_qdrant_client,
) -> dict[str, Any]:
    if not dry_run and not confirm:
        return {
            "ok": False,
            "error": "Refusing to modify system state without --confirm. Use --dry-run to inspect first.",
        }

    report: dict[str, Any] = {
        "ok": True,
        "dry_run": bool(dry_run),
        "confirmed": bool(confirm),
        "collection": collection_name,
        "qdrant": {
            "url": settings.qdrant_url,
            "collection_exists": False,
            "points_count": 0,
            "deleted": False,
            "deleted_vectors": 0,
        },
        "db_rows": {},
    }

    db = None
    try:
        client = qdrant_client_factory()
        collection_exists = _collection_exists(client, collection_name)
        report["qdrant"]["collection_exists"] = collection_exists
        points_count = _collection_points_count(client, collection_name) if collection_exists else 0
        report["qdrant"]["points_count"] = points_count
        if collection_exists:
            LOGGER.info("Qdrant collection present: %s points=%d", collection_name, points_count)
            if confirm and not dry_run:
                client.delete_collection(collection_name=collection_name)
                report["qdrant"]["deleted"] = True
                report["qdrant"]["deleted_vectors"] = points_count
                LOGGER.info("Deleted Qdrant collection: %s deleted_vectors=%d", collection_name, points_count)
        else:
            LOGGER.info("Qdrant collection already absent: %s", collection_name)

        db = db_session_factory()
        row_counts = _count_rows(db)
        report["db_rows"] = row_counts
        LOGGER.info("DB rows scheduled for reset: %s", row_counts)
        if confirm and not dry_run:
            deleted_risk = int(db.query(ASXRiskNote).delete(synchronize_session=False))
            deleted_financial = int(db.query(ASXPeriodicFinancial).delete(synchronize_session=False))
            deleted_extractions = int(db.query(ExtractionRun).delete(synchronize_session=False))
            deleted_documents = int(db.query(Document).delete(synchronize_session=False))
            db.commit()
            report["db_deleted"] = {
                "documents": deleted_documents,
                "extraction_runs": deleted_extractions,
                "financial_rows": deleted_financial,
                "risk_rows": deleted_risk,
            }
            LOGGER.info("Deleted DB rows: %s", report["db_deleted"])
        return report
    except Exception as exc:
        if db is not None:
            db.rollback()
        LOGGER.exception("Reset failed")
        return {
            "ok": False,
            "dry_run": bool(dry_run),
            "confirmed": bool(confirm),
            "collection": collection_name,
            "error": str(exc),
        }
    finally:
        if db is not None:
            db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset local RAG/Qdrant and DB ingestion state.")
    parser.add_argument("--collection", default="asx_docs", help="Qdrant collection to delete.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be deleted without mutating state.")
    parser.add_argument("--confirm", action="store_true", help="Actually delete Qdrant and DB state.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    report = run_reset(
        dry_run=bool(args.dry_run),
        confirm=bool(args.confirm),
        collection_name=str(args.collection or "asx_docs").strip() or "asx_docs",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
