#!/usr/bin/env python3
"""Read-only inspection of a Qdrant RAG collection.

Prints collection metadata, point count by ticker, duplicate point IDs,
missing chunk_index sequences per document, and payload/id integrity violations.
Does not modify the collection.
"""
from __future__ import annotations

import sys
import uuid
from collections import defaultdict
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.embeddings import coerce_qdrant_point_id  # noqa: E402


def _get_distance_name(distance) -> str:
    if distance is None:
        return "unknown"
    if hasattr(distance, "value"):
        return str(distance.value)
    return str(distance)


def _is_canonical_uuid(s) -> bool:
    """Return True iff s is a canonical UUID string (lowercase hex with hyphens)."""
    if not isinstance(s, str):
        return False
    try:
        u = uuid.UUID(s)
        return str(u) == s
    except (ValueError, TypeError):
        return False


def _scroll_all_points(client: QdrantClient, collection_name: str, batch_size: int = 500):
    """Scroll through all points in the collection (read-only). Yields (point_id, payload)."""
    offset = None
    while True:
        result, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in result:
            yield point.id, (point.payload or {})
        if next_offset is None:
            break
        offset = next_offset


def main() -> None:
    collection_name = settings.qdrant_collection
    client = QdrantClient(url=settings.qdrant_url)

    try:
        info = client.get_collection(collection_name=collection_name)
    except Exception as e:
        print(f"Error: Collection '{collection_name}' not found or unreachable: {e}")
        sys.exit(1)

    # Collection metadata
    vectors_config = getattr(info.config, "params", None)
    vectors = getattr(vectors_config, "vectors", None) if vectors_config else None
    size = None
    distance = None
    if isinstance(vectors, qmodels.VectorParams):
        size = int(vectors.size)
        distance = vectors.distance
    elif isinstance(vectors, dict):
        first = next(iter(vectors.values()), None)
        if isinstance(first, qmodels.VectorParams):
            size = int(first.size)
            distance = first.distance

    try:
        count_result = client.count(
            collection_name=collection_name,
            exact=True,
        )
        total_count = int(getattr(count_result, "count", 0) or 0)
    except Exception:
        total_count = int(getattr(info, "points_count", 0) or 0)

    print("=== Collection metadata ===")
    print(f"  collection name:  {collection_name}")
    print(f"  vector dimension: {size if size is not None else 'unknown'}")
    print(f"  distance metric:  {_get_distance_name(distance)}")
    print(f"  total point count: {total_count}")
    print()

    if total_count == 0:
        print("Collection is empty. No ticker groups or integrity checks.")
        return

    # Gather data in one pass
    ticker_counts: dict[str, int] = defaultdict(int)
    seen_ids: set[str | int] = set()
    duplicate_ids: list[str | int] = []
    doc_chunks: dict[str, list[int]] = defaultdict(list)
    document_id_not_canonical = []  # (point_id_str, document_id_value)
    logical_vector_id_mismatch = []  # (point_id_str, expected_logical_id, payload_logical_id)
    physical_point_id_mismatch = []  # (point_id_str, expected_logical_id)

    for point_id, payload in _scroll_all_points(client, collection_name):
        point_id_str = str(point_id)

        # Count by ticker
        ticker = payload.get("ticker")
        if ticker is not None:
            ticker_counts[str(ticker)] += 1
        else:
            ticker_counts["<no ticker>"] += 1

        # Duplicate point IDs
        if point_id in seen_ids:
            duplicate_ids.append(point_id)
        else:
            seen_ids.add(point_id)

        # document_id must be canonical UUID. The logical vector ID remains
        # document_id:chunk_index even when the physical Qdrant point ID is a
        # deterministic UUIDv5 storage ID.
        doc_id_raw = payload.get("document_id")
        if doc_id_raw is None or not _is_canonical_uuid(str(doc_id_raw)):
            document_id_not_canonical.append((point_id_str, str(doc_id_raw) if doc_id_raw is not None else None))
        else:
            doc_id = str(doc_id_raw)
            chunk_idx_raw = payload.get("chunk_index")
            try:
                chunk_idx_int = int(chunk_idx_raw)
            except (TypeError, ValueError):
                chunk_idx_int = None
            if chunk_idx_int is not None:
                expected_logical_id = f"{doc_id}:{chunk_idx_int}"
                payload_logical_id = str(payload.get("logical_vector_id") or "").strip()
                if payload_logical_id != expected_logical_id:
                    logical_vector_id_mismatch.append(
                        (point_id_str, expected_logical_id, payload_logical_id or "<missing>")
                    )
                accepted_physical_ids = {
                    expected_logical_id,
                    str(coerce_qdrant_point_id(expected_logical_id)),
                }
                if point_id_str not in accepted_physical_ids:
                    physical_point_id_mismatch.append((point_id_str, expected_logical_id))

        # Chunk indices per document
        doc_id = payload.get("document_id")
        chunk_idx = payload.get("chunk_index")
        if doc_id is not None and chunk_idx is not None:
            try:
                doc_chunks[str(doc_id)].append(int(chunk_idx))
            except (TypeError, ValueError):
                pass

    # Missing chunk_index sequences per document
    doc_gaps: dict[str, list[int]] = {}
    for doc_id, indices in doc_chunks.items():
        if not indices:
            continue
        indices_sorted = sorted(set(indices))
        expected = set(range(indices_sorted[-1] + 1))
        missing = sorted(expected - set(indices_sorted))
        if missing:
            doc_gaps[doc_id] = missing

    # Print ticker counts
    print("=== Count by ticker ===")
    for ticker in sorted(ticker_counts.keys()):
        print(f"  {ticker}: {ticker_counts[ticker]}")
    print()

    # Duplicate IDs
    print("=== Duplicate point IDs ===")
    if not duplicate_ids:
        print("  None detected.")
    else:
        for pid in duplicate_ids[:50]:
            print(f"  {pid}")
        if len(duplicate_ids) > 50:
            print(f"  ... and {len(duplicate_ids) - 50} more (total {len(duplicate_ids)} duplicates)")
    print()

    # Missing chunk_index per document
    print("=== Missing chunk_index sequences (per document) ===")
    if not doc_gaps:
        print("  None detected (all documents have contiguous chunk indices 0..N-1).")
    else:
        for doc_id in sorted(doc_gaps.keys())[:20]:
            missing = doc_gaps[doc_id]
            preview = missing[:10]
            extra = f", ... +{len(missing) - 10} more" if len(missing) > 10 else ""
            print(f"  {doc_id}: missing indices {preview}{extra}")
        if len(doc_gaps) > 20:
            print(f"  ... and {len(doc_gaps) - 20} more documents with gaps")
    print()

    # document_id not canonical UUID
    print("=== document_id not canonical UUID ===")
    if not document_id_not_canonical:
        print("  None (all points have payload[\"document_id\"] as canonical UUID string).")
    else:
        for point_id_str, doc_val in document_id_not_canonical[:30]:
            label = repr(doc_val) if doc_val is not None else "<missing>"
            print(f"  point_id={point_id_str!r}  document_id={label}")
        if len(document_id_not_canonical) > 30:
            print(f"  ... and {len(document_id_not_canonical) - 30} more (total {len(document_id_not_canonical)} violations)")
    print()

    # logical_vector_id missing or mismatch
    print("=== logical_vector_id missing or mismatch ===")
    if not logical_vector_id_mismatch:
        print("  None (all payload logical_vector_id values match document_id:chunk_index).")
    else:
        for point_id_str, expected, actual in logical_vector_id_mismatch[:30]:
            print(f"  point_id={point_id_str!r}  expected_logical_id={expected!r}  logical_vector_id={actual!r}")
        if len(logical_vector_id_mismatch) > 30:
            print(
                f"  ... and {len(logical_vector_id_mismatch) - 30} more "
                f"(total {len(logical_vector_id_mismatch)} violations)"
            )
    print()

    # physical point ID mismatch
    print("=== physical point ID mismatch ===")
    if not physical_point_id_mismatch:
        print("  None (all point IDs are literal logical IDs or deterministic UUIDv5 physical IDs).")
    else:
        for point_id_str, expected in physical_point_id_mismatch[:30]:
            print(f"  point_id={point_id_str!r}  expected_logical_id={expected!r}")
        if len(physical_point_id_mismatch) > 30:
            print(
                f"  ... and {len(physical_point_id_mismatch) - 30} more "
                f"(total {len(physical_point_id_mismatch)} violations)"
            )
    print()

    # Summary table
    print("=== Summary ===")
    print(f"  Total points:        {total_count}")
    print(f"  Unique point IDs:    {len(seen_ids)}")
    print(f"  Duplicate IDs:       {len(duplicate_ids)}")
    print(f"  Documents with gaps: {len(doc_gaps)}")
    print(f"  document_id not canonical UUID: {len(document_id_not_canonical)}")
    print(f"  logical_vector_id mismatch:     {len(logical_vector_id_mismatch)}")
    print(f"  physical point ID mismatch:     {len(physical_point_id_mismatch)}")
    print(f"  Tickers:             {len(ticker_counts)}")


if __name__ == "__main__":
    main()
