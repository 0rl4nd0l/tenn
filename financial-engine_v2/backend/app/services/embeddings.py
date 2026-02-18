from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
def ensure_collection(client:QdrantClient, collection:str, dim:int)->None:
    existing=[c.name for c in client.get_collections().collections]
    if collection in existing:
        return
    client.create_collection(collection_name=collection, vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE))
def upsert_points(client:QdrantClient, collection:str, points:list[dict])->None:
    client.upsert(collection_name=collection, points=[qmodels.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points])
