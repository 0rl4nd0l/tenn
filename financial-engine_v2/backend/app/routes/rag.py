from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from app.services.rag import query_rag


router = APIRouter()


class RagQueryRequest(BaseModel):
    query: str
    ticker: str | None = None
    top_k: int = 8
    debug: bool = False


@router.post("/rag/query")
def rag_query(payload: RagQueryRequest):
    return query_rag(
        query=payload.query,
        ticker=payload.ticker,
        top_k=payload.top_k,
        debug=payload.debug,
    )
