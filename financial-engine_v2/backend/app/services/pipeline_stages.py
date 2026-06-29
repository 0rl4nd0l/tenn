from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Any, Callable, Mapping, Optional


class ExtractionStageStatus(str, Enum):
    SKIPPED = "skipped"
    OK = "ok"
    OK_LOW_CONFIDENCE = "ok_low_confidence"
    FAILED = "failed"
    PARSER_ERROR = "parser_error"


@dataclass(frozen=True)
class ExtractionStageResult:
    status: ExtractionStageStatus
    payload: dict[str, Any]
    sections: list[dict[str, Any]]
    error: Optional[str] = None
    confidence: Optional[float] = None
    model_name: Optional[str] = None
    failure_code: Optional[str] = None


class EmbeddingStageStatus(str, Enum):
    SKIPPED = "skipped"
    OK = "ok"


@dataclass(frozen=True)
class EmbeddingStageResult:
    status: EmbeddingStageStatus
    chunks_created: int
    chunks_skipped: int = 0
    invalid_payloads: int = 0
    written_points: int = 0
    skipped_invalid_vectors: int = 0


@dataclass(frozen=True)
class DocumentProcessResult:
    processed: int
    skipped_download: int
    error: Optional[str] = None
    extraction_status: Optional[str] = None
    chunks_created: int = 0
    chunks_skipped: int = 0
    invalid_payloads: int = 0
    written_points: int = 0

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "processed": self.processed,
            "skipped_download": self.skipped_download,
            "error": self.error,
            "extraction_status": self.extraction_status,
            "chunks_created": self.chunks_created,
            "chunks_skipped": self.chunks_skipped,
            "invalid_payloads": self.invalid_payloads,
            "written_points": self.written_points,
        }


@dataclass
class DownloadProcessAggregate:
    processed: int = 0
    skipped_download: int = 0
    extraction_failed_count: int = 0
    chunks_created: int = 0
    chunks_skipped: int = 0
    invalid_payloads: int = 0
    written_points: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    def add(self, document_id: Any, result: DocumentProcessResult) -> None:
        self.processed += int(result.processed)
        self.skipped_download += int(result.skipped_download)
        self.chunks_created += int(result.chunks_created)
        self.chunks_skipped += int(result.chunks_skipped)
        self.invalid_payloads += int(result.invalid_payloads)
        self.written_points += int(result.written_points)

        status = (result.extraction_status or "").strip().lower()
        if status == "failed":
            self.extraction_failed_count += 1
            self.errors.append(
                {
                    "document_id": str(document_id),
                    "stage": "process_document",
                    "error": "extraction_failed",
                    "extraction_status": result.extraction_status,
                }
            )
        elif result.error is not None:
            self.errors.append({"document_id": str(document_id), "error": result.error})

    def to_legacy_tuple(
        self,
    ) -> tuple[int, int, int, list[dict[str, Any]], dict[str, int]]:
        return (
            self.processed,
            self.skipped_download,
            self.extraction_failed_count,
            list(self.errors),
            {
                "chunks_created": self.chunks_created,
                "chunks_skipped": self.chunks_skipped,
                "invalid_payloads": self.invalid_payloads,
                "written_points": self.written_points,
            },
        )


def normalize_document_process_result(result: Any) -> DocumentProcessResult:
    if isinstance(result, DocumentProcessResult):
        return result
    if isinstance(result, Mapping):
        return DocumentProcessResult(
            processed=int(result.get("processed", 0) or 0),
            skipped_download=int(result.get("skipped_download", 0) or 0),
            error=result.get("error") if result.get("error") is not None else None,
            extraction_status=(
                str(result.get("extraction_status"))
                if result.get("extraction_status") is not None
                else None
            ),
            chunks_created=int(result.get("chunks_created", 0) or 0),
            chunks_skipped=int(result.get("chunks_skipped", 0) or 0),
            invalid_payloads=int(result.get("invalid_payloads", 0) or 0),
            written_points=int(result.get("written_points", 0) or 0),
        )
    raise TypeError(f"Unsupported document process result type: {type(result)!r}")


def _coerce_status(value: Any) -> ExtractionStageStatus:
    text = str(value or "").strip().lower()
    if text == ExtractionStageStatus.OK.value:
        return ExtractionStageStatus.OK
    if text == ExtractionStageStatus.OK_LOW_CONFIDENCE.value:
        return ExtractionStageStatus.OK_LOW_CONFIDENCE
    if text == ExtractionStageStatus.FAILED.value:
        return ExtractionStageStatus.FAILED
    if text == ExtractionStageStatus.SKIPPED.value:
        return ExtractionStageStatus.SKIPPED
    if text == ExtractionStageStatus.PARSER_ERROR.value:
        return ExtractionStageStatus.PARSER_ERROR
    return ExtractionStageStatus.FAILED


