from __future__ import annotations

from pathlib import Path
import shlex


def _dockerfile_copy_instructions(dockerfile: Path) -> list[tuple[tuple[str, ...], str]]:
    instructions: list[tuple[tuple[str, ...], str]] = []
    for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = shlex.split(line)
        if len(parts) >= 3 and parts[0].upper() == "COPY":
            instructions.append((tuple(parts[1:-1]), parts[-1]))
    return instructions


def test_backend_dockerfile_packages_cockpit_import_dependency() -> None:
    dockerfile = Path(__file__).resolve().parents[1] / "Dockerfile"

    copy_instructions = _dockerfile_copy_instructions(dockerfile)

    assert any(
        any(source.rstrip("/") == "cockpit" for source in sources)
        and destination.rstrip("/") == "/app/cockpit"
        for sources, destination in copy_instructions
    )
