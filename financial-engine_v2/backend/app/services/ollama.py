import json
import re

import httpx


def _normalize_url(base: str) -> str:
    return base.rstrip("/")


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
        r = c.post(f"{_normalize_url(ollama_url)}/api/generate", json={"model": model, "prompt": prompt, "stream": False})
        r.raise_for_status()
        txt = r.json().get("response", "")
    m = re.search(r"\{.*\}", txt, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No JSON found in model response: {txt[:400]}")
    return json.loads(m.group(0))
