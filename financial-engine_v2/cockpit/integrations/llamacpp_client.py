from __future__ import annotations

import json
from typing import Callable

import httpx


class LlamaCppClient:
    """Chat client for llama.cpp servers using the OpenAI-compatible API (/v1/...)."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.model = model

    def health(self, timeout: float = 5.0) -> dict:
        url = f"{self.base_url}/v1/models"
        with httpx.Client(timeout=timeout) as client:
            try:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                names = [str(m.get("id", "")).strip() for m in payload.get("data", []) if m.get("id")]
                return {"ok": True, "url": self.base_url, "models": names}
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    @staticmethod
    def _error_body_preview(response: httpx.Response | None, limit: int = 300) -> str:
        if response is None:
            return ""
        try:
            body = response.read().decode("utf-8", errors="replace")
        except Exception:
            try:
                body = response.text
            except Exception:
                body = ""
        return body[:limit]

    def chat(self, prompt: str, timeout: float = 120.0, on_chunk: Callable[[str], None] | None = None) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        parts: list[str] = []

        with httpx.Client(timeout=timeout) as client:
            try:
                with client.stream(
                    "POST",
                    url,
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line:
                            continue
                        if isinstance(line, bytes):
                            line = line.decode("utf-8", errors="ignore")
                        if line == "data: [DONE]":
                            break
                        if line.startswith("data: "):
                            line = line[6:]
                        try:
                            payload = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        choices = payload.get("choices") or []
                        chunk = (choices[0].get("delta", {}) if choices else {}).get("content") or ""
                        if chunk:
                            parts.append(chunk)
                            if on_chunk is not None:
                                on_chunk(chunk)
            except httpx.HTTPStatusError as exc:
                body = self._error_body_preview(exc.response)
                raise RuntimeError(
                    f"llama.cpp request failed ({exc.response.status_code}) at {url}: {body}"
                ) from exc
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                raise RuntimeError(
                    f"llama.cpp request error at {url}: {exc}. "
                    "Verify llama-server is running (curl http://localhost:8001/v1/models)."
                ) from exc

        if not parts:
            raise RuntimeError(f"llama.cpp returned no content from {url}")
        return "".join(parts)

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            value = "http://localhost:8001"
        if "://" not in value:
            value = f"http://{value}"
        value = value.rstrip("/")
        # Strip trailing /v1 if present — we append it ourselves per-call.
        if value.lower().endswith("/v1"):
            value = value[:-3]
        return value
