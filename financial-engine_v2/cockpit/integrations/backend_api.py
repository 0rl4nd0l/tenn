from __future__ import annotations

from typing import Any

import httpx


class BackendApiClient:
    def __init__(self, base_url: str, *, api_key: str = "") -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.api_key = str(api_key or "").strip()

    def health(self, timeout: float = 5.0) -> dict[str, Any]:
        url = f"{self.base_url}/api/health"
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                return {"ok": True, "url": self.base_url, "payload": payload}
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    def get_price(
        self,
        ticker: str,
        exchange: str = "ASX",
        range_: str = "3mo",
        interval: str = "1d",
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/price"
        params = {
            "ticker": str(ticker or "").strip().upper(),
            "exchange": str(exchange or "").strip().upper(),
            "range": str(range_ or "").strip(),
            "interval": str(interval or "").strip(),
        }
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                return {"ok": True, "url": self.base_url, "payload": payload}
            except httpx.HTTPStatusError as exc:
                detail = None
                try:
                    body = exc.response.json() if exc.response is not None else {}
                    detail = body.get("detail")
                except Exception:
                    detail = None
                code = exc.response.status_code if exc.response is not None else "unknown"
                message = str(detail or f"HTTP {code}")
                return {
                    "ok": False,
                    "url": self.base_url,
                    "status_code": code,
                    "error": message,
                }
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    def rag_query(
        self,
        q: str,
        top_k: int = 10,
        ticker: str | None = None,
        provider: str | None = None,
        language: str = "en",
        date_from: str | None = None,
        date_to: str | None = None,
        timeout: float = 15.0,
        source: str = "news",
    ) -> dict[str, Any]:
        url = f"{self.base_url}/rag/query"
        body: dict[str, Any] = {
            "query": q,
            "source": source,
            "top_k": top_k,
        }
        if ticker is not None:
            body["ticker"] = ticker
        if provider is not None:
            body["provider"] = provider
        if language:
            body["language"] = language
        if date_from is not None:
            body["date_from"] = date_from
        if date_to is not None:
            body["date_to"] = date_to
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.post(url, json=body, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {"results": []}

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            value = "http://localhost:8000"
        if "://" not in value:
            value = f"http://{value}"
        return value.rstrip("/")
