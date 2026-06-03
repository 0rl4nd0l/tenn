from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import settings


def _valid_api_key(provided: str | None) -> bool:
    expected = str(getattr(settings, "api_key", "") or "").strip()
    if not expected:
        return False
    return str(provided or "").strip() == expected


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Require an operator API key for non-health API routes.

    Accept either `X-API-Key: <key>` or `Authorization: Bearer <key>`.
    The check deliberately fails closed when no `API_KEY`/`TENN_API_KEY` is configured.
    """
    bearer_token = None
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            bearer_token = token

    if _valid_api_key(x_api_key) or _valid_api_key(bearer_token):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key required",
        headers={"WWW-Authenticate": "Bearer"},
    )
