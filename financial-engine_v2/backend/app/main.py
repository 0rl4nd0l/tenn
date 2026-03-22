import errno
import logging
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import func

from app.api.routes import (
    BookIngestRequest,
    TranscriptIngestRequest,
    ingest_book_route,
    ingest_transcript_route,
    require_api_key,
    router,
)
from app.core.config import LOADED_ENV_FILES, PROJECT_ROOT, settings
from app.core.db import SessionLocal, engine
from app.models.base import Base
from app.models.documents import Document
from app.models.extractions import ExtractionRun
from app.routes.chat import router as chat_router
from app.services.embeddings import (
    get_qdrant_collection_vector_config,
    validate_qdrant_collection,
    verify_qdrant,
)
from app.services.llm import embed_texts
from app.services.rag import query_rag


app = FastAPI(title="Financial Engine v2")
app.include_router(router, prefix="/api")
app.include_router(chat_router)
app.include_router(chat_router, prefix="/api")


class RagQueryRequest(BaseModel):
    query: str
    ticker: str | None = None
    top_k: int = 8
    debug: bool = False


@app.post("/rag/query", dependencies=[Depends(require_api_key)])
def rag_query(body: RagQueryRequest):
    try:
        return query_rag(
            query=body.query,
            ticker=body.ticker,
            top_k=body.top_k,
            debug=body.debug,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/ingest/transcript", dependencies=[Depends(require_api_key)])
def ingest_transcript_alias(body: TranscriptIngestRequest):
    return ingest_transcript_route(body)


@app.post("/ingest/book", dependencies=[Depends(require_api_key)])
def ingest_book_alias(body: BookIngestRequest):
    return ingest_book_route(body)


RUNTIME_EMBEDDING_MODEL_FILE = PROJECT_ROOT / "reports" / "runtime_embedding_model.txt"
logger = logging.getLogger(__name__)
VECTOR_ID_FORMAT = "document_id:chunk_index"
DISTANCE = "COSINE"


def _architecture_version_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_ROOT.parent,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def _log_architecture_runtime_assertion() -> None:
    logger.info(
        "Architecture version: %s\nEmbedding model: %s\nVector ID format: %s\nDistance: %s",
        _architecture_version_hash(),
        str(settings.embed_model or "").strip(),
        VECTOR_ID_FORMAT,
        DISTANCE,
    )


def _log_runtime_feature_warnings() -> None:
    if not settings.enable_embeddings:
        logger.warning("WARNING: embeddings disabled - RAG functionality will be limited")
    if not settings.enable_extraction:
        logger.warning("WARNING: extraction disabled - ingestion outputs will be limited")


def _log_runtime_config() -> None:
    logger.info(
        "Runtime config -> TASK_MODE=%s, ENABLE_EMBEDDINGS=%s, QDRANT_URL=%s, CELERY_BROKER_URL=%s",
        settings.task_mode,
        str(settings.enable_embeddings).lower(),
        settings.qdrant_url,
        settings.celery_broker_url,
    )
    if LOADED_ENV_FILES:
        logger.debug("Loaded env files: %s", ", ".join(LOADED_ENV_FILES))


def _socket_can_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    with socket.create_connection((host, port), timeout=timeout):
        return True


def check_llamacpp(base_url: str) -> bool:
    target = str(base_url or "").strip().rstrip("/")
    if not target:
        raise RuntimeError("missing base URL")
    response = httpx.get(f"{target}/v1/models", timeout=5.0)
    response.raise_for_status()
    payload = response.json()
    models = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise RuntimeError("unexpected /v1/models payload")
    for row in models:
        if not isinstance(row, dict):
            continue
        model_id = str(row.get("id") or "").strip()
        if ":" in model_id:
            raise RuntimeError("Endpoint appears to be Ollama, not llama.cpp")
    return True


def check_ollama(base_url: str) -> bool:
    target = str(base_url or "").strip().rstrip("/")
    if not target:
        raise RuntimeError("missing base URL")
    response = httpx.get(f"{target}/api/tags", timeout=5.0)
    response.raise_for_status()
    payload = response.json()
    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise RuntimeError("unexpected /api/tags payload")
    return True


def validate_backends(llamacpp_base_url: str, ollama_base_url: str) -> None:
    llama_url = str(llamacpp_base_url or "").strip().rstrip("/")
    ollama_url = str(ollama_base_url or "").strip().rstrip("/")
    if not llama_url:
        raise RuntimeError("llama.cpp base URL must be configured.")
    if (
        ollama_url
        and (
        llama_url == ollama_url
        or llama_url.startswith(ollama_url)
        or ollama_url.startswith(llama_url)
        )
    ):
        raise RuntimeError("Potential backend overlap detected")
    try:
        check_llamacpp(llama_url)
    except Exception as exc:
        raise RuntimeError(f"llama.cpp endpoint invalid: {exc}") from exc
    if not ollama_url:
        return
    try:
        check_ollama(ollama_url)
    except Exception as exc:
        raise RuntimeError(f"Ollama endpoint invalid: {exc}") from exc


def _redis_socket_target() -> tuple[str, int]:
    parsed = urlparse(str(settings.celery_broker_url or "").strip())
    host = str(parsed.hostname or "").strip() or "127.0.0.1"
    port = int(parsed.port or 6379)
    return host, port


def _redis_connected() -> bool:
    broker_url = str(settings.celery_broker_url or "").strip().lower()
    if not broker_url.startswith(("redis://", "rediss://")):
        return False
    host, port = _redis_socket_target()
    try:
        return _socket_can_connect(host, port)
    except OSError:
        return False


def _log_redis_startup_status() -> None:
    if _redis_connected():
        logger.info("Celery broker reachable at %s", settings.celery_broker_url)
        return
    if str(settings.task_mode or "").strip().lower() != "celery":
        logger.info(
            "Celery broker unreachable while TASK_MODE=%s; host will continue without broker-backed ingestion",
            settings.task_mode,
        )
        return
    logger.warning(
        "Celery broker unreachable; ingestion disabled",
        extra={
            "celery_broker_url": settings.celery_broker_url,
            "ingestion_disabled": True,
        },
    )


def _should_skip_qdrant_startup_validation(exc: Exception) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError) and exc.errno == errno.EPERM:
        return True
    return "Operation not permitted" in str(exc)


