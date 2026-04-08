from __future__ import annotations

import logging
from urllib.parse import urlparse
import uuid
from collections.abc import Mapping
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.services.llamacpp_embeddings import (
    llamacpp_embed,
    probe_llamacpp_embeddings,
)
from app.services.llamacpp_runtime import resolve_embedding_runtime_config
from app.services.ollama import ollama_embed, probe_ollama_embeddings


logger = logging.getLogger(__name__)


def _normalize_runtime_base_url(value: str | None) -> str:
    normalized = str(value or "").strip().rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[: -len("/v1")]
    return normalized.rstrip("/")


def _extract_runtime_host_port(value: str | None) -> tuple[str, int | None]:
    normalized = _normalize_runtime_base_url(value)
    if not normalized:
        return "", None
    parsed = urlparse(normalized)
    return str(parsed.hostname or "").strip().lower(), parsed.port


def _looks_like_ollama_runtime(base_url: str | None) -> bool:
    hostname, port = _extract_runtime_host_port(base_url)
    if port == 11434:
        return True
    return hostname in {"ollama", "host.docker.internal"} and port is None


def _resolve_embedding_backend(
    *,
    provider: str | None,
    base_url: str | None,
) -> str:
    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider == "ollama":
        return "ollama"
    if normalized_provider == "local" and _looks_like_ollama_runtime(base_url):
        return "ollama"
    return "llamacpp"


def _extract_vector_params(candidate: Any) -> tuple[int | None, Any | None]:
    if candidate is None:
        return None, None

    if isinstance(candidate, qmodels.VectorParams):
        return int(candidate.size), candidate.distance

    size = getattr(candidate, "size", None)
    distance = getattr(candidate, "distance", None)
    if size is not None:
        try:
            return int(size), distance
        except (TypeError, ValueError):
            pass

    if isinstance(candidate, Mapping):
        first = next(iter(candidate.values()), None)
        return _extract_vector_params(first)

    return None, None


def is_qdrant_vector_dimension_mismatch_error(exc: Exception) -> bool:
    message = str(exc or "").strip().lower()
    return "vector dimension error" in message or "dimension mismatch" in message


def _is_canonical_document_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return value == str(uuid.UUID(value))
    except (ValueError, TypeError):
        return False


def validate_asx_docs_payload(
    payload: Any,
    *,
    mode: str = "write",
) -> tuple[bool, str | None]:
    if not isinstance(payload, dict):
        return False, "payload is not a dict"

    document_id = payload.get("document_id")
    ticker = payload.get("ticker")
    chunk_index = payload.get("chunk_index")

    if document_id is None:
        return False, "payload field document_id is None"
    if not _is_canonical_document_id(str(document_id)):
        return False, "document_id is not a canonical UUID"
    if ticker is None or not str(ticker).strip():
        return False, "payload field ticker is missing"
    if chunk_index is None:
        return False, "payload field chunk_index is None"

    if mode == "read":
        return True, None
    if mode != "write":
        raise ValueError(f"unsupported payload validation mode: {mode}")

    try:
        int(chunk_index)
    except (TypeError, ValueError):
        return False, "chunk_index is not an integer"
    return True, None


def validate_payload(payload: Any, *, mode: str = "write") -> tuple[bool, str | None]:
    return validate_asx_docs_payload(payload, mode=mode)


def log_rejected_payload(
    reason: str,
    *,
    payload: Any = None,
    collection: str | None = None,
    point_id: Any = None,
    action: str = "rejected",
    source: Any = None,
) -> None:
    details = payload if isinstance(payload, dict) else {}
    logger.error(
        "Rejected Qdrant payload: reason=%s action=%s collection=%s point_id=%s document_id=%s ticker=%s title=%s source=%s",
        reason,
        action,
        collection or "",
        point_id if point_id is not None else "",
        details.get("document_id"),
        details.get("ticker"),
        details.get("title"),
        source if source not in (None, "") else details.get("source") or details.get("source_url") or "",
        extra={
            "collection": collection or "",
            "point_id": point_id if point_id is not None else "",
            "document_id": details.get("document_id"),
            "ticker": details.get("ticker"),
            "title": details.get("title"),
            "reason": reason,
            "action": action,
            "source": source if source not in (None, "") else details.get("source") or details.get("source_url") or "",
        },
    )