def run_extraction_stage(
    *,
    enable_extraction: bool,
    resolved_pdf_path: str,
    doc_metadata: Mapping[str, str],
    llm_client: Any,
    multipass_runner: Callable[..., Any],
    default_model_name: str,
    failure_classifier: Callable[[Any, Optional[Mapping[str, Any]]], str],
) -> ExtractionStageResult:
    if not enable_extraction:
        return ExtractionStageResult(
            status=ExtractionStageStatus.SKIPPED,
            payload={"status": "skipped_extraction"},
            sections=[],
            model_name=None,
            failure_code="disabled",
        )

    try:
        multipass_result = multipass_runner(
            resolved_pdf_path,
            dict(doc_metadata),
            llm_client,
        )
    except Exception as exc:  # pragma: no cover - defensive; validated via tests
        error_text = str(exc)
        return ExtractionStageResult(
            status=ExtractionStageStatus.FAILED,
            payload={"error": error_text},
            sections=[],
            error=error_text,
            confidence=None,
            model_name=default_model_name,
            failure_code=failure_classifier(error_text, None),
        )

    raw_payload = getattr(multipass_result, "payload", None)
    if isinstance(raw_payload, dict):
        payload = raw_payload
    elif isinstance(raw_payload, Mapping):
        payload = dict(raw_payload)
    else:
        payload = {}
    if not payload:
        payload = {"error": "invalid_multipass_payload"}

    raw_sections = getattr(multipass_result, "sections", None)
    sections = list(raw_sections) if isinstance(raw_sections, list) else []

    status = _coerce_status(getattr(multipass_result, "status", None))
    error = getattr(multipass_result, "error", None)
    raw_confidence = payload.get("confidence_metrics")
    confidence = (
        float(raw_confidence)
        if isinstance(raw_confidence, (int, float))
        and not isinstance(raw_confidence, bool)
        else None
    )
    failure_code: Optional[str] = None
    if status == ExtractionStageStatus.FAILED:
        failure_code = failure_classifier(error, payload)

    return ExtractionStageResult(
        status=status,
        payload=payload,
        sections=sections,
        error=error,
        confidence=confidence,
        model_name=default_model_name,
        failure_code=failure_code,
    )


