from __future__ import annotations

from pathlib import Path

import pytest

from cockpit.integrations.qual_context_bootstrap import build_qual_context_reader


class _BackendClient:
    def rag_query(self, **kwargs):  # pragma: no cover - not exercised here
        return {"results": []}


def test_build_qual_context_reader_ignores_legacy_local_embedding_config() -> None:
    reader = build_qual_context_reader(
        repo_root=Path("."),
        qc_cfg={
            "embed_backend": "hash",
            "embed_model": "hash",
            "corpus_filter": "company",
            "ticker_match_mode": "soft",
            "top_k": 5,
            "timeout": 7.5,
        },
        backend_api_client=_BackendClient(),
        context_name="qualitative_context",
    )

    assert reader.embed_backend == "ollama"
    assert reader.embed_model == "nomic-embed-text"
    assert reader.corpus_filter == "company"
    assert reader.ticker_match_mode == "soft"
    assert reader.top_k == 5
    assert reader.timeout == 7.5


def test_build_qual_context_reader_requires_backend_rag_query() -> None:
    with pytest.raises(RuntimeError, match="backend_api_client\\.rag_query"):
        build_qual_context_reader(
            repo_root=Path("."),
            qc_cfg={"embed_backend": "sentence-transformers"},
            backend_api_client=object(),
            context_name="qualitative_context",
        )
