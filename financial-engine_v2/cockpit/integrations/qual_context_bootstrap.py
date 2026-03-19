from __future__ import annotations

from pathlib import Path
from typing import Any

from cockpit.integrations.qual_context import QualContextReader


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    txt = str(value).strip().lower()
    if txt in {"1", "true", "yes", "on"}:
        return True
    if txt in {"0", "false", "no", "off"}:
        return False
    return None


def context_enabled(cfg: dict[str, Any] | None, *, default: bool = False) -> bool:
    raw = cfg if isinstance(cfg, dict) else {}
    coerced = _coerce_bool(raw.get("enabled"))
    return bool(coerced) if coerced is not None else bool(default)


def build_qual_context_reader(
    *,
    repo_root: Path,
    qc_cfg: dict[str, Any] | None,
    backend_api_client: Any,
    context_name: str = "qualitative_context",  # noqa: ARG002 - reserved for future multi-context support
) -> QualContextReader:
    cfg = qc_cfg if isinstance(qc_cfg, dict) else {}
    embed_backend = str(cfg.get("embed_backend") or "ollama").strip().lower() or "ollama"
    embed_model = str(cfg.get("embed_model") or "nomic-embed-text").strip() or "nomic-embed-text"

    reader = QualContextReader(
        repo_root=repo_root,
        backend_api_client=backend_api_client,
        embed_backend=embed_backend,
        embed_model=embed_model,
        corpus_filter=str(cfg.get("corpus_filter") or "news").strip(),
        ticker_match_mode=str(cfg.get("ticker_match_mode") or "soft").strip(),
        top_k=int(cfg.get("top_k") or 8),
        timeout=float(cfg.get("timeout") or 12.0),
    )
    reader.validate_runtime()
    return reader

