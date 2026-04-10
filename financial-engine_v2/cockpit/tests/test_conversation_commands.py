from __future__ import annotations

from cockpit.core.conversation_commands import derive_conversational_command


def test_filestats_phrase_maps_to_slash_command() -> None:
    assert derive_conversational_command("bhp filestats") == "/filestats BHP"


def test_filestat_singular_maps_to_slash_command() -> None:
    assert derive_conversational_command("bhpt filestat") == "/filestats BHPT"


def test_non_command_phrase_returns_none() -> None:
    assert derive_conversational_command("tell me about bhp") is None
