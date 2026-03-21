from __future__ import annotations

import json
import re
from typing import Callable

import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.model = model

    def health(self, timeout: float = 5.0) -> dict:
        url = f"{self.base_url}/api/tags"
        with httpx.Client(timeout=timeout) as client:
            try:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json() if response.content else {}
                names = []
                for item in payload.get("models", []) if isinstance(payload, dict) else []:
                    name = str((item or {}).get("name", "")).strip()
                    if name:
                        names.append(name)
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
        url = f"{self.base_url}/api/generate"
        parts: list[str] = []
        emitted_any = False

        with httpx.Client(timeout=timeout) as client:
            # One retry for transient startup issues before any text has been emitted.
            for attempt in (1, 2):
                try:
                    with client.stream(
                        "POST",
                        url,
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": True,
                        },
                    ) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line:
                                continue
                            if isinstance(line, bytes):
                                line = line.decode("utf-8", errors="ignore")
                            try:
                                payload = json.loads(str(line))
                            except json.JSONDecodeError:
                                continue

                            chunk = str(payload.get("response") or "")
                            if chunk:
                                parts.append(chunk)
                                emitted_any = True
                                if on_chunk is not None:
                                    on_chunk(chunk)

                            if payload.get("done"):
                                return "".join(parts)

                    break
                except httpx.HTTPStatusError as exc:
                    body = self._error_body_preview(exc.response)
                    hint = ""
                    if exc.response is not None and exc.response.status_code == 404:
                        hint = " Hint: if OLLAMA_URL ends with '/api', remove that suffix."
                    raise RuntimeError(
                        f"Ollama request failed ({exc.response.status_code}) at {url}. "
                        f"Response: {body}. Verify OLLAMA_URL, model name, and that Ollama is running.{hint}"
                    ) from exc
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    if attempt == 1 and not emitted_any:
                        continue
                    raise RuntimeError(
                        f"Ollama request error at {url}: {exc}. "
                        "Verify Ollama is reachable from this process (curl /api/tags) and OLLAMA_URL is correct."
                    ) from exc
                except Exception as exc:
                    raise RuntimeError(
                        f"Ollama request error at {url}: {exc}"
                    ) from exc

        if not parts:
            raise RuntimeError(f"Ollama request failed with no response payload at {url}")
        return "".join(parts)

    @staticmethod
    def _normalize_base_url(raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            value = "http://localhost:11434"

        # Common malformed value: "localhost11434" -> "localhost:11434"
        malformed = re.fullmatch(r"(localhost)(\d{2,5})", value)
        if malformed:
            value = f"{malformed.group(1)}:{malformed.group(2)}"

        if "://" not in value:
            value = f"http://{value}"

        value = value.rstrip("/")
        if value.lower().endswith("/api"):
            value = value[:-4]
        return value
