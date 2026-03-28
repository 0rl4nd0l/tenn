from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RichLog


def load_cockpit_help_text(repo_root: Path | None = None) -> str:
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "docs" / "ops" / "cockpit-cheat-sheet.md"
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        return (
            "Cockpit help is unavailable.\n\n"
            f"Expected file: {path}\n"
            f"Error: {exc}"
        )


class HelpScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "close_help", "Close"),
    ]

    DEFAULT_CSS = """
    #help-modal {
        width: 92%;
        height: 90%;
        border: round $accent;
        padding: 1;
        background: $surface;
    }
    #help-log {
        height: 1fr;
        border: round $panel;
        padding: 0 1;
    }
    #help-close-row {
        height: 3;
        align: right middle;
    }
    """

    def __init__(self, title: str = "Cockpit Help", repo_root: Path | None = None) -> None:
        super().__init__()
        self._title = title
        self._repo_root = repo_root

    def compose(self) -> ComposeResult:
        with Vertical(id="help-modal"):
            yield Label(self._title)
            yield RichLog(id="help-log", wrap=True, markup=False, highlight=True)
            with Vertical(id="help-close-row"):
                yield Button("Close", id="help-close", variant="primary")

    def on_mount(self) -> None:
        log = self.query_one("#help-log", RichLog)
        for line in load_cockpit_help_text(self._repo_root).splitlines():
            log.write(line)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close":
            self.dismiss(None)

    def action_close_help(self) -> None:
        self.dismiss(None)