def _read_stored_embedding_model() -> str | None:
    if not RUNTIME_EMBEDDING_MODEL_FILE.exists():
        return None
    try:
        stored = RUNTIME_EMBEDDING_MODEL_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("Unable to read stored embedding model marker %s: %s", RUNTIME_EMBEDDING_MODEL_FILE, exc)
        return None
    return stored or None


def _write_runtime_embedding_model(model_name: str) -> None:
    resolved_model = str(model_name or "").strip()
    if not resolved_model:
        raise RuntimeError("Embedding model is not configured")
    RUNTIME_EMBEDDING_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_EMBEDDING_MODEL_FILE.write_text(resolved_model, encoding="utf-8")


def _count_db_embedding_rows() -> tuple[int, int]:
    db = SessionLocal()
    try:
        document_count = int(db.query(func.count(Document.document_id)).scalar() or 0)
        extraction_count = int(db.query(func.count(ExtractionRun.run_id)).scalar() or 0)
        return document_count, extraction_count
    finally:
        db.close()


def _qdrant_collection_state(client, collection_name: str) -> tuple[bool, int]:
    collections = client.get_collections()
    names = {collection.name for collection in collections.collections}
    if collection_name not in names:
        return False, 0
    collection_info = client.get_collection(collection_name=collection_name)
    raw_points_count = getattr(collection_info, "points_count", None)
    if raw_points_count is None:
        raw_points_count = getattr(collection_info, "vectors_count", None)
    return True, int(raw_points_count or 0)


def _get_embedding_state_snapshot(client=None) -> dict[str, object]:
    document_count, extraction_count = _count_db_embedding_rows()
    qdrant_collection_exists = False
    qdrant_points_count = 0

    if client is not None:
        qdrant_collection_exists, qdrant_points_count = _qdrant_collection_state(
            client,
            settings.qdrant_collection,
        )

    return {
        "stored_model": _read_stored_embedding_model(),
        "configured_model": str(settings.embed_model or "").strip(),
        "document_count": document_count,
        "extraction_count": extraction_count,
        "qdrant_collection_exists": qdrant_collection_exists,
        "qdrant_points_count": qdrant_points_count,
    }


def _validate_embedding_model_on_startup(client=None) -> None:
    snapshot = _get_embedding_state_snapshot(client=client)
    stored_model = str(snapshot.get("stored_model") or "").strip()
    configured_model = str(snapshot.get("configured_model") or "").strip()
    document_count = int(snapshot.get("document_count") or 0)
    extraction_count = int(snapshot.get("extraction_count") or 0)
    qdrant_collection_exists = bool(snapshot.get("qdrant_collection_exists"))
    qdrant_points_count = int(snapshot.get("qdrant_points_count") or 0)
    has_db_state = document_count > 0 or extraction_count > 0
    has_vectors = qdrant_collection_exists and qdrant_points_count > 0

    if not configured_model:
        raise RuntimeError("Embedding model is not configured")
    if not stored_model:
        _write_runtime_embedding_model(configured_model)
        logger.info("Recorded runtime embedding model marker: %s", configured_model)
        return
    if has_db_state and not has_vectors:
        logger.warning(
            "Database has embedding metadata but Qdrant collection is empty; startup allowed with inconsistency warning configured=%s document_count=%d extraction_count=%d qdrant_collection_exists=%s qdrant_points_count=%d",
            configured_model,
            document_count,
            extraction_count,
            qdrant_collection_exists,
            qdrant_points_count,
        )
        if stored_model and stored_model != configured_model:
            logger.warning(
                "Stored embedding model differs from config while Qdrant is empty: stored=%s configured=%s",
                stored_model,
                configured_model,
            )
        return
    if stored_model == configured_model:
        return
    if not has_vectors:
        logger.warning(
            "Stored embedding model differs from config but empty Qdrant collection allows startup: stored=%s configured=%s qdrant_collection_exists=%s qdrant_points_count=%d",
            stored_model,
            configured_model,
            qdrant_collection_exists,
            qdrant_points_count,
        )
        return
    raise RuntimeError(
        f"Embedding model mismatch: stored model is '{stored_model}', configured model is '{configured_model}', "
        f"documents={document_count}, extraction_runs={extraction_count}, qdrant_points={qdrant_points_count}. "
        "Reset and rebuild ingestion before serving RAG queries."
    )


