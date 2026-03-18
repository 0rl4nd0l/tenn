#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.embeddings import validate_asx_docs_payload  # noqa: E402


def _iter_points(
    client: QdrantClient,
    *,
    collection_name: str,
    batch_size: int = 500,
):
    offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            yield point
        if next_offset is None:
            break
        offset = next_offset


def cleanup_asx_docs_payloads(
    client: QdrantClient,
    *,
    collection_name: str,
    delete: bool = False,
    batch_size: int = 500,
) -> dict[str, Any]:
    invalid_points: list[dict[str, Any]] = []

    for point in _iter_points(client, collection_name=collection_name, batch_size=batch_size):
        payload = dict(getattr(point, "payload", None) or {})
        is_valid, reason = validate_asx_docs_payload(payload, mode="read")
        if is_valid:
            continue
        invalid_points.append(
            {
                "point_id": getattr(point, "id", None),
                "document_id": payload.get("document_id"),
                "ticker": payload.get("ticker"),
                "title": payload.get("title"),
                "reason": reason or "payload validation failed",
            }
        )

    deleted_count = 0
    if delete and invalid_points:
        client.delete(
            collection_name=collection_name,
            points_selector=qmodels.PointIdsList(
                points=[item["point_id"] for item in invalid_points if item.get("point_id") not in (None, "")]
            ),
            wait=True,
        )
        deleted_count = len([item for item in invalid_points if item.get("point_id") not in (None, "")])

    return {
        "collection": collection_name,
        "invalid_count": len(invalid_points),
        "deleted_count": deleted_count,
        "delete_requested": bool(delete),
        "invalid_points": invalid_points,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report or delete malformed payloads from asx_docs.")
    parser.add_argument("--qdrant-url", default=str(settings.qdrant_url), help="Qdrant URL.")
    parser.add_argument(
        "--collection",
        default=str(settings.qdrant_collection),
        help="Target collection. Defaults to the configured asx_docs collection.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete malformed points after reporting them.",
    )
    parser.add_argument("--batch-size", type=int, default=500, help="Scroll batch size.")
    args = parser.parse_args()

    client = QdrantClient(url=args.qdrant_url)
    report = cleanup_asx_docs_payloads(
        client,
        collection_name=args.collection,
        delete=args.delete,
        batch_size=max(1, int(args.batch_size)),
    )

    print(f"collection={report['collection']}")
    print(f"invalid_count={report['invalid_count']}")
    print(f"delete_requested={str(report['delete_requested']).lower()}")
    print(f"deleted_count={report['deleted_count']}")
    for item in report["invalid_points"]:
        print(
            "invalid"
            f" point_id={item.get('point_id')}"
            f" document_id={item.get('document_id')}"
            f" ticker={item.get('ticker')}"
            f" title={item.get('title')}"
            f" reason={item.get('reason')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
