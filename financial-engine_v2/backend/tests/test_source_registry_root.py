from __future__ import annotations

from pathlib import Path

from app.services import source_registry


def test_existing_research_memory_store_wins_before_writable_fallback(
    tmp_path: Path,
) -> None:
    configured = tmp_path / "configured" / "reports" / "research_memory"
    project_data = tmp_path / "project" / "data" / "reports" / "research_memory"
    legacy = tmp_path / "backend" / "reports" / "research_memory"
    project_data.mkdir(parents=True)
    (project_data / "market_memory.sqlite").write_bytes(b"sqlite placeholder")

    selected = source_registry._select_research_memory_root(
        [configured, project_data, legacy]
    )

    assert selected == project_data
    assert not legacy.exists()


def test_explicit_research_memory_root_override_wins_when_it_has_store(
    monkeypatch,
    tmp_path: Path,
) -> None:
    override = tmp_path / "override" / "research_memory"
    configured = tmp_path / "configured" / "reports" / "research_memory"
    override.mkdir(parents=True)
    (override / "company_memory.sqlite").write_bytes(b"sqlite placeholder")
    monkeypatch.setenv("TENN_RESEARCH_MEMORY_ROOT", str(override))

    candidates = [
        source_registry._configured_research_memory_root(),
        configured,
    ]
    selected = source_registry._select_research_memory_root(
        [candidate for candidate in candidates if candidate is not None]
    )

    assert selected == override
    assert not configured.exists()


def test_writable_configured_root_wins_when_no_existing_store(tmp_path: Path) -> None:
    configured = tmp_path / "configured" / "reports" / "research_memory"
    project_data = tmp_path / "project" / "data" / "reports" / "research_memory"
    legacy = tmp_path / "backend" / "reports" / "research_memory"

    selected = source_registry._select_research_memory_root(
        [configured, project_data, legacy]
    )

    assert selected == configured
    assert configured.exists()
    assert not legacy.exists()
