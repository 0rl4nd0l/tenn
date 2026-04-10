from __future__ import annotations

from dataclasses import replace
import os
from typing import Any, Literal

from app.core.config import settings
from app.services.extraction_run_observability import ExtractionRunObserver
from app.services.llamacpp_runtime import resolve_extraction_runtime_config
from app.services.multipass_extraction import MultipassResult, run_multipass_extraction

ExtractionMethod = Literal["auto", "docling", "pymupdf", "anthropic"]
SUPPORTED_EXTRACTION_METHODS: tuple[str, ...] = (
    "auto",
    "docling",
    "pymupdf",
    "anthropic",
)
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-20250514"


def normalize_extraction_method(method: str | None) -> str:
    normalized = str(method or "auto").strip().lower() or "auto"
    if normalized not in SUPPORTED_EXTRACTION_METHODS:
        raise ValueError(
            f"unsupported extraction method '{method}'; supported={SUPPORTED_EXTRACTION_METHODS}"
        )
    return normalized


def _build_anthropic_client() -> tuple[Any, str, str]:
    import anthropic

    api_key = (
        str(getattr(settings, "anthropic_api_key", "") or "").strip()
        or str(os.environ.get("ANTHROPIC_API_KEY", "") or "").strip()
    )
    if not api_key:
        raise RuntimeError(
            "anthropic extraction unavailable: ANTHROPIC_API_KEY not set"
        )

    model = (
        str(os.environ.get("ANTHROPIC_MODEL", "") or "").strip()
        or ANTHROPIC_DEFAULT_MODEL
    )
    client = anthropic.Anthropic(api_key=api_key)
    setattr(client, "_extraction_model", model)
    return client, model, "anthropic"


def _base_method_provenance(
    *,
    requested_method: str,
    strict_method: bool,
    parser_backend: str | None,
    model_id: str | None,
    runtime_id: str | None,
) -> dict[str, Any]:
    return {
        "requested_method": requested_method,
        "actual_method": requested_method,
        "strict_method": bool(strict_method),
        "parser_id": parser_backend,
        "model_id": model_id,
        "runtime_id": runtime_id,
        "fallback_used": False,
        "error_stage": None,
        "warnings": [],
    }


def _infer_error_stage(error: Any) -> str | None:
    text = str(error or "").strip()
    if not text:
        return None
    for marker in (
        "docling",
        "pass1",
        "classifier_low_confidence",
        "pass3",
        "anthropic",
    ):
        if marker in text:
            return marker
    return "extraction"


def run_method_isolated_extraction(
    pdf_path: str,
    doc_metadata: dict[str, Any],
    llm_client: Any,
    *,
    requested_method: str = "auto",
    strict_method: bool = False,
    skip_narrative: bool = False,
    observer: ExtractionRunObserver | None = None,
) -> MultipassResult:
    normalized_method = normalize_extraction_method(requested_method)
    parser_backend: str | None = None
    effective_client = llm_client
    model_id: str | None = None
    runtime_id: str | None = None

    if normalized_method == "docling":
        parser_backend = "docling"
        runtime_id, model_id = resolve_extraction_runtime_config()
    elif normalized_method == "pymupdf":
        parser_backend = "pymupdf"
        runtime_id, model_id = resolve_extraction_runtime_config()
    elif normalized_method == "anthropic":
        parser_backend = "docling"
        effective_client, model_id, runtime_id = _build_anthropic_client()
    else:
        runtime_id, model_id = resolve_extraction_runtime_config()

    provenance = _base_method_provenance(
        requested_method=normalized_method,
        strict_method=strict_method,
        parser_backend=parser_backend,
        model_id=model_id,
        runtime_id=runtime_id,
    )
    if observer is not None:
        observer.set_actual_method(
            normalized_method if normalized_method != "auto" else parser_backend
        )
        observer.emit(
            "env_check",
            "succeeded",
            "Extraction environment ready.",
            details={
                "parser_backend": parser_backend,
                "runtime_id": runtime_id,
                "model_id": model_id,
            },
        )

    result = run_multipass_extraction(
        pdf_path,
        doc_metadata,
        effective_client,
        skip_narrative=skip_narrative,
        parser_backend=parser_backend,
        strict_parser=strict_method and parser_backend in {"docling", "pymupdf"},
        observer=observer,
    )

    payload = dict(result.payload) if isinstance(result.payload, dict) else {}
    structured_meta = payload.get("_structured_extraction")
    structured_meta = structured_meta if isinstance(structured_meta, dict) else {}
    parser_id = str(
        structured_meta.get("parser_id") or parser_backend or normalized_method
    )
    actual_method = normalized_method if normalized_method == "anthropic" else parser_id
    fallback_used = bool(structured_meta.get("fallback_used"))
    if not fallback_used and normalized_method in {"docling", "anthropic"}:
        fallback_used = parser_id.startswith("pymupdf")

    warnings = structured_meta.get("warnings")
    warnings = list(warnings) if isinstance(warnings, list) else []

    provenance.update(
        {
            "actual_method": actual_method,
            "parser_id": parser_id,
            "fallback_used": fallback_used,
            "error_stage": _infer_error_stage(result.error),
            "warnings": warnings,
        }
    )
    payload["_method_provenance"] = provenance
    if observer is not None:
        observer.set_actual_method(actual_method)

    return replace(result, payload=payload)
