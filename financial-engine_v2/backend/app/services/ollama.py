import json
import re

import httpx


def _normalize_url(base: str) -> str:
    return base.rstrip("/")


def _parse_json_response(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Empty response from Ollama")
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"JSON response is not an object: {type(parsed).__name__}")
        return parsed
    except json.JSONDecodeError:
        # Backward compatibility: extract the first JSON object if model adds wrappers.
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError(f"JSON response is not an object: {type(parsed).__name__}")
        return parsed


def ollama_embed(ollama_url: str, model: str, texts: list[str], timeout: float = 180.0) -> list[list[float]]:
    if not texts:
        return []

    base_url = _normalize_url(ollama_url)
    with httpx.Client(timeout=timeout) as c:
        # Prefer modern endpoint first (Ollama >= 0.1.40+), then fallback.
        r = c.post(f"{base_url}/api/embed", json={"model": model, "input": texts})
        if r.status_code == 404:
            vecs = []
            for t in texts:
                legacy = c.post(f"{base_url}/api/embeddings", json={"model": model, "prompt": t})
                legacy.raise_for_status()
                data = legacy.json()
                vec = data.get("embedding")
                if not isinstance(vec, list):
                    raise RuntimeError(f"Bad embeddings response: {data}")
                vecs.append(vec)
            return vecs

        r.raise_for_status()
        data = r.json()
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError(f"Bad embed response: {data}")
        if embeddings and not isinstance(embeddings[0], list):
            raise RuntimeError(f"Bad embed vector shape: {data}")
        return embeddings


def ollama_generate_json(ollama_url: str, model: str, prompt: str, timeout: float = 240.0) -> dict:
    with httpx.Client(timeout=timeout) as c:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            # Ask Ollama to enforce valid JSON output where supported.
            "format": "json",
            "options": {"temperature": 0},
        }
        r = c.post(f"{_normalize_url(ollama_url)}/api/generate", json=payload)
        if r.status_code >= 400:
            # Fallback for older/limited runtimes that reject structured output args.
            fallback = {"model": model, "prompt": prompt, "stream": False}
            r = c.post(f"{_normalize_url(ollama_url)}/api/generate", json=fallback)
        r.raise_for_status()
        txt = r.json().get("response", "")
    return _parse_json_response(txt)
