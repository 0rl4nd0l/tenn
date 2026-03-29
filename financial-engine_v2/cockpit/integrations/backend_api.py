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

    def capabilities(self, timeout: float = 5.0) -> dict[str, Any]:
        url = f"{self.base_url}/api/system/capabilities"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.get(url, headers=headers)
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
                return {
                    "ok": False,
                    "url": self.base_url,
                    "status_code": code,
                    "error": str(detail or f"HTTP {code}"),
                }
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    def apply_proposal(self, proposal_id: str, timeout: float = 30.0) -> dict[str, Any]:
        url = f"{self.base_url}/api/system/proposals/apply"
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.post(url, json={"proposal_id": proposal_id}, headers=headers)
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
                return {
                    "ok": False,
                    "url": self.base_url,
                    "status_code": code,
                    "error": str(detail or f"HTTP {code}"),
                }
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

    def synthesize_research(
        self,
        ticker: str,
        gathered_sources: dict[str, Any],
        *,
        focus: str | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Call POST /research/synthesize to synthesize gathered sources into a brief.

        Uses a long timeout (120s default) because LLM synthesis can be slow.
        """
        url = f"{self.base_url}/research/synthesize"
        body: dict[str, Any] = {
            "ticker": str(ticker or "").strip().upper(),
            "gathered_sources": gathered_sources,
        }
        if focus:
            body["focus"] = str(focus).strip()
        headers: dict[str, str] = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            try:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return response.json() if response.content else {}
            except httpx.HTTPStatusError as exc:
                detail = None
                try:
                    err_body = exc.response.json() if exc.response is not None else {}
                    detail = err_body.get("detail")
                except Exception:
                    pass
                code = exc.response.status_code if exc.response is not None else "unknown"
                raise RuntimeError(f"Synthesis failed (HTTP {code}): {detail or exc}") from exc
            except httpx.TimeoutException as exc:
                raise RuntimeError(f"Synthesis timed out after {timeout}s: {exc}") from exc

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            value = "http://localhost:8000"
        if "://" not in value:
            value = f"http://{value}"
        return value.rstrip("/")