def log_invalid_asx_docs_payload(
    reason: str,
    *,
    payload: Any = None,
    collection: str | None = None,
    point_id: Any = None,
    action: str = "skipped",
    source: Any = None,
) -> None:
    details = payload if isinstance(payload, dict) else {}
    logger.warning(
        "Invalid asx_docs payload %s: reason=%s collection=%s point_id=%s document_id=%s ticker=%s title=%s source=%s",
        action,
        reason,
        collection or "",
        point_id if point_id is not None else "",
        details.get("document_id"),
        details.get("ticker"),
        details.get("title"),
        source if source not in (None, "") else details.get("source") or details.get("source_url") or "",
        extra={
            "collection": collection or "",
            "point_id": point_id if point_id is not None else "",
            "document_id": details.get("document_id"),
            "ticker": details.get("ticker"),
            "title": details.get("title"),
            "reason": reason,
            "action": action,
            "source": source if source not in (None, "") else details.get("source") or details.get("source_url") or "",
        },
    )


def resolve_llamacpp_embedding_config(
    *,
    llm_url: str | None = None,
    model: str | None = None,
) -> tuple[str, str]:
    base_url = str(llm_url or "").strip()
    if base_url.lower().startswith("cpu://"):
        requested_model = str(model or "").strip()
        normalized_model = requested_model.lower()
        resolved_model = requested_model
        if normalized_model.startswith("sentence-transformers") or normalized_model.startswith("local:"):
            resolved_model = None
        logger.warning(
            "Ignoring non-HTTP embedding base_url=%s from routing config and resolving default embedding runtime.",
            base_url,
        )
        return resolve_embedding_runtime_config(
            base_url=None,
            model=resolved_model or None,
        )

    return resolve_embedding_runtime_config(base_url=llm_url, model=model)


def embed_texts_batched(
    texts: list[str],
    *,
    llm_url: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    batch_size: int | None = None,
    timeout: float = 120.0,
    client: Optional[Any] = None,
) -> list[list[float]]:
    if not texts:
        return []

    resolved_base_url, resolved_model = resolve_llamacpp_embedding_config(
        llm_url=llm_url,
        model=model,
    )
    embedding_backend = _resolve_embedding_backend(
        provider=provider,
        base_url=resolved_base_url,
    )
    effective_batch_size = max(1, int(batch_size or settings.embedding_batch_size or 32))

    if embedding_backend == "ollama":
        probe_ollama_embeddings(
            resolved_base_url,
            resolved_model,
            timeout=min(float(timeout), 30.0),
            client=client,
        )
    else:
        probe_llamacpp_embeddings(
            resolved_base_url,
            resolved_model,
            timeout=min(float(timeout), 30.0),
            client=client,
        )

    vectors: list[list[float]] = []
    for index in range(0, len(texts), effective_batch_size):
        batch = texts[index : index + effective_batch_size]
        if embedding_backend == "ollama":
            vectors.extend(
                ollama_embed(
                    resolved_base_url,
                    resolved_model,
                    batch,
                    timeout=float(timeout),
                    client=client,
                )
            )
            continue
        vectors.extend(
            llamacpp_embed(
                resolved_base_url,
                resolved_model,
                batch,
                timeout=float(timeout),
                client=client,
                verify_models=False,
            )
        )
    return vectors


def get_embedding_runtime_diagnostics() -> dict[str, Any]:
    base_url, model = resolve_llamacpp_embedding_config()
    embedding_backend = _resolve_embedding_backend(
        provider=None,
        base_url=base_url,
    )
    diagnostics: dict[str, Any] = {
        "base_url": base_url,
        "model": model,
        "provider": embedding_backend,
        "batch_size": int(max(1, settings.embedding_batch_size)),
        "qdrant_url": str(settings.qdrant_url),
        "qdrant_collection": str(settings.qdrant_collection),
    }

    try:
        if embedding_backend == "ollama":
            diagnostics["probe"] = probe_ollama_embeddings(base_url, model)
        else:
            diagnostics["probe"] = probe_llamacpp_embeddings(base_url, model)
    except Exception as exc:
        diagnostics["probe"] = {
            "base_url": base_url,
            "model": model,
            "ok": False,
            "error": str(exc),
        }

    return diagnostics


