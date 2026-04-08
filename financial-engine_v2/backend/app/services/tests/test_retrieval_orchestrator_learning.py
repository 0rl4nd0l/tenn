from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.retrieval_orchestrator import RetrievalOrchestrator


@pytest.fixture
def temp_prefs_file():
    """Create a temporary chat_preferences.json file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


def test_retrieve_uses_learned_top_k(temp_prefs_file, monkeypatch):
    """Rule 0: retrieve() should use learned top_k from chat_preferences."""
    prefs = {
        "schema_version": 1,
        "updated_at": "2026-04-07T12:00:00Z",
        "source_session_id": "test_session",
        "metric_weights": {
            "w_retrieval": 0.4,
            "w_confidence": 0.35,
            "w_coherence": 0.25,
            "sample_count": 20,
        },
        "retrieval_preferences": {
            "rag_financial_synthesis": {
                "top_k": 12,
                "commentary_weight": 0.3,
                "avg_composite_metric": 0.88,
                "sample_count": 20,
            }
        },
        "router_preferences": {},
    }
    temp_prefs_file.write_text(json.dumps(prefs), encoding="utf-8")

    # Patch the _CHAT_PREFERENCES_PATH constant
    import app.services.retrieval_orchestrator as ro_module

    monkeypatch.setattr(ro_module, "_CHAT_PREFERENCES_PATH", temp_prefs_file)

    # Create orchestrator with null dependencies to avoid real Qdrant calls
    orchestrator = RetrievalOrchestrator(
        classifier=RetrievalOrchestrator._NullFrameworkClassifier(),
        framework_retriever=RetrievalOrchestrator._NullFrameworkRetriever(),
        hybrid_retriever=RetrievalOrchestrator._NullHybridRetriever(),
        reranker=RetrievalOrchestrator._NullReranker(),
        commentary_retriever=RetrievalOrchestrator._NullHybridRetriever(),
        commentary_reranker=RetrievalOrchestrator._NullReranker(),
    )

    # Mock the reranker to capture the top_k argument
    mock_reranker = MagicMock(return_value=[])
    orchestrator.reranker.rerank = mock_reranker
    mock_commentary_reranker = MagicMock(return_value=[])
    orchestrator.commentary_reranker.rerank = mock_commentary_reranker

    # Call retrieve with default top_k_chunks=8
    result = orchestrator.retrieve("What is BHP's revenue?")

    # Verify the learned top_k=12 was used (not the default 8)
    assert mock_reranker.call_count == 1
    call_kwargs = mock_reranker.call_args[1]
    assert call_kwargs["top_k"] == 12

    # Verify commentary_weight calculation
    # With commentary_weight=0.3, total_target = 12/(1-0.3) = 17.14
    # commentary = 17.14 * 0.3 = 5.14 → 5
    assert mock_commentary_reranker.call_count == 1
    commentary_kwargs = mock_commentary_reranker.call_args[1]
    assert commentary_kwargs["top_k"] == 5


def test_retrieve_uses_hardcoded_defaults_when_no_prefs(monkeypatch):
    """When chat_preferences.json doesn't exist, use hardcoded defaults."""
    import app.services.retrieval_orchestrator as ro_module

    nonexistent_path = Path("/tmp/nonexistent_chat_prefs.json")
    monkeypatch.setattr(ro_module, "_CHAT_PREFERENCES_PATH", nonexistent_path)

    orchestrator = RetrievalOrchestrator(
        classifier=RetrievalOrchestrator._NullFrameworkClassifier(),
        framework_retriever=RetrievalOrchestrator._NullFrameworkRetriever(),
        hybrid_retriever=RetrievalOrchestrator._NullHybridRetriever(),
        reranker=RetrievalOrchestrator._NullReranker(),
        commentary_retriever=RetrievalOrchestrator._NullHybridRetriever(),
        commentary_reranker=RetrievalOrchestrator._NullReranker(),
    )

    mock_reranker = MagicMock(return_value=[])
    orchestrator.reranker.rerank = mock_reranker

    # Call with default top_k_chunks=8
    orchestrator.retrieve("What is RIO's debt?")

    # Should use hardcoded default
    call_kwargs = mock_reranker.call_args[1]
    assert call_kwargs["top_k"] == 8


def test_retrieve_ignores_malformed_prefs(temp_prefs_file, monkeypatch):
    """When chat_preferences.json is malformed, fall back to defaults."""
    temp_prefs_file.write_text("{invalid json", encoding="utf-8")

    import app.services.retrieval_orchestrator as ro_module

    monkeypatch.setattr(ro_module, "_CHAT_PREFERENCES_PATH", temp_prefs_file)

    orchestrator = RetrievalOrchestrator(
        classifier=RetrievalOrchestrator._NullFrameworkClassifier(),
        framework_retriever=RetrievalOrchestrator._NullFrameworkRetriever(),
        hybrid_retriever=RetrievalOrchestrator._NullHybridRetriever(),
        reranker=RetrievalOrchestrator._NullReranker(),
        commentary_retriever=RetrievalOrchestrator._NullHybridRetriever(),
        commentary_reranker=RetrievalOrchestrator._NullReranker(),
    )

    mock_reranker = MagicMock(return_value=[])
    orchestrator.reranker.rerank = mock_reranker

    orchestrator.retrieve("What is FMG's capex?")

    # Should fall back to hardcoded default
    call_kwargs = mock_reranker.call_args[1]
    assert call_kwargs["top_k"] == 8