def _validate_qdrant_on_startup() -> None:
    if not settings.enable_qdrant or not settings.enable_embeddings:
        return
    try:
        client = verify_qdrant()
    except Exception as exc:
        if not _should_skip_qdrant_startup_validation(exc):
            raise
        logger.warning("WARNING: qdrant startup validation skipped: %s", exc)
        return

    existing_collection, points_count = _qdrant_collection_state(client, settings.qdrant_collection)
    snapshot = _get_embedding_state_snapshot(client=client)
    _validate_embedding_model_on_startup(client=client)
    vectors = embed_texts(
        ["x"],
        metadata={
            "task_type": "embedding",
            "component": "startup_validation",
            "operation": "qdrant_dimension_probe",
        },
    )
    if not vectors or not vectors[0]:
        raise RuntimeError(
            "Could not get embedding dimension from model: embedding service returned no vector. "
            "Ensure the embedding model is available before starting the application."
        )

    expected_dim = len(vectors[0])
    actual_dim = None
    actual_distance = None
    if existing_collection:
        collection_config = get_qdrant_collection_vector_config(client, settings.qdrant_collection)
        actual_dim = collection_config.get("actual_dim")
        actual_distance = collection_config.get("actual_distance")
        points_count = int(collection_config.get("points_count") or 0)
    logger.info(
        "qdrant_startup_state",
        extra={
            "qdrant_collection": settings.qdrant_collection,
            "qdrant_collection_exists": existing_collection,
            "qdrant_points_count": points_count,
            "document_count": int(snapshot.get("document_count") or 0),
            "extraction_count": int(snapshot.get("extraction_count") or 0),
            "embed_model": snapshot.get("configured_model"),
            "stored_embed_model": snapshot.get("stored_model"),
            "expected_dim": expected_dim,
            "actual_dim": actual_dim,
            "actual_distance": str(actual_distance) if actual_distance is not None else None,
        },
    )
    if not existing_collection:
        logger.info(
            "Qdrant collection '%s' does not exist; startup allowed and collection will be created during ingestion",
            settings.qdrant_collection,
        )
        return
    if points_count <= 0:
        logger.warning(
            "Qdrant collection '%s' exists but has 0 vectors; startup allowed expected_dim=%s actual_dim=%s",
            settings.qdrant_collection,
            expected_dim,
            actual_dim,
        )
        return
    try:
        validate_qdrant_collection(client, settings.qdrant_collection, expected_dim)
    except RuntimeError as exc:
        if "does not exist" not in str(exc):
            raise
        logger.warning(
            "WARNING: qdrant collection '%s' is missing - it will be created during ingestion or the first RAG query",
            settings.qdrant_collection,
        )
    except Exception as exc:
        if not _should_skip_qdrant_startup_validation(exc):
            raise
        logger.warning("WARNING: qdrant startup validation skipped: %s", exc)


def _system_status_snapshot() -> dict[str, object]:
    redis_connected = _redis_connected()
    qdrant_connected = False
    collections_present: list[str] = []
    document_count_estimate = 0
    latest_document = None
    latest_extraction = None
    try:
        db = SessionLocal()
        try:
            document_count_estimate = int(db.query(func.count(Document.document_id)).scalar() or 0)
            latest_document = db.query(func.max(Document.ingested_at)).scalar()
            latest_extraction = db.query(func.max(ExtractionRun.created_at)).scalar()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Database status probe failed: %s", exc)

    last_ingestion_candidates = [
        value.isoformat()
        for value in (latest_document, latest_extraction)
        if isinstance(value, datetime)
    ]
    last_ingestion_activity = max(last_ingestion_candidates) if last_ingestion_candidates else None

    try:
        client = verify_qdrant()
        qdrant_connected = True
        collections = client.get_collections()
        collections_present = sorted(collection.name for collection in collections.collections)
    except Exception as exc:
        logger.warning("Qdrant status probe failed: %s", exc)

    return {
        "redis_connected": redis_connected,
        "qdrant_connected": qdrant_connected,
        "collections_present": collections_present,
        "document_count_estimate": document_count_estimate,
        "last_ingestion_activity": last_ingestion_activity,
    }


@app.get("/api/system/status", dependencies=[Depends(require_api_key)])
def system_status():
    return _system_status_snapshot()


@app.on_event("startup")
def startup():
    Path(settings.docs_root).mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    _log_runtime_config()
    _log_runtime_feature_warnings()
    _log_redis_startup_status()
    _validate_qdrant_on_startup()
    _log_architecture_runtime_assertion()