def verify_qdrant(qdrant_url: str | None = None) -> QdrantClient:
    resolved_qdrant_url = str(qdrant_url or settings.qdrant_url).strip()
    client = QdrantClient(url=resolved_qdrant_url, timeout=60.0)
    try:
        client.get_collections()
    except Exception as exc:
        raise RuntimeError(f"Qdrant unavailable at {resolved_qdrant_url}: {exc}") from exc
    return client


def get_qdrant_collection_vector_config(
    client: QdrantClient,
    collection: str,
) -> dict[str, Any]:
    info = client.get_collection(collection_name=collection)
    params = getattr(info.config, "params", None)
    vectors = getattr(params, "vectors", None) if params is not None else None

    actual_dim, actual_distance = _extract_vector_params(vectors)

    raw_points_count = getattr(info, "points_count", None)
    if raw_points_count is None:
        raw_points_count = getattr(info, "vectors_count", None)

    return {
        "actual_dim": actual_dim,
        "actual_distance": actual_distance,
        "points_count": int(raw_points_count or 0),
    }


def validate_qdrant_collection(client: QdrantClient, collection: str, expected_dim: int) -> None:
    expected_distance = qmodels.Distance.COSINE
    collections = client.get_collections()
    existing = [entry.name for entry in collections.collections]
    if collection not in existing:
        raise RuntimeError(
            f"Qdrant collection '{collection}' does not exist. Create it before starting the application."
        )

    config = get_qdrant_collection_vector_config(client, collection)
    actual_dim = config.get("actual_dim")
    actual_distance = config.get("actual_distance")

    if actual_dim is None:
        raise RuntimeError(
            f"Qdrant collection '{collection}' has no vector config. Recreate the collection with the expected vector config."
        )
    if actual_dim != expected_dim:
        raise RuntimeError(
            f"Qdrant collection '{collection}' dimension mismatch: expected {expected_dim}, got {actual_dim}. "
            "Recreate the collection with the correct dimension before continuing."
        )
    if actual_distance != expected_distance:
        raise RuntimeError(
            f"Qdrant collection '{collection}' distance mismatch: expected {expected_distance}, got {actual_distance}. "
            "Recreate the collection with the correct distance before continuing."
        )


def _ensure_payload_indexes(client: QdrantClient, collection: str) -> None:
    """Create keyword payload indexes if they don't already exist. Idempotent."""
    try:
        info = client.get_collection(collection)
        existing_fields = set((info.payload_schema or {}).keys())
    except Exception:
        existing_fields = set()
    for field_name in ("ticker",):
        if field_name not in existing_fields:
            try:
                client.create_payload_index(
                    collection_name=collection,
                    field_name=field_name,
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                logger.info("Created payload index %s on %s", field_name, collection)
            except Exception as exc:
                logger.warning("Failed to create payload index %s on %s: %s", field_name, collection, exc)


def ensure_collection(client: QdrantClient, collection: str, dim: int) -> str:
    collections = client.get_collections()
    existing = [entry.name for entry in collections.collections]
    expected_dim = int(dim)
    expected_distance = qmodels.Distance.COSINE

    if collection in existing:
        config = get_qdrant_collection_vector_config(client, collection)
        actual_dim = config.get("actual_dim")
        actual_distance = config.get("actual_distance")

        if actual_dim is not None and actual_dim != expected_dim:
            if collection != "commentary_chunks":
                raise RuntimeError(
                    f"Qdrant collection '{collection}' dimension mismatch: expected {expected_dim}, got {actual_dim}. "
                    "Recreate the collection with the correct dimension before continuing."
                )

            fallback_collection = "commentary_chunks_v2"
            logger.warning(
                "Embedding dimension mismatch detected for commentary_chunks; routing to commentary_chunks_v2"
            )
            if fallback_collection in existing:
                fallback_config = get_qdrant_collection_vector_config(client, fallback_collection)
                fallback_dim = fallback_config.get("actual_dim")
                fallback_distance = fallback_config.get("actual_distance")
                if fallback_dim is not None and fallback_dim != expected_dim:
                    raise RuntimeError(
                        f"Qdrant collection '{fallback_collection}' dimension mismatch: expected {expected_dim}, got {fallback_dim}. "
                        "Recreate the collection with the correct dimension before continuing."
                    )
                if fallback_distance is not None and fallback_distance != expected_distance:
                    raise RuntimeError(
                        f"Qdrant collection '{fallback_collection}' distance mismatch: expected {expected_distance}, got {fallback_distance}. "
                        "Recreate the collection with the correct distance before continuing."
                    )
            else:
                client.create_collection(
                    collection_name=fallback_collection,
                    vectors_config=qmodels.VectorParams(size=expected_dim, distance=expected_distance),
                )
            _ensure_payload_indexes(client, fallback_collection)
            return fallback_collection

        if actual_distance is not None and actual_distance != expected_distance:
            raise RuntimeError(
                f"Qdrant collection '{collection}' distance mismatch: expected {expected_distance}, got {actual_distance}. "
                "Recreate the collection with the correct distance before continuing."
            )
        _ensure_payload_indexes(client, collection)
        return collection

    client.create_collection(
        collection_name=collection,
        vectors_config=qmodels.VectorParams(size=expected_dim, distance=expected_distance),
    )
    _ensure_payload_indexes(client, collection)
    return collection


def delete_points_for_document(client: QdrantClient, collection: str, document_id: str) -> None:
    document_id_str = str(document_id or "").strip().lower()
    if not _is_canonical_document_id(document_id_str):
        raise ValueError("document_id must be a canonical UUID")

    client.delete(
        collection_name=collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id_str),
                    )
                ]
            )
        ),
        wait=True,
    )


