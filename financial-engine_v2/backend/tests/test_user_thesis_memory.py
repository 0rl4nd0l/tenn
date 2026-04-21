from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.user_thesis_memory import UserThesisMemoryStore


def test_proposal_requires_confirmation_before_apply(tmp_path: Path) -> None:
    store = UserThesisMemoryStore(tmp_path / "user_thesis_memory.sqlite")
    proposal = store.create_proposal(
        ticker="BHP",
        proposal_type="create_thesis",
        statement="Copper growth supports rerating.",
        signal="BUY",
    )

    with pytest.raises(ValueError, match="not confirmed"):
        store.apply_confirmed_proposal(proposal["proposal_id"])


def test_create_confirm_apply_creates_thesis_entry(tmp_path: Path) -> None:
    store = UserThesisMemoryStore(tmp_path / "user_thesis_memory.sqlite")
    proposal = store.create_proposal(
        ticker="BHP",
        proposal_type="create_thesis",
        statement="Copper growth supports rerating.",
        signal="BUY",
    )

    confirmed = store.confirm_proposal(proposal["proposal_id"], note="user said yes")
    assert confirmed["status"] == "confirmed"

    applied = store.apply_confirmed_proposal(proposal["proposal_id"])
    assert applied["proposal"]["status"] == "applied"
    assert applied["entry"]["ticker"] == "BHP"
    assert applied["entry"]["entry_type"] == "thesis"
    assert applied["entry"]["signal"] == "BUY"


def test_add_evidence_uses_supporting_and_disconfirming_types(tmp_path: Path) -> None:
    store = UserThesisMemoryStore(tmp_path / "user_thesis_memory.sqlite")

    supporting = store.create_proposal(
        ticker="BHP",
        proposal_type="add_evidence",
        statement="Unit costs are improving.",
        metadata={"is_supporting": True},
    )
    store.confirm_proposal(supporting["proposal_id"])
    supporting_result = store.apply_confirmed_proposal(supporting["proposal_id"])
    assert supporting_result["entry"]["entry_type"] == "supporting_evidence"

    disconfirming = store.create_proposal(
        ticker="BHP",
        proposal_type="add_evidence",
        statement="Grade quality has deteriorated.",
        metadata={"is_supporting": False},
    )
    store.confirm_proposal(disconfirming["proposal_id"])
    disconfirming_result = store.apply_confirmed_proposal(disconfirming["proposal_id"])
    assert disconfirming_result["entry"]["entry_type"] == "disconfirming_evidence"


def test_retrieve_returns_active_entries_for_primary_ticker(tmp_path: Path) -> None:
    store = UserThesisMemoryStore(tmp_path / "user_thesis_memory.sqlite")
    proposal = store.create_proposal(
        ticker="BHP",
        proposal_type="create_thesis",
        statement="Copper growth supports rerating.",
        signal="BUY",
        confidence=0.81,
    )
    store.confirm_proposal(proposal["proposal_id"])
    store.apply_confirmed_proposal(proposal["proposal_id"])

    payload = store.retrieve(
        query="What is my thesis for BHP?",
        entities={"primary_ticker": "BHP"},
        intent="strategy",
    )

    assert payload["status"] == "ok"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["entry_type"] == "thesis"
    assert payload["items"][0]["active_score"] == pytest.approx(0.81)
