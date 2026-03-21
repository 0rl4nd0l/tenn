from __future__ import annotations

import asyncio
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Footer, Header, Label, RichLog, Select, Static


# ---------------------------------------------------------------------------
# Service health probes
# ---------------------------------------------------------------------------

@dataclass
class _ServiceCheck:
    name: str
    url: str           # HTTP URL, or "tcp://host:port" for raw TCP
    status: str = "checking"   # checking | ok | warn | error
    detail: str = ""


def _build_service_checks(backend_url: str, ollama_url: str) -> list[_ServiceCheck]:
    backend_health = backend_url.rstrip("/") + "/api/health"
    return [
        _ServiceCheck("Backend API",  backend_health),
        _ServiceCheck("Ollama",        ollama_url.rstrip("/")),
        _ServiceCheck("llama.cpp",     "http://localhost:8001/v1/models"),
        _ServiceCheck("Qdrant",        "http://localhost:6333/readyz"),
        _ServiceCheck("Redis",         "tcp://localhost:6379"),
    ]


def _probe(svc: _ServiceCheck) -> None:
    """Run a single synchronous probe — called from a thread."""
    if svc.url.startswith("tcp://"):
        _, rest = svc.url.split("://", 1)
        host, port_str = rest.rsplit(":", 1)
        try:
            s = socket.create_connection((host, int(port_str)), timeout=2)
            s.close()
            svc.status = "ok"
            svc.detail = "reachable"
        except Exception as exc:
            svc.status = "error"
            svc.detail = str(exc)[:60]
        return

    try:
        req = urllib.request.Request(svc.url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            svc.status = "ok"
            svc.detail = f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        svc.status = "warn"
        svc.detail = f"HTTP {exc.code}"
    except Exception as exc:
        svc.status = "error"
        svc.detail = str(exc)[:60]


# ---------------------------------------------------------------------------
# Launch profiles
# ---------------------------------------------------------------------------
# Each profile pre-fills the option widgets and injects env vars at launch.
#
# Keys:
#   read_only  bool        — block mutating actions
#   no_web     bool        — disable web fetch tool
#   verbose    bool        — enable DEBUG log level + verbose output
#   env        dict[str,str] — extra env vars forwarded to cockpit.main

LAUNCH_PROFILES: list[tuple[str, str]] = [
    ("full",    "Full"),
    ("testing", "Testing"),
]

PROFILE_FLAGS: dict[str, dict[str, Any]] = {
    "full": {
        "read_only": False,
        "no_web":    False,
        "verbose":   False,
        "env":       {},
    },
    "testing": {
        "read_only": True,
        "no_web":    False,
        "verbose":   True,
        "env": {
            "COCKPIT_LOG_LEVEL":                      "DEBUG",
            "COCKPIT_VERBOSE_LOGGING":                "1",
            "COCKPIT_LOG_TO_STDERR":                  "1",
            "COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS": "15",
        },
    },
}


# ---------------------------------------------------------------------------
# Pre-boot Textual App
# ---------------------------------------------------------------------------

_STATUS_ICON = {"ok": "✓", "warn": "~", "error": "✗", "checking": "·"}
_STATUS_COLOR = {"ok": "green", "warn": "yellow", "error": "red", "checking": "dim"}


class PreBootApp(App[dict[str, Any]]):
    """
    Pre-boot health check and mode selector.

    Returns a dict:
        {"read_only": bool, "no_web": bool, "profile": str, "cancelled": bool}
    """

    CSS = """
    Screen {
        align: center middle;
    }
    #preboot-root {
        width: 80;
        height: auto;
        border: round $accent;
        padding: 1 2;
    }
    #preboot-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
    }
    #health-section {
        border: round $panel;
        padding: 0 1;
        height: auto;
        margin-bottom: 1;
    }
    #health-label {
        text-style: bold;
        margin-bottom: 0;
    }
    #health-log {
        height: 7;
    }
    #options-section {
        border: round $panel;
        padding: 0 1;
        height: auto;
        margin-bottom: 1;
    }
    #options-label {
        text-style: bold;
        margin-bottom: 0;
    }
    #profile-row {
        height: 3;
        margin-top: 1;
    }
    #profile-label {
        width: 10;
        padding-top: 1;
    }
    #opt-profile {
        width: 1fr;
    }
    #btn-row {
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    #btn-cancel {
        margin-right: 1;
    }
    """

    BINDINGS = [
        Binding("enter", "launch", "Launch"),
        Binding("escape", "cancel_boot", "Cancel"),
    ]

    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        ollama_url: str = "http://localhost:11434",
        initial_flags: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self._backend_url = backend_url
        self._ollama_url = ollama_url
        self._initial = initial_flags or {}
        self._checks = _build_service_checks(backend_url, ollama_url)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="preboot-root"):
            yield Label("Cockpit  —  Pre-Boot Setup", id="preboot-title")

            with Vertical(id="health-section"):
                yield Label("Service Health", id="health-label")
                yield RichLog(id="health-log", wrap=False, markup=False, max_lines=10)

            with Vertical(id="options-section"):
                yield Label("Launch Options", id="options-label")
                yield Checkbox(
                    "Read-only mode  (block mutating actions)",
                    id="opt-readonly",
                    value=self._initial.get("read_only", False),
                )
                yield Checkbox(
                    "Enable web fetch",
                    id="opt-web",
                    value=not self._initial.get("no_web", True),
                )
                yield Checkbox(
                    "Verbose logging  (DEBUG level + stderr)",
                    id="opt-verbose",
                    value=self._initial.get("verbose", False),
                )
                with Horizontal(id="profile-row"):
                    yield Label("Profile:", id="profile-label")
                    yield Select(
                        LAUNCH_PROFILES,
                        value=self._initial.get("profile", LAUNCH_PROFILES[0][0]),
                        id="opt-profile",
                    )

            with Horizontal(id="btn-row"):
                yield Button("Cancel", id="btn-cancel", variant="warning")
                yield Button("Launch  [Enter]", id="btn-launch", variant="success")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        log = self.query_one("#health-log", RichLog)
        for svc in self._checks:
            log.write(f"  {_STATUS_ICON['checking']}  {svc.name}")
        asyncio.create_task(self._run_health_checks())

    async def _run_health_checks(self) -> None:
        await asyncio.gather(*[asyncio.to_thread(_probe, svc) for svc in self._checks])
        self._render_health()

    def _render_health(self) -> None:
        log = self.query_one("#health-log", RichLog)
        log.clear()
        for svc in self._checks:
            icon = _STATUS_ICON[svc.status]
            log.write(f"  {icon}  {svc.name:<16} {svc.detail}")

    # ------------------------------------------------------------------
    # Profile selection → pre-fill option widgets
    # ------------------------------------------------------------------

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "opt-profile":
            return
        profile = str(event.value or "")
        flags = PROFILE_FLAGS.get(profile, {})
        if "read_only" in flags:
            self.query_one("#opt-readonly", Checkbox).value = flags["read_only"]
        if "no_web" in flags:
            self.query_one("#opt-web", Checkbox).value = not flags["no_web"]
        if "verbose" in flags:
            self.query_one("#opt-verbose", Checkbox).value = flags["verbose"]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-launch":
            self.action_launch()
        elif event.button.id == "btn-cancel":
            self.action_cancel_boot()

    def action_launch(self) -> None:
        read_only = self.query_one("#opt-readonly", Checkbox).value
        web_enabled = self.query_one("#opt-web", Checkbox).value
        verbose = self.query_one("#opt-verbose", Checkbox).value
        profile = str(self.query_one("#opt-profile", Select).value or LAUNCH_PROFILES[0][0])
        env = dict(PROFILE_FLAGS.get(profile, {}).get("env", {}))
        if verbose:
            env.setdefault("COCKPIT_LOG_LEVEL", "DEBUG")
            env.setdefault("COCKPIT_VERBOSE_LOGGING", "1")
            env.setdefault("COCKPIT_LOG_TO_STDERR", "1")
        self.exit({
            "read_only": read_only,
            "no_web": not web_enabled,
            "verbose": verbose,
            "profile": profile,
            "env": env,
            "cancelled": False,
        })

    def action_cancel_boot(self) -> None:
        self.exit({"cancelled": True})
