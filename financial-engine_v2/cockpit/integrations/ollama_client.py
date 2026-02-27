from __future__ import annotations

import json
import re
from typing import Callable

import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.model = model
        self.default_options = {
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        }

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

    def chat(self, prompt: str, timeout: float = 120.0, on_chunk: Callable[[str], None] | None = None) -> str:
        with httpx.Client(timeout=timeout) as client:
            url = f"{self.base_url}/api/generate"
            payload = None
            # One retry for transient transport issues.
            for attempt in (1, 2):
                try:
                    if on_chunk is None:
                        response = client.post(
                            url,
                            json={
                                "model": self.model,
                                "prompt": prompt,
                                "stream": False,
                                "options": self.default_options,
                            },
                        )
                        response.raise_for_status()
                        payload = response.json()
                    else:
                        full_response: list[str] = []
                        with client.stream(
                            "POST",
                            url,
                            json={
                                "model": self.model,
                                "prompt": prompt,
                                "stream": True,
                                "options": self.default_options,
                            },
                        ) as response:
                            response.raise_for_status()
                            for line in response.iter_lines():
                                if not line:
                                    continue
                                item = json.loads(line)
                                chunk = str(item.get("response") or "")
                                if chunk:
                                    full_response.append(chunk)
                                    on_chunk(chunk)
                                if item.get("done"):
                                    break
                        payload = {"response": "".join(full_response)}
                    break
                except httpx.HTTPStatusError as exc:
                    body = exc.response.text[:300] if exc.response is not None else ""
                    hint = ""
                    if exc.response is not None and exc.response.status_code == 404:
                        hint = " Hint: if OLLAMA_URL ends with '/api', remove that suffix."
                    raise RuntimeError(
                        f"Ollama request failed ({exc.response.status_code}) at {url}. "
                        f"Response: {body}. Verify OLLAMA_URL, model name, and that Ollama is running.{hint}"
                    ) from exc
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    if attempt == 1:
                        continue
                    raise RuntimeError(
                        f"Ollama request error at {url}: {exc}. "
                        "Verify Ollama is reachable from this process (curl /api/tags) and OLLAMA_URL is correct."
                    ) from exc
                except Exception as exc:
                    raise RuntimeError(
                        f"Ollama request error at {url}: {exc}"
                    ) from exc
        if payload is None:
            raise RuntimeError(f"Ollama request failed with no response payload at {url}")
        return str(payload.get("response") or "")

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
