import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.services.embeddings import coerce_qdrant_point_id, upsert_points


def test_upsert_points_accepts_document_chunk_id_in_local_mode():
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="test_collection",
        vectors_config=qmodels.VectorParams(size=2, distance=qmodels.Distance.COSINE),
    )

    doc_id = "a3d7d2b0-1111-2222-3333-abcdefabcdef"
    points = [
        {
            "id": f"{doc_id}:0",
            "vector": [0.1, 0.2],
            "payload": {
                "document_id": doc_id,
                "ticker": "ABC",
                "doc_class": "announcement",
                "doc_subtype": "periodic",
                "chunk_index": 0,
                "title": "Test doc",
            },
        }
    ]

    upsert_points(client, "test_collection", points)

    records, _ = client.scroll(collection_name="test_collection", limit=1, with_payload=True)
    assert len(records) == 1
    logical_vector_id = f"{doc_id}:0"
    assert str(records[0].id) == str(uuid.uuid5(uuid.NAMESPACE_URL, logical_vector_id))
    payload = records[0].payload or {}
    assert payload.get("document_id") == doc_id
    assert payload.get("chunk_index") == 0
    assert payload.get("logical_vector_id") == logical_vector_id


def test_coerce_qdrant_point_id_is_deterministic_uuid5_for_logical_id():
    logical_vector_id = "a3d7d2b0-1111-2222-3333-abcdefabcdef:4"

    first = coerce_qdrant_point_id(logical_vector_id)
    second = coerce_qdrant_point_id(logical_vector_id)

    assert first == second
    assert first == str(uuid.uuid5(uuid.NAMESPACE_URL, logical_vector_id))
    assert first != logical_vector_id
