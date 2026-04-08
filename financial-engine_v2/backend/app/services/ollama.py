from __future__ import annotations

import json
import re
from typing import Any

import httpx


def _normalize_url(base: str) -> str:
    normalized = str(base or "").strip().rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[: -len("/v1")]
    return normalized.rstrip("/")


def ollama_embed(
    ollama_url: str,
    model: str,
    texts: list[str],
    timeout: float = 180.0,
    client: httpx.Client | None = None,
) -> list[list[float]]:
    if not texts:
        return []

    base_url = _normalize_url(ollama_url)

    def _do_embed(http_client: httpx.Client) -> list[list[float]]:
        response = http_client.post(f"{base_url}/api/embed", json={"model": model, "input": texts})
        if response.status_code == 404:
            vectors: list[list[float]] = []
            for text in texts:
                legacy = http_client.post(
                    f"{base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                legacy.raise_for_status()
                data = legacy.json()
                vector = data.get("embedding")
                if not isinstance(vector, list):
                    raise RuntimeError(f"Bad embeddings response: {data}")
                vectors.append(list(vector))
            return vectors

        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError(f"Bad embed response: {data}")
        if embeddings and not isinstance(embeddings[0], list):
            raise RuntimeError(f"Bad embed vector shape: {data}")
        return [list(vector) for vector in embeddings]

    if client is not None:
        return _do_embed(client)
    with httpx.Client(timeout=timeout) as http_client:
        return _do_embed(http_client)


def probe_ollama_embeddings(
    ollama_url: str,
    model: str,
    timeout: float = 120.0,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    vectors = ollama_embed(
        ollama_url,
        model,
        ["hello"],
        timeout=timeout,
        client=client,
    )
    if not vectors or not vectors[0]:
        raise RuntimeError("Ollama embedding probe returned an empty vector.")
    return {
        "base_url": _normalize_url(ollama_url),
        "model": str(model or "").strip(),
        "ok": True,
        "dimension": len(vectors[0]),
    }


def ollama_generate_json(
    ollama_url: str,
    model: str,
    prompt: str,
    timeout: float = 240.0,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    base_url = _normalize_url(ollama_url)

    def _do_generate(http_client: httpx.Client) -> dict[str, Any]:
        response = http_client.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        text = response.json().get("response", "")
        match = re.search(r"\{.*\}", str(text), flags=re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in model response: {str(text)[:400]}")
        return json.loads(match.group(0))

    if client is not None:
        return _do_generate(client)
    with httpx.Client(timeout=timeout) as http_client:
        return _do_generate(http_client)
