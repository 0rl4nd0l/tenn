from __future__ import annotations

import json

import httpx
import pytest

from app.services.ollama import ollama_embed


def test_ollama_embed_sends_configured_gpu_option(monkeypatch) -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2]]})

    monkeypatch.setenv("OLLAMA_EMBED_NUM_GPU", "0")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    vectors = ollama_embed(
        "http://127.0.0.1:11434",
        "nomic-embed-text",
        ["health probe"],
        client=client,
    )

    assert vectors == [[0.1, 0.2]]
    assert requests == [
        {
            "model": "nomic-embed-text",
            "input": ["health probe"],
            "options": {"num_gpu": 0},
        }
    ]


def test_ollama_embed_rejects_invalid_gpu_option(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_EMBED_NUM_GPU", "cpu")

    with pytest.raises(RuntimeError, match="Invalid OLLAMA_EMBED_NUM_GPU"):
        ollama_embed("http://127.0.0.1:11434", "nomic-embed-text", ["x"])
