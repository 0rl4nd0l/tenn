from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes import require_api_key
from app.core.db import get_db
from app.services.extraction_review import (
    SNIPPETS_ROOT,
    create_review_session,
    get_error_queue,
    list_review_runs,
    load_review_session,
    submit_review_decision,
)

router = APIRouter(tags=["extraction_review"])


class ExtractionReviewSessionRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)


class ExtractionReviewDecisionRequest(BaseModel):
    item_id: str
    status: Literal["approved", "wrong", "abstain"]
    expected_value: Any | None = None
    reviewer_note: str | None = None


@router.post("/session", dependencies=[Depends(require_api_key)])
def create_session(
    payload: ExtractionReviewSessionRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return create_review_session(
            db,
            payload.document_ids,
            run_ids=payload.run_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/runs")
def recent_runs(
    ticker: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    normalized_ticker = str(ticker or "").strip().upper() or None
    return list_review_runs(db, ticker=normalized_ticker, limit=limit)


@router.get("/session/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    try:
        return load_review_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/session/{session_id}/decision", dependencies=[Depends(require_api_key)])
def review_decision(
    session_id: str,
    payload: ExtractionReviewDecisionRequest,
) -> dict[str, Any]:
    try:
        return submit_review_decision(
            session_id,
            item_id=payload.item_id,
            status=payload.status,
            expected_value=payload.expected_value,
            reviewer_note=payload.reviewer_note,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail=f"review item not found: {exc.args[0]}"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/errors")
def error_queue(limit: int = Query(default=200, ge=1, le=500)) -> dict[str, Any]:
    return get_error_queue(limit=limit)


@router.get("/snippets/{image_name}")
def get_snippet_image(image_name: str) -> FileResponse:
    if "/" in image_name or "\\" in image_name or not image_name.strip():
        raise HTTPException(status_code=400, detail="invalid snippet image name")
    path = (SNIPPETS_ROOT / image_name).resolve()
    try:
        path.relative_to(SNIPPETS_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="invalid snippet image path"
        ) from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="snippet image not found")
    return FileResponse(path, media_type="image/png")
