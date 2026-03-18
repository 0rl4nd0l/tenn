from __future__ import annotations

from typing import Optional

import httpx

from app.services.llamacpp_runtime import (
    build_embedding_headers,
    resolve_embedding_runtime_config,
    verify_llm_models,
)

EMBEDDINGS_UNAVAILABLE_ERROR = (
    "Embeddings endpoint unavailable. Start llama.cpp with --embeddings or set "
    "EMBEDDING_URL to a working embeddings server."
)


def _build_request_headers() -> dict[str, str]:
    headers = build_embedding_headers()
    headers["Content-Type"] = "application/json"
    return headers


def _parse_embeddings_payload(data: object, expected_count: int) -> list[list[float]]:
    if not isinstance(data, dict):
        raise RuntimeError(f"Bad llama.cpp embeddings response: {data}")

    rows = data.get("data")
    if not isinstance(rows, list):
        raise RuntimeError(f"Bad llama.cpp embeddings response: {data}")

    embeddings = [item["embedding"] for item in rows]
    if len(embeddings) != expected_count:
        raise RuntimeError(
            f"embedding batch size mismatch: expected {expected_count}, got {len(embeddings)}"
        )
    return [list(vector) for vector in embeddings]


def _raise_if_embeddings_unavailable(response: object) -> None:
    status_code = int(getattr(response, "status_code", 0) or 0)
    if status_code == 501:
        raise RuntimeError(EMBEDDINGS_UNAVAILABLE_ERROR)


def probe_llamacpp_embeddings(
    base_url: str,
    model: str,
    timeout: float = 30.0,
    client: Optional[httpx.Client] = None,
) -> dict[str, object]:
    resolved_base_url, resolved_model = resolve_embedding_runtime_config(
        base_url=base_url,
        model=model,
    )
    headers = _build_request_headers()
    own_client = client is None
    payload = {
        "model": resolved_model,
        "input": ["hello"],
    }

    def _do_probe(http_client: httpx.Client) -> dict[str, object]:
        verify_llm_models(
            resolved_base_url,
            headers=headers,
            timeout=min(timeout, 30.0),
            client=http_client,
        )

        response = http_client.post(
            f"{resolved_base_url}/v1/embeddings",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        _raise_if_embeddings_unavailable(response)
        response.raise_for_status()
        embeddings = _parse_embeddings_payload(response.json(), expected_count=1)
        vector = embeddings[0]
        if not vector:
            raise RuntimeError("Embedding probe returned an empty vector.")
        return {
            "base_url": resolved_base_url,
            "model": resolved_model,
            "ok": True,
            "dimension": len(vector),
        }

    if own_client:
        with httpx.Client(timeout=timeout) as http_client:
            return _do_probe(http_client)
    return _do_probe(client)


def llamacpp_embed(
    base_url: str,
    model: str,
    texts: list[str],
    timeout: float = 120.0,
    client: Optional[httpx.Client] = None,
    *,
    verify_models: bool = True,
) -> list[list[float]]:
    if not texts:
        return []

    resolved_base_url, resolved_model = resolve_embedding_runtime_config(
        base_url=base_url,
        model=model,
    )
    headers = _build_request_headers()
    own_client = client is None
    payload = {
        "model": resolved_model,
        "input": texts,
    }

    def _do_embed(http_client: httpx.Client) -> list[list[float]]:
        if verify_models:
            verify_llm_models(
                resolved_base_url,
                headers=headers,
                timeout=min(timeout, 30.0),
                client=http_client,
            )

        response = http_client.post(
            f"{resolved_base_url}/v1/embeddings",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        _raise_if_embeddings_unavailable(response)
        response.raise_for_status()
        return _parse_embeddings_payload(response.json(), expected_count=len(texts))

    if own_client:
        with httpx.Client(timeout=timeout) as http_client:
            return _do_embed(http_client)
    return _do_embed(client)
