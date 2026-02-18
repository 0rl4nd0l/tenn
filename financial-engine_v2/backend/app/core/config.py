from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = "sqlite:///./data/fe_local.db"
    celery_broker_url: str = "memory://"
    celery_result_backend: str = "cache+memory://"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "asx_docs"
    docs_root: str = "./data/asx/docs"
    ollama_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    extract_model: str = "llama3.1:8b"

    # Runtime controls for local isolated execution.
    task_mode: str = "celery"  # celery | sync
    auto_create_tables: bool = False
    enable_embeddings: bool = True
    enable_qdrant: bool = True
    enable_extraction: bool = True
    enable_marketindex_fallback: bool = False
    marketindex_announcements_file: str = "../data/raw/marketindex_announcements.json"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
