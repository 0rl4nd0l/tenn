from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.core.db import engine
from app.models.base import Base

app=FastAPI(title='Financial Engine v2')
app.include_router(router, prefix='/api')


@app.on_event("startup")
def startup():
    Path(settings.docs_root).mkdir(parents=True, exist_ok=True)
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