def upsert_points(client: QdrantClient, collection: str, points: list[dict]) -> dict[str, int]:
    is_local_mode = "qdrant_client.local." in type(getattr(client, "_client", None)).__module__

    def _coerce_id(raw_id: Any) -> Any:
        if not isinstance(raw_id, str):
            return raw_id
        try:
            uuid.UUID(raw_id)
            return raw_id
        except ValueError:
            return str(uuid.uuid5(uuid.NAMESPACE_URL, raw_id))

    valid_points: list[qmodels.PointStruct] = []
    skipped_count = 0

    for point in points:
        if not isinstance(point, dict):
            log_rejected_payload("point is not a dict", collection=collection)
            skipped_count += 1
            continue

        point_id = point.get("id")
        vector = point.get("vector")
        payload = point.get("payload")

        if point_id in (None, ""):
            log_rejected_payload("point id is missing", payload=payload, collection=collection, point_id=point_id)
            skipped_count += 1
            continue
        if not isinstance(vector, list) or not vector:
            log_rejected_payload("vector is missing or empty", payload=payload, collection=collection, point_id=point_id)
            skipped_count += 1
            continue
        if not isinstance(payload, dict):
            log_rejected_payload("payload is not a dict", payload=payload, collection=collection, point_id=point_id)
            skipped_count += 1
            continue
        if collection == settings.qdrant_collection:
            is_valid, reason = validate_asx_docs_payload(payload, mode="write")
            if not is_valid:
                log_invalid_asx_docs_payload(
                    reason or "payload validation failed",
                    payload=payload,
                    collection=collection,
                    point_id=point_id,
                    action="skipped_write",
                )
                skipped_count += 1
                continue

        valid_points.append(
            qmodels.PointStruct(
                id=_coerce_id(point_id),
                vector=vector,
                payload=payload,
            )
        )

    if skipped_count:
        logger.warning(
            "Skipped %d invalid Qdrant point(s) for collection=%s",
            skipped_count,
            collection,
        )
    if not valid_points:
        logger.info(
            "Qdrant upsert skipped for collection=%s written_points=0 rejected_payloads=%d",
            collection,
            skipped_count,
        )
        return {"written_points": 0, "rejected_payloads": skipped_count}

    client.upsert(
        collection_name=collection,
        points=valid_points,
    )
    logger.info(
        "Qdrant upsert completed for collection=%s written_points=%d rejected_payloads=%d",
        collection,
        len(valid_points),
        skipped_count,
    )
    return {"written_points": len(valid_points), "rejected_payloads": skipped_count}
