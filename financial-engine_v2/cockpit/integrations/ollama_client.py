from __future__ import annotations

import re
import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = self._normalize_base_url(base_url)
        self.model = model

    def chat(self, prompt: str, timeout: float = 120.0) -> str:
        with httpx.Client(timeout=timeout) as client:
            url = f"{self.base_url}/api/generate"
            try:
                response = client.post(
                    url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:300] if exc.response is not None else ""
                raise RuntimeError(
                    f"Ollama request failed ({exc.response.status_code}) at {url}. "
                    f"Response: {body}. Verify OLLAMA_URL, model name, and that Ollama is running."
                ) from exc
            except Exception as exc:
                raise RuntimeError(
                    f"Ollama request error at {url}: {exc}"
                ) from exc
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

        return value.rstrip("/")
