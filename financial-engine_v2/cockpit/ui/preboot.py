from __future__ import annotations

import asyncio
import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Label, RichLog, Select, Static

from cockpit.integrations.llamacpp_manager import (
    discover_models,
    find_llama_server_process,
    models_dir_from_process,
    restart_with_model,
)


# ---------------------------------------------------------------------------
# Service health probes
# ---------------------------------------------------------------------------

@dataclass
class _ServiceCheck:
    name: str
    url: str           # HTTP URL, or "tcp://host:port" for raw TCP
    status: str = "checking"   # checking | ok | warn | error
    detail: str = ""
    models: list[str] = field(default_factory=list)


def _build_service_checks(backend_url: str, ollama_url: str) -> list[_ServiceCheck]:
    backend_health = backend_url.rstrip("/") + "/api/health"
    # Probe /api/tags for Ollama so we also get the installed model list.
    ollama_tags = ollama_url.rstrip("/") + "/api/tags"
    return [
        _ServiceCheck("Backend API",  backend_health),
        _ServiceCheck("Ollama",        ollama_tags),
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
            if svc.name in ("Ollama", "llama.cpp"):
                try:
                    body = json.loads(resp.read().decode("utf-8"))
                    if svc.name == "Ollama":
                        svc.models = [
                            m.get("name", "").strip()
                            for m in body.get("models", [])
                            if m.get("name", "").strip()
                        ]
                    else:  # llama.cpp
                        svc.models = [
                            m.get("id", "").strip()
                            for m in body.get("data", [])
                            if m.get("id", "").strip()
                        ]
                except Exception:
                    pass
    except urllib.error.HTTPError as exc:
        svc.status = "warn"
        svc.detail = f"HTTP {exc.code}"
    except Exception as exc:
        svc.status = "error"
        svc.detail = str(exc)[:60]


# ---------------------------------------------------------------------------
# Launch profiles
# ---------------------------------------------------------------------------

LAUNCH_PROFILES: list[tuple[str, str]] = [
    ("Full",    "full"),
    ("Testing", "testing"),
]

PROFILE_FLAGS: dict[str, dict[str, Any]] = {
    "full": {
        "read_only":  False,
        "no_web":     False,
        "verbose":    False,
        "enable_rag": True,
        "env":        {},
    },
    "testing": {
        "read_only":  True,
        "no_web":     False,
        "verbose":    True,
        "enable_rag": False,
        "env": {
            "COCKPIT_LOG_LEVEL":                      "DEBUG",
            "COCKPIT_VERBOSE_LOGGING":                "1",
            "COCKPIT_LOG_TO_STDERR":                  "1",
            "COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS": "15",
        },
    },
}

LLM_PROVIDERS: list[tuple[str, str]] = [
    ("Ollama  (localhost:11434)", "ollama"),
    ("llama.cpp  (localhost:8001)", "llamacpp"),
]

_FALLBACK_MODELS: list[tuple[str, str]] = [("llama3:latest", "llama3:latest")]


def _resolve_initial_option_state(initial_flags: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(initial_flags or {})
    valid_profiles = {value for _, value in LAUNCH_PROFILES}
    profile = raw.get("profile")
    if profile not in valid_profiles:
        profile = LAUNCH_PROFILES[0][1]
    defaults = PROFILE_FLAGS.get(profile, {})
    valid_providers = {value for _, value in LLM_PROVIDERS}
    llm_provider = raw.get("llm_provider", "ollama")
    if llm_provider not in valid_providers:
        llm_provider = "ollama"
    return {
        "profile": profile,
        "read_only": bool(raw["read_only"]) if "read_only" in raw else bool(defaults.get("read_only", False)),
        "no_web": bool(raw["no_web"]) if "no_web" in raw else bool(defaults.get("no_web", False)),
        "verbose": bool(raw["verbose"]) if "verbose" in raw else bool(defaults.get("verbose", False)),
        "enable_rag": bool(raw["enable_rag"]) if "enable_rag" in raw else True,
        "llm_provider": llm_provider,
        "llm_model": raw.get("llm_model", "llama3:latest"),
    }


# ---------------------------------------------------------------------------
# Pre-boot Textual App
# ---------------------------------------------------------------------------

_STATUS_ICON = {"ok": "[OK]", "warn": "[??]", "error": "[!!]", "checking": "[ ]"}


class PreBootScreen(Screen):
    """
    Pre-boot setup as a Screen — embeddable in any App (e.g. CockpitWebApp).
    Calls on_launch(flags) when the user clicks Launch, or on_cancel() on Escape.
    """

    BINDINGS = [
        Binding("enter", "launch", "Launch"),
        Binding("escape", "cancel_boot", "Cancel"),
    ]

    _SHARED_CSS = """
    #preboot-root {
        width: 1fr;
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    #preboot-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        text-align: center;
        width: 1fr;
    }
    #health-section {
        border: round $accent;
        padding: 0 1;
        height: auto;
        margin-bottom: 1;
        width: 1fr;
    }
    #health-label { text-style: bold; }
    #health-log { height: 5; }
    #options-section {
        border: round $panel;
        padding: 0 1;
        height: auto;
        margin-bottom: 1;
        width: 1fr;
    }
    #options-label { text-style: bold; }
    #profile-row { height: 3; margin-top: 1; width: 1fr; }
    #profile-label { width: 10; padding-top: 1; }
    #opt-profile { width: 1fr; }
    #llm-section {
        border: round $panel;
        padding: 0 1;
        height: auto;
        margin-bottom: 1;
        width: 1fr;
    }
    #llm-label { text-style: bold; }
    #provider-row { height: 3; margin-top: 1; width: 1fr; }
    #provider-label { width: 10; padding-top: 1; }
    #opt-provider { width: 1fr; }
    #provider-status { width: 22; padding-top: 1; color: $text-muted; text-align: right; }
    #model-row { height: 3; margin-top: 1; width: 1fr; }
    #model-label { width: 10; padding-top: 1; }
    #opt-model { width: 1fr; }
    #btn-row { height: 3; margin-top: 1; margin-bottom: 1; width: 1fr; }
    #btn-spacer { width: 1fr; }
    #btn-cancel { margin-right: 1; width: auto; }
    #btn-launch { width: auto; }
    """

    DEFAULT_CSS = _SHARED_CSS

    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        ollama_url: str = "http://localhost:11434",
        initial_flags: dict[str, Any] | None = None,
        on_launch: Callable[[dict[str, Any]], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._backend_url = backend_url
        self._ollama_url = ollama_url
        self._initial = _resolve_initial_option_state(initial_flags)
        self._checks = _build_service_checks(backend_url, ollama_url)
        self._on_launch = on_launch
        self._on_cancel = on_cancel
        # Guard: Select fires Changed on mount; block on_select_changed until
        # initial widget values are set and the first refresh has passed.
        self._selects_active = False
        # llama.cpp process info + discovered models (populated after health checks).
        self._llama_proc: dict | None = None
        self._llama_fs_models: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="preboot-root"):
            yield Label("Cockpit  —  Pre-Boot Setup", id="preboot-title")
            with Vertical(id="health-section"):
                yield Label("Service Health", id="health-label")
                yield RichLog(id="health-log", wrap=False, markup=False, max_lines=10)
            with Vertical(id="options-section"):
                yield Label("Launch Options", id="options-label")
                yield Checkbox("Read-only mode  (block mutating actions)", id="opt-readonly")
                yield Checkbox("Enable web fetch", id="opt-web")
                yield Checkbox("Enable embedding + RAG  (qualitative_context, news_context)", id="opt-rag")
                yield Checkbox("Verbose logging  (DEBUG level + stderr)", id="opt-verbose")
                with Horizontal(id="profile-row"):
                    yield Label("Profile:", id="profile-label")
                    yield Select(LAUNCH_PROFILES, value=self._initial.get("profile", LAUNCH_PROFILES[0][1]), id="opt-profile")
            with Vertical(id="llm-section"):
                yield Label("LLM Backend", id="llm-label")
                with Horizontal(id="provider-row"):
                    yield Label("Provider:", id="provider-label")
                    yield Select(LLM_PROVIDERS, value=self._initial.get("llm_provider", "ollama"), id="opt-provider")
                    yield Static("", id="provider-status")
                with Horizontal(id="model-row"):
                    yield Label("Model:", id="model-label")
                    yield Select(_FALLBACK_MODELS, value="llama3:latest", id="opt-model", allow_blank=False)
            with Horizontal(id="btn-row"):
                yield Static("", id="btn-spacer")
                yield Button("Cancel", id="btn-cancel", variant="warning")
                yield Button("Launch  [Enter]", id="btn-launch", variant="success")

    def on_mount(self) -> None:
        self.query_one("#opt-readonly", Checkbox).value = self._initial["read_only"]
        self.query_one("#opt-web", Checkbox).value = not self._initial["no_web"]
        self.query_one("#opt-rag", Checkbox).value = self._initial["enable_rag"]
        self.query_one("#opt-verbose", Checkbox).value = self._initial["verbose"]
        log = self.query_one("#health-log", RichLog)
        for svc in self._checks:
            log.write(f"  {_STATUS_ICON['checking']}  {svc.name}")
        asyncio.create_task(self._run_health_checks())
        self.call_after_refresh(self._activate_selects)

    def _activate_selects(self) -> None:
        self._selects_active = True

    async def _run_health_checks(self) -> None:
        # Run HTTP/TCP probes and llama-server process discovery in parallel.
        probe_tasks = [asyncio.to_thread(_probe, svc) for svc in self._checks]
        proc_task = asyncio.to_thread(find_llama_server_process)

        results = await asyncio.gather(*probe_tasks, proc_task, return_exceptions=True)
        self._llama_proc = results[-1] if isinstance(results[-1], dict) else None

        # Discover models on the filesystem from the process's model dir (or fallback).
        if self._llama_proc:
            models_dir = models_dir_from_process(self._llama_proc)
            self._llama_fs_models = await asyncio.to_thread(discover_models, models_dir)

        self._render_health()

    def _render_health(self) -> None:
        log = self.query_one("#health-log", RichLog)
        log.clear()
        for svc in self._checks:
            log.write(f"  {_STATUS_ICON[svc.status]}  {svc.name:<16} {svc.detail}")
        self._refresh_llm_widgets()

    def _refresh_llm_widgets(self) -> None:
        """Update provider status badge and model dropdown from health check results."""
        svc_map = {s.name: s for s in self._checks}
        ollama = svc_map.get("Ollama")
        llamacpp = svc_map.get("llama.cpp")

        parts = []
        if ollama:
            icon = "[OK]" if ollama.status == "ok" else "[!!]"
            parts.append(f"Ollama {icon}")
        if llamacpp:
            icon = "[OK]" if llamacpp.status == "ok" else "[!!]"
            parts.append(f"llama.cpp {icon}")
        self.query_one("#provider-status", Static).update("  ".join(parts))

        provider = str(self.query_one("#opt-provider", Select).value or "ollama")
        self._set_model_options(provider, svc_map)

    def _set_model_options(self, provider: str, svc_map: dict) -> None:
        """Repopulate the model Select for the chosen provider."""
        model_select = self.query_one("#opt-model", Select)

        if provider == "llamacpp":
            options = self._llamacpp_model_options()
        else:
            # Ollama: use models from health check
            svc = svc_map.get("Ollama")
            api_models = svc.models if svc else []
            if api_models:
                options = [(m, m) for m in api_models]
            else:
                options = _FALLBACK_MODELS

        model_select.set_options(options)
        # Try to keep preferred selection.
        preferred = self._initial.get("llm_model", "")
        available_values = [v for _, v in options]
        if preferred in available_values:
            model_select.value = preferred
        elif available_values:
            model_select.value = available_values[0]

    def _llamacpp_model_options(self) -> list[tuple[str, str]]:
        """
        Build model options for llama.cpp from filesystem-discovered .gguf files.
        Each option value is the full path; the label shows the alias + filename.
        The currently loaded model is marked with (active).
        """
        if not self._llama_fs_models:
            # Fallback: if we have the running process, show its model.
            if self._llama_proc and self._llama_proc.get("model_path"):
                alias = self._llama_proc.get("model_alias") or Path(self._llama_proc["model_path"]).stem
                label = f"{alias}  (active)"
                return [(label, self._llama_proc["model_path"])]
            return _FALLBACK_MODELS

        active_path = (self._llama_proc or {}).get("model_path", "")
        active_alias = (self._llama_proc or {}).get("model_alias", "")
        options: list[tuple[str, str]] = []
        for m in self._llama_fs_models:
            if m["path"] == active_path:
                alias = active_alias or m["stem"]
                label = f"{alias}  [{m['name']}]  (active)"
            else:
                label = f"{m['stem']}  [{m['name']}]"
            options.append((label, m["path"]))
        return options

    def on_select_changed(self, event: Select.Changed) -> None:
        if not self._selects_active:
            return
        if event.select.id == "opt-profile":
            flags = PROFILE_FLAGS.get(str(event.value or ""), {})
            if "read_only" in flags:
                self.query_one("#opt-readonly", Checkbox).value = flags["read_only"]
            if "no_web" in flags:
                self.query_one("#opt-web", Checkbox).value = not flags["no_web"]
            if "enable_rag" in flags:
                self.query_one("#opt-rag", Checkbox).value = flags["enable_rag"]
            if "verbose" in flags:
                self.query_one("#opt-verbose", Checkbox).value = flags["verbose"]
        elif event.select.id == "opt-provider":
            svc_map = {s.name: s for s in self._checks}
            self._set_model_options(str(event.value or "ollama"), svc_map)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-launch":
            self.action_launch()
        elif event.button.id == "btn-cancel":
            self.action_cancel_boot()

    def _collect_flags(self) -> dict[str, Any]:
        read_only = self.query_one("#opt-readonly", Checkbox).value
        web_enabled = self.query_one("#opt-web", Checkbox).value
        rag_enabled = self.query_one("#opt-rag", Checkbox).value
        verbose = self.query_one("#opt-verbose", Checkbox).value
        profile = str(self.query_one("#opt-profile", Select).value or LAUNCH_PROFILES[0][1])
        llm_provider = str(self.query_one("#opt-provider", Select).value or "ollama")
        raw_model_value = str(self.query_one("#opt-model", Select).value or "")
        env = dict(PROFILE_FLAGS.get(profile, {}).get("env", {}))
        if verbose:
            env.setdefault("COCKPIT_LOG_LEVEL", "DEBUG")
            env.setdefault("COCKPIT_VERBOSE_LOGGING", "1")
            env.setdefault("COCKPIT_LOG_TO_STDERR", "1")

        # For llamacpp, raw_model_value is a full .gguf path.
        # Derive the alias (what the API client sends as "model") from the stem.
        if llm_provider == "llamacpp":
            model_path = raw_model_value
            if model_path and model_path.endswith(".gguf"):
                # Use the running process alias if this is the active model.
                if self._llama_proc and self._llama_proc.get("model_path") == model_path:
                    model_alias = self._llama_proc.get("model_alias") or Path(model_path).stem
                else:
                    model_alias = Path(model_path).stem
            else:
                model_path = ""
                model_alias = raw_model_value or "local"
        else:
            model_path = ""
            model_alias = raw_model_value or "llama3:latest"

        return {
            "read_only": read_only,
            "no_web": not web_enabled,
            "enable_rag": rag_enabled,
            "verbose": verbose,
            "profile": profile,
            "llm_provider": llm_provider,
            "llm_model": model_alias,
            "llm_model_path": model_path,
            "env": env,
            "cancelled": False,
        }

    def action_launch(self) -> None:
        flags = self._collect_flags()
        # For llamacpp, check if the selected model differs from what's running.
        if (
            flags["llm_provider"] == "llamacpp"
            and self._llama_proc
            and flags.get("llm_model_path")
            and self._llama_proc.get("model_path") != flags["llm_model_path"]
        ):
            asyncio.create_task(self._restart_and_launch(flags))
            return
        if self._on_launch:
            self._on_launch(flags)

    async def _restart_and_launch(self, flags: dict[str, Any]) -> None:
        """Restart llama-server with the selected model, then launch the cockpit."""
        log = self.query_one("#health-log", RichLog)
        btn = self.query_one("#btn-launch", Button)
        btn.disabled = True

        model_path = flags["llm_model_path"]
        model_alias = flags["llm_model"]

        log.write(f"\n  [ ] Switching to {Path(model_path).name}...")

        def _status(msg: str) -> None:
            self.call_from_thread(log.write, f"  ... {msg}")

        success = await asyncio.to_thread(
            restart_with_model,
            self._llama_proc,
            model_path,
            model_alias,
            90.0,
            _status,
        )

        if success:
            log.write("  [OK] llama-server ready — launching cockpit")
        else:
            log.write("  [!!] Server startup timed out — proceeding anyway")

        btn.disabled = False
        if self._on_launch:
            self._on_launch(flags)

    def action_cancel_boot(self) -> None:
        if self._on_cancel:
            self._on_cancel()


class PreBootApp(App[dict[str, Any]]):
    """
    Standalone terminal wrapper around PreBootScreen.
    Used by cockpit_tui.py for the terminal (non-web) flow.
    Returns flags dict via self.exit().
    """

    CSS = "Screen { background: $background; }"

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

    def on_mount(self) -> None:
        self.push_screen(
            PreBootScreen(
                backend_url=self._backend_url,
                ollama_url=self._ollama_url,
                initial_flags=self._initial,
                on_launch=lambda flags: self.exit(flags),
                on_cancel=lambda: self.exit({"cancelled": True}),
            )
        )
