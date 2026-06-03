import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def _resolve_project_path(value: str) -> str:
    p = Path(str(value or "")).expanduser()
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return str(p)


def _normalize_database_url(url: str) -> str:
    text = str(url or "").strip()
    if not text.lower().startswith("sqlite:///"):
        return text
    raw_path = text[len("sqlite:///") :]
    if raw_path in {"", ":memory:"} or raw_path.startswith("file:"):
        return text
    p = Path(raw_path).expanduser()
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return _sqlite_url(p)


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = _sqlite_url(DATA_ROOT / "fe_local.db")
    celery_broker_url: str = "memory://"
    celery_result_backend: str = "cache+memory://"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "asx_docs"
    docs_root: str = str(DATA_ROOT / "asx" / "docs")
    ollama_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    extract_model: str = "llama3:latest"
    api_key: str = ""

    # Runtime controls for local isolated execution.
    task_mode: str = "celery"  # celery | sync
    auto_create_tables: bool = False
    enable_embeddings: bool = True
    enable_qdrant: bool = True
    enable_extraction: bool = True
    enable_marketindex_fallback: bool = False
    marketindex_announcements_file: str = str(DATA_ROOT / "raw" / "marketindex_announcements.json")
    enable_importance_classification: bool = True
    importance_output_root: str = str(DATA_ROOT / "asx" / "importance")
    importance_materialize_output: bool = False
    importance_include_pdf_text: bool = True
    importance_link_mode: str = "symlink"
    importance_sort_source_docs: bool = True

    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")


settings = Settings()
if not settings.api_key:
    settings.api_key = str(os.environ.get("TENN_API_KEY", "") or "").strip()
settings.database_url = _normalize_database_url(settings.database_url)
settings.docs_root = _resolve_project_path(settings.docs_root)
settings.marketindex_announcements_file = _resolve_project_path(settings.marketindex_announcements_file)
settings.importance_output_root = _resolve_project_path(settings.importance_output_root)