def run_embedding_stage(
    *,
    chunks: list[str],
    doc: Any,
    enable_embeddings: bool,
    enable_qdrant: bool,
    qdrant_client: Any,
    qdrant_url: str,
    qdrant_collection: str,
    ollama_client: Any,
    embed_chunks: Callable[..., list[list[float]]],
    qdrant_client_factory: Callable[[str], Any],
    ensure_collection_fn: Callable[[Any, str, int], Any],
    delete_points_for_document_fn: Callable[[Any, str, str], Any],
    upsert_points_fn: Callable[
        [Any, str, list[dict[str, Any]]], Mapping[str, Any] | None
    ],
    validate_payload_fn: Callable[[Mapping[str, Any]], tuple[bool, Optional[str]]],
    log_rejected_payload_fn: Callable[..., Any],
    logger_obj: Any,
) -> EmbeddingStageResult:
    chunks_created = len(chunks)
    chunks_skipped = 0
    invalid_payloads = 0
    written_points = 0
    skipped_invalid_vectors = 0

    if not enable_embeddings or not chunks:
        return EmbeddingStageResult(
            status=EmbeddingStageStatus.SKIPPED,
            chunks_created=chunks_created,
        )

    if getattr(doc, "document_id", None) is None:
        log_rejected_payload_fn(
            "document_id is None before embedding",
            payload={"document_id": None, "ticker": doc.ticker},
            collection=qdrant_collection,
            source=doc.source_url,
        )
        skipped_invalid_vectors = len(chunks)
        invalid_payloads += len(chunks)
        chunks_skipped += len(chunks)
        return EmbeddingStageResult(
            status=EmbeddingStageStatus.OK,
            chunks_created=chunks_created,
            chunks_skipped=chunks_skipped,
            invalid_payloads=invalid_payloads,
            written_points=written_points,
            skipped_invalid_vectors=skipped_invalid_vectors,
        )

    if not str(getattr(doc, "ticker", "") or "").strip():
        log_rejected_payload_fn(
            "ticker is missing before embedding",
            payload={"document_id": str(doc.document_id).lower(), "ticker": doc.ticker},
            collection=qdrant_collection,
            source=doc.source_url,
        )
        skipped_invalid_vectors = len(chunks)
        invalid_payloads += len(chunks)
        chunks_skipped += len(chunks)
        return EmbeddingStageResult(
            status=EmbeddingStageStatus.OK,
            chunks_created=chunks_created,
            chunks_skipped=chunks_skipped,
            invalid_payloads=invalid_payloads,
            written_points=written_points,
            skipped_invalid_vectors=skipped_invalid_vectors,
        )

    doc_id_str = str(doc.document_id).lower()
    try:
        uuid.UUID(doc_id_str)
    except Exception:
        log_rejected_payload_fn(
            "document_id is not a canonical UUID before embedding",
            payload={"document_id": doc_id_str, "ticker": doc.ticker},
            collection=qdrant_collection,
            source=doc.source_url,
        )
        skipped_invalid_vectors = len(chunks)
        invalid_payloads += len(chunks)
        chunks_skipped += len(chunks)
        doc_id_str = ""

    vectors = embed_chunks(chunks, ollama_client=ollama_client) if doc_id_str else []

    if len(vectors) != len(chunks):
        mismatch_count = abs(len(chunks) - len(vectors))
        skipped_invalid_vectors += mismatch_count
        chunks_skipped += mismatch_count
        logger_obj.error(
            "Embedding/vector count mismatch for document_id=%s ticker=%s source=%s expected=%d got=%d",
            doc_id_str,
            doc.ticker,
            doc.source_url,
            len(chunks),
            len(vectors),
        )

    if enable_qdrant and vectors:
        qc = (
            qdrant_client
            if qdrant_client is not None
            else qdrant_client_factory(qdrant_url)
        )
        usable_vectors = vectors[: len(chunks)]
        vector_dimension = len(usable_vectors[0])
        ensure_collection_fn(qc, qdrant_collection, vector_dimension)
        points: list[dict[str, Any]] = []
        for index, vector in enumerate(usable_vectors):
            logical_vector_id = f"{doc_id_str}:{index}"
            payload = {
                "document_id": doc_id_str,
                "ticker": doc.ticker,
                "doc_class": doc.doc_class,
                "doc_subtype": doc.doc_subtype,
                "chunk_index": index,
                "logical_vector_id": logical_vector_id,
                "title": doc.title,
                "text": chunks[index],
            }
            is_valid, reason = validate_payload_fn(payload)
            if not is_valid:
                skipped_invalid_vectors += 1
                invalid_payloads += 1
                chunks_skipped += 1
                log_rejected_payload_fn(
                    reason or "payload validation failed",
                    payload=payload,
                    collection=qdrant_collection,
                    point_id=logical_vector_id,
                    source=doc.source_url,
                )
                continue
            points.append({"id": logical_vector_id, "vector": vector, "payload": payload})
        if points:
            delete_points_for_document_fn(qc, qdrant_collection, doc_id_str)
        upsert_result = dict(upsert_points_fn(qc, qdrant_collection, points) or {})
        written_points += int(upsert_result.get("written_points", 0))
        rejected_payloads = int(upsert_result.get("rejected_payloads", 0))
        invalid_payloads += rejected_payloads
        chunks_skipped += rejected_payloads

    return EmbeddingStageResult(
        status=EmbeddingStageStatus.OK,
        chunks_created=chunks_created,
        chunks_skipped=chunks_skipped,
        invalid_payloads=invalid_payloads,
        written_points=written_points,
        skipped_invalid_vectors=skipped_invalid_vectors,
    )


def build_reproducibility_metadata(
    *,
    doc: Any,
    resolved_pdf_path: str,
    extractor_version: str,
    prompt_hash: str,
    stage_result: ExtractionStageResult,
) -> dict[str, Any]:
    metrics = (
        stage_result.payload.get("metrics")
        if isinstance(stage_result.payload, Mapping)
        else {}
    )
    non_null_metric_count = 0
    if isinstance(metrics, Mapping):
        non_null_metric_count = len(
            [value for value in metrics.values() if value is not None]
        )

    return {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "extractor_version": extractor_version,
        "prompt_hash": prompt_hash,
        "model_name": stage_result.model_name,
        "status": stage_result.status.value,
        "failure_code": stage_result.failure_code,
        "document_id": str(getattr(doc, "document_id", "")),
        "ticker": str(getattr(doc, "ticker", "") or ""),
        "source_url": str(getattr(doc, "source_url", "") or ""),
        "resolved_pdf_path": resolved_pdf_path,
        "pdf_sha256": str(getattr(doc, "pdf_sha256", "") or ""),
        "sections_count": len(stage_result.sections),
        "non_null_metric_count": non_null_metric_count,
    }


def attach_reproducibility_metadata(
    structured_payload: Mapping[str, Any] | None,
    reproducibility: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(structured_payload or {})
    payload["_reproducibility"] = dict(reproducibility)
    return payload
