from __future__ import annotations

from pathlib import Path
from typing import Any

from cockpit.integrations.qual_context import QualContextReader


DEFAULT_NEWS_CONTEXT_RELATIVE_PATH = Path("reports/qual_context/news.sqlite")
DEFAULT_NEWS_EVAL_RELATIVE_PATH = Path("reports/qual_context/news_eval.sqlite")
DEFAULT_NIGHTLY_NEWS_ARTIFACT_ROOT = Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context")


def resolve_qual_context_db_path(*, repo_root: Path, raw_path: str) -> Path:
    db_path = Path(raw_path).expanduser()
    if db_path.is_absolute():
        return db_path.resolve()
    primary = (repo_root / db_path).resolve()
    secondary = (repo_root.parent / db_path).resolve()
    if primary.exists():
        return primary
    if secondary.exists():
        return secondary
    return primary


def _resolve_relative_context_candidates(*, repo_root: Path, raw_path: str) -> list[Path]:
    db_path = Path(raw_path).expanduser()
    if db_path.is_absolute():
        return [db_path.resolve()]
    return [
        (repo_root / db_path).resolve(),
        (repo_root.parent / db_path).resolve(),
    ]


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def _newest_existing_file(paths: list[Path]) -> Path | None:
    existing: list[Path] = []
    for path in _dedupe_paths(paths):
        if path.exists() and path.is_file():
            existing.append(path)
    if not existing:
        return None
    return max(existing, key=lambda path: (path.stat().st_mtime_ns, path.stat().st_size, str(path)))


def _is_default_news_context_path(raw_path: str) -> bool:
    db_path = Path(raw_path).expanduser()
    return not db_path.is_absolute() and db_path == DEFAULT_NEWS_CONTEXT_RELATIVE_PATH


def _default_nightly_news_context_db_path() -> Path:
    return (DEFAULT_NIGHTLY_NEWS_ARTIFACT_ROOT / "news.sqlite").expanduser().resolve()


def resolve_rag_dependency_policy(raw_policy: str, profile: str) -> str:
    policy = str(raw_policy or "error").strip().lower()
    if policy not in {"error", "fallback_hash", "auto"}:
        raise ValueError(
            "Invalid rag.qualitative_context.dependency_policy value "
            f"'{raw_policy}'. Expected one of: error, fallback_hash, auto."
        )
    if policy != "auto":
        return policy
    return "error" if profile in {"prod", "production", "live"} else "fallback_hash"


def _coerce_optional_bool(value: Any) -> bool | None:
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


def resolve_news_context_db_path(
    *,
    repo_root: Path,
    rag_cfg: dict[str, Any],
) -> Path | None:
    news_cfg = rag_cfg.get("news_context") if isinstance(rag_cfg, dict) else {}
    news_cfg = news_cfg if isinstance(news_cfg, dict) else {}

    enabled = _coerce_optional_bool(news_cfg.get("enabled"))
    # Auto-detect optional news corpus by default.
    if enabled is False:
        return None

    explicit_path = str(news_cfg.get("db_path") or "").strip()
    if explicit_path:
        resolved_candidates = _resolve_relative_context_candidates(repo_root=repo_root, raw_path=explicit_path)
        resolved = resolve_qual_context_db_path(repo_root=repo_root, raw_path=explicit_path)
        if _is_default_news_context_path(explicit_path):
            freshest_default = _newest_existing_file(
                [
                    _default_nightly_news_context_db_path(),
                    *resolved_candidates,
                ]
            )
            if freshest_default is not None:
                return freshest_default
        if resolved.exists():
            return resolved
        # If enabled is explicitly true, treat missing explicit path as a hard config error upstream.
        if enabled is True:
            return resolved
        return None

    news_candidates = [
        _default_nightly_news_context_db_path(),
        (repo_root / DEFAULT_NEWS_CONTEXT_RELATIVE_PATH).resolve(),
        (repo_root.parent / DEFAULT_NEWS_CONTEXT_RELATIVE_PATH).resolve(),
    ]
    freshest_news = _newest_existing_file(news_candidates)
    if freshest_news is not None:
        return freshest_news

    eval_candidates = [
        (repo_root / DEFAULT_NEWS_EVAL_RELATIVE_PATH).resolve(),
        (repo_root.parent / DEFAULT_NEWS_EVAL_RELATIVE_PATH).resolve(),
    ]
    for candidate in eval_candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def make_qual_context_reader(
    *,
    repo_root: Path,
    qc_cfg: dict[str, Any],
    db_path: Path,
    embed_backend: str | None = None,
    embed_model: str | None = None,
) -> QualContextReader:
    return QualContextReader(
        repo_root=repo_root,
        db_path=str(db_path),
        embed_backend=str(embed_backend if embed_backend is not None else (qc_cfg.get("embed_backend") or "sentence-transformers")),
        embed_model=str(embed_model if embed_model is not None else (qc_cfg.get("embed_model") or "bge-large-en-v1.5")),
        corpus_filter=str(qc_cfg.get("corpus_filter") or "company"),
        exclude_corpus_filter=str(qc_cfg.get("exclude_corpus_filter") or ""),
        top_k=int(qc_cfg.get("top_k") or 8),
        max_text_chars=int(qc_cfg.get("max_text_chars") or 1200),
        ollama_endpoint=str(qc_cfg.get("ollama_endpoint") or "http://127.0.0.1:11434"),
        hash_dim=int(qc_cfg.get("hash_dim") or 384),
        st_device=str(qc_cfg.get("st_device") or "auto"),
        st_batch_size=int(qc_cfg.get("st_batch_size") or 16),
        ticker_match_mode=str(qc_cfg.get("ticker_match_mode") or "strict"),
        recall_top_k_multiplier=int(qc_cfg.get("recall_top_k_multiplier") or 20),
    )


def build_qual_context_reader(
    *,
    repo_root: Path,
    qc_cfg: dict[str, Any],
    db_path: Path,
    dependency_policy: str,
    startup_notices: list[str] | None = None,
) -> QualContextReader:
    reader = make_qual_context_reader(
        repo_root=repo_root,
        qc_cfg=qc_cfg,
        db_path=db_path,
    )
    try:
        reader.validate_runtime()
        return reader
    except Exception as exc:
        if dependency_policy != "fallback_hash":
            raise RuntimeError(f"RAG startup validation failed: {exc}") from exc

        configured_backend = str(qc_cfg.get("embed_backend") or "sentence-transformers").strip().lower()
        err = str(exc).lower()
        is_missing_st_dependency = (
            configured_backend == "sentence-transformers"
            and "sentence-transformers" in err
            and "missing" in err
        )
        if not is_missing_st_dependency:
            raise RuntimeError(f"RAG startup validation failed: {exc}") from exc

        fallback_reader = make_qual_context_reader(
            repo_root=repo_root,
            qc_cfg=qc_cfg,
            db_path=db_path,
            embed_backend="hash",
            embed_model="hash",
        )
        fallback_reader.validate_runtime()
        if startup_notices is not None:
            startup_notices.append(
                "startup: RAG backend fallback to 'hash' because sentence-transformers is not installed. "
                "Install dependency with `pip install sentence-transformers` to restore semantic retrieval."
            )
        return fallback_reader
