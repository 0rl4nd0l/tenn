from __future__ import annotations

from cockpit.storage.state import StateStore


def test_route_alias_proposal_is_not_active_until_confirmed(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))

    proposed = store.propose_route_alias_preference(
        source_utterance="when I say my stonks I mean my personal portfolio",
        alias_phrase="my stonks",
        canonical_intent="holdings",
        scope="user",
        provenance_message_id="msg-1",
    )

    assert proposed["confirmation_status"] == "proposed"
    assert proposed["enabled"] is False
    assert store.list_active_route_aliases(canonical_intent="holdings") == []

    confirmed = store.confirm_route_alias_preference(proposed["preference_id"])

    assert confirmed is not None
    assert confirmed["confirmation_status"] == "confirmed"
    assert confirmed["enabled"] is True
    assert store.list_active_route_aliases(canonical_intent="holdings") == [confirmed]


def test_rejected_disabled_and_deleted_aliases_are_inactive(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))
    rejected = store.propose_route_alias_preference(
        source_utterance="holdies means my portfolio",
        alias_phrase="holdies",
        canonical_intent="holdings",
    )
    disabled = store.propose_route_alias_preference(
        source_utterance="bags means my portfolio",
        alias_phrase="bags",
        canonical_intent="holdings",
    )
    deleted = store.propose_route_alias_preference(
        source_utterance="folio means my portfolio",
        alias_phrase="folio",
        canonical_intent="holdings",
    )

    store.reject_route_alias_preference(rejected["preference_id"])
    store.confirm_route_alias_preference(disabled["preference_id"])
    store.disable_route_alias_preference(disabled["preference_id"])
    assert store.delete_route_alias_preference(deleted["preference_id"]) is True

    assert store.list_active_route_aliases(canonical_intent="holdings") == []


def test_route_alias_preferences_do_not_use_generic_user_preferences(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))

    proposed = store.propose_route_alias_preference(
        source_utterance="my stonks means my portfolio",
        alias_phrase="my stonks",
        canonical_intent="holdings",
    )
    store.confirm_route_alias_preference(proposed["preference_id"])

    assert store.get_preferences() == {}


def test_route_alias_preferences_are_stored_outside_thesis_memory(tmp_path) -> None:
    store = StateStore(str(tmp_path / "state.db"))

    store.propose_route_alias_preference(
        source_utterance="my stonks means my portfolio",
        alias_phrase="my stonks",
        canonical_intent="holdings",
    )

    rows = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    table_names = {row[0] for row in rows}
    assert "route_alias_preferences" in table_names
    assert "user_thesis_memory" not in table_names
