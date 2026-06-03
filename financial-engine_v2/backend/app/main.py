from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import inspect, text

from app.api.routes import router
from app.core.config import settings
from app.core.db import engine
from app.models.base import Base


def _ensure_sqlite_schema_compatibility() -> None:
    """Apply tiny local SQLite compatibility fixes not covered by create_all().

    Local isolated mode often uses an existing SQLite DB. SQLAlchemy create_all()
    creates missing tables but does not add new columns, so keep additive fixes for
    recent model columns here until the operator runs a full migration/rebuild.
    """
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "asx_periodic_financials" in table_names:
            columns = {column["name"] for column in inspector.get_columns("asx_periodic_financials")}
            if "metric_provenance" not in columns:
                conn.execute(text("ALTER TABLE asx_periodic_financials ADD COLUMN metric_provenance JSON"))

        if "documents" in table_names:
            columns = {column["name"] for column in inspector.get_columns("documents")}
            if "download_status" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN download_status VARCHAR(32) NOT NULL DEFAULT 'pending'"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_download_status ON documents(download_status)"))
            if "download_error_code" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN download_error_code VARCHAR(128)"))
            if "download_error_detail" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN download_error_detail TEXT"))
            conn.execute(
                text(
                    """
                    UPDATE documents
                    SET download_status = CASE
                            WHEN pdf_sha256 LIKE 'blocked_%' THEN 'blocked'
                            WHEN pdf_sha256 IS NOT NULL AND trim(pdf_sha256) <> '' THEN 'downloaded'
                            ELSE COALESCE(download_status, 'pending')
                        END,
                        download_error_code = CASE
                            WHEN pdf_sha256 LIKE 'blocked_%' THEN pdf_sha256
                            ELSE download_error_code
                        END,
                        pdf_sha256 = CASE
                            WHEN pdf_sha256 LIKE 'blocked_%' THEN ''
                            ELSE pdf_sha256
                        END
                    """
                )
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.docs_root).mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        _ensure_sqlite_schema_compatibility()
    yield


app = FastAPI(title="Financial Engine v2", lifespan=lifespan)
app.include_router(router, prefix="/api")
