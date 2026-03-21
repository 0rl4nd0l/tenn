from __future__ import annotations

import json
import os
from typing import Callable

import httpx


class LlamaCppClient:
    """Chat client for llama.cpp servers using the OpenAI-compatible API (/v1/...)."""

    def __init__(self, base_url: str, model: str, api_key: str = "") -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.model = model
        self._api_key = api_key.strip()

    def health(self, timeout: float = 5.0) -> dict:
        url = f"{self.base_url}/v1/models"
        headers = self._build_headers()
        with httpx.Client(timeout=timeout) as client:
            try:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                names = [str(m.get("id", "")).strip() for m in payload.get("data", []) if m.get("id")]
                return {"ok": True, "url": self.base_url, "models": names}
            except Exception as exc:
                return {"ok": False, "url": self.base_url, "error": str(exc)}

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}

        api_key = self._api_key
        if not api_key:
            for env_name in ("LLAMACPP_API_KEY", "LLM_API_KEY"):
                api_key = str(os.getenv(env_name) or "").strip()
                if api_key:
                    break
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        raw_header = str(os.getenv("LLM_AUTH_HEADER") or "").strip()
        if raw_header:
            name, sep, value = raw_header.partition(":")
            if not sep or not name.strip() or not value.strip():
                raise RuntimeError("LLM_AUTH_HEADER must be formatted as 'Header-Name: value'")
            headers[name.strip()] = value.strip()

        return headers

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
        headers = self._build_headers()

        with httpx.Client(timeout=timeout) as client:
            try:
                with client.stream(
                    "POST",
                    url,
                    headers=headers,
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
                hint = ""
                if exc.response is not None and exc.response.status_code == 401:
                    hint = " Verify LLM_API_KEY / LLM_AUTH_HEADER for the llama.cpp endpoint."
                raise RuntimeError(
                    f"llama.cpp request failed ({exc.response.status_code}) at {url}: {body}{hint}"
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
