from __future__ import annotations

import asyncio
import json
import socket
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Label, RichLog, Select, Static

from cockpit.integrations.llamacpp_manager import (
    _extract_arg,
    discover_models,
    discover_ollama_models,
    find_llama_server_process,
    has_no_mmap,
    list_models_api,
    models_dir_from_process,
    restart_into_router_mode,
    restart_with_model,
    switch_model,
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


def _llamacpp_models_url(llamacpp_url: str) -> str:
    base = (llamacpp_url or "").strip() or "http://localhost:8001"
    if "://" not in base:
        base = f"http://{base}"
    base = base.rstrip("/")
    if base.lower().endswith("/v1/models"):
        return base
    if base.lower().endswith("/v1"):
        return f"{base}/models"
    return f"{base}/v1/models"


def _llamacpp_provider_label(llamacpp_url: str) -> str:
    parsed = urlsplit(_llamacpp_models_url(llamacpp_url))
    host = parsed.hostname or "localhost"
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return f"llama.cpp  ({host}:{port})"


def _build_service_checks(
    backend_url: str,
    ollama_url: str = "",  # noqa: ARG001
    llamacpp_url: str = "http://localhost:8001",
) -> list[_ServiceCheck]:
    backend_health = backend_url.rstrip("/") + "/api/health"
    return [
        _ServiceCheck("Backend API",  backend_health),
        _ServiceCheck("llama.cpp",     _llamacpp_models_url(llamacpp_url)),
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
            if svc.name == "llama.cpp":
                try:
                    body = json.loads(resp.read().decode("utf-8"))
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

_FALLBACK_MODELS: list[tuple[str, str]] = [("llama3:latest", "llama3:latest")]


def _resolve_initial_option_state(initial_flags: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(initial_flags or {})
    valid_profiles = {value for _, value in LAUNCH_PROFILES}
    profile = raw.get("profile")
    if profile not in valid_profiles:
        profile = LAUNCH_PROFILES[0][1]
    defaults = PROFILE_FLAGS.get(profile, {})
    llm_provider = raw.get("llm_provider", "llamacpp")
    if llm_provider != "llamacpp":
        llm_provider = "llamacpp"
    return {
        "profile": profile,
        "read_only": bool(raw["read_only"]) if "read_only" in raw else bool(defaults.get("read_only", False)),
        "no_web": bool(raw["no_web"]) if "no_web" in raw else bool(defaults.get("no_web", False)),
        "verbose": bool(raw["verbose"]) if "verbose" in raw else bool(defaults.get("verbose", False)),
        "enable_rag": bool(raw["enable_rag"]) if "enable_rag" in raw else True,
        "llm_provider": llm_provider,
        "llm_model": raw.get("llm_model", "qwen2.5-coder-14b"),
        "extraction_model": raw.get("extraction_model", "qwen2.5-14b-instruct"),
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
    #extraction-row { height: 3; margin-top: 1; width: 1fr; }
    #extraction-label { width: 10; padding-top: 1; }
    #opt-extraction-model { width: 1fr; }
    #mmap-row { height: 3; margin-top: 1; width: 1fr; }
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
        llamacpp_url: str = "http://localhost:8001",
        initial_flags: dict[str, Any] | None = None,
        on_launch: Callable[[dict[str, Any]], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._backend_url = backend_url
        self._ollama_url = ollama_url
        self._llamacpp_url = llamacpp_url
        self._initial = _resolve_initial_option_state(initial_flags)
        self._checks = _build_service_checks(backend_url, ollama_url, llamacpp_url)
        self._provider_options = [(_llamacpp_provider_label(llamacpp_url), "llamacpp")]
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
                    yield Select(self._provider_options, value=self._initial.get("llm_provider", "llamacpp"), id="opt-provider")
                    yield Static("", id="provider-status")
                with Horizontal(id="model-row"):
                    yield Label("Chat:", id="model-label")
                    yield Select(_FALLBACK_MODELS, value="llama3:latest", id="opt-model", allow_blank=False)
                with Horizontal(id="extraction-row"):
                    yield Label("Extract:", id="extraction-label")
                    yield Select(_FALLBACK_MODELS, value="llama3:latest", id="opt-extraction-model", allow_blank=False)
                with Horizontal(id="mmap-row"):
                    yield Checkbox("Load model into RAM  (disable mmap — faster prefill, slower startup)", id="opt-mmap-off", value=True)
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

        if self._llama_proc:
            models_dir = models_dir_from_process(self._llama_proc)
            # Discover local .gguf files and Ollama models in parallel.
            fs_task = asyncio.to_thread(discover_models, models_dir)
            ollama_task = asyncio.to_thread(discover_ollama_models)
            fs_models, ollama_models = await asyncio.gather(fs_task, ollama_task)

            # Merge: filesystem models first, then Ollama models not already listed.
            seen_paths = {m["path"] for m in fs_models}
            merged = list(fs_models)
            for m in ollama_models:
                if m["path"] not in seen_paths:
                    merged.append(m)
                    seen_paths.add(m["path"])

            # In router mode, also include models known to the router API
            # that aren't on the local filesystem (e.g. HuggingFace cached).
            if self._llama_proc.get("router_mode"):
                host = _extract_arg(self._llama_proc.get("raw_args", []), ("--host",)) or "127.0.0.1"
                port = _extract_arg(self._llama_proc.get("raw_args", []), ("--port",)) or "8001"
                api_key = _extract_arg(self._llama_proc.get("raw_args", []), ("--api-key",))
                api_models = await asyncio.to_thread(list_models_api, host, port, api_key)
                seen_stems = {m["stem"] for m in merged}
                for am in api_models:
                    if am["name"] not in seen_stems:
                        merged.append({
                            "path": am["name"],  # router mode uses name, not path
                            "name": am["name"],
                            "stem": am["name"],
                        })

            self._llama_fs_models = merged

        self._render_health()

    def _render_health(self) -> None:
        log = self.query_one("#health-log", RichLog)
        log.clear()
        for svc in self._checks:
            mode_tag = ""
            if svc.name == "llama.cpp" and self._llama_proc:
                mode_tag = "  (router)" if self._llama_proc.get("router_mode") else "  (single-model)"
            log.write(f"  {_STATUS_ICON[svc.status]}  {svc.name:<16} {svc.detail}{mode_tag}")
        self._refresh_llm_widgets()

    def _refresh_llm_widgets(self) -> None:
        """Update provider status badge and model dropdown from health check results."""
        svc_map = {s.name: s for s in self._checks}
        llamacpp = svc_map.get("llama.cpp")
        if llamacpp:
            icon = "[OK]" if llamacpp.status == "ok" else "[!!]"
            self.query_one("#provider-status", Static).update(f"llama.cpp {icon}")
        else:
            self.query_one("#provider-status", Static).update("llama.cpp [??]")
        self._set_model_options("llamacpp", svc_map)

        # Reflect current mmap state from running process.
        if self._llama_proc:
            current_no_mmap = has_no_mmap(self._llama_proc.get("raw_args", []))
            self.query_one("#opt-mmap-off", Checkbox).value = current_no_mmap

    def _set_model_options(self, provider: str, svc_map: dict) -> None:
        """Repopulate chat and extraction model Selects for the llama.cpp runtime."""
        options = self._llamacpp_model_options()
        available_values = [v for _, v in options]

        # --- Chat model dropdown ---
        model_select = self.query_one("#opt-model", Select)
        model_select.set_options(options)
        if available_values:
            active_path = (self._llama_proc or {}).get("model_path", "")
            if active_path in available_values:
                model_select.value = active_path
            else:
                model_select.value = available_values[0]

        # --- Extraction model dropdown ---
        extraction_select = self.query_one("#opt-extraction-model", Select)
        extraction_select.set_options(options)
        if available_values:
            # Auto-select the first instruct model for extraction.
            instruct_match = next(
                (v for v in available_values if "instruct" in str(v).lower()),
                None,
            )
            extraction_select.value = instruct_match or available_values[0]

    def _llamacpp_model_options(self) -> list[tuple[str, str]]:
        """
        Build model options for llama.cpp from filesystem-discovered .gguf files.
        Each option value is the full path; the label shows the alias + filename.
        In router mode, shows load state from the API. In single-model mode,
        marks the currently loaded model with (active).
        """
        if not self._llama_fs_models:
            if self._llama_proc and self._llama_proc.get("model_path"):
                alias = self._llama_proc.get("model_alias") or Path(self._llama_proc["model_path"]).stem
                label = f"{alias}  (active)"
                return [(label, self._llama_proc["model_path"])]
            return _FALLBACK_MODELS

        # In router mode, query the API for per-model load status.
        router_states: dict[str, str] = {}
        if self._llama_proc and self._llama_proc.get("router_mode"):
            host = _extract_arg(self._llama_proc.get("raw_args", []), ("--host",)) or "127.0.0.1"
            port = _extract_arg(self._llama_proc.get("raw_args", []), ("--port",)) or "8001"
            api_key = _extract_arg(self._llama_proc.get("raw_args", []), ("--api-key",))
            for m in list_models_api(host, port, api_key):
                router_states[m["name"]] = m["state"]

        active_path = (self._llama_proc or {}).get("model_path", "")
        active_alias = (self._llama_proc or {}).get("model_alias", "")
        options: list[tuple[str, str]] = []
        for m in self._llama_fs_models:
            stem = m["stem"]
            if router_states:
                state = router_states.get(stem, "available")
                label = f"{stem}  [{m['name']}]  ({state})"
            elif m["path"] == active_path:
                alias = active_alias or stem
                label = f"{alias}  [{m['name']}]  (active)"
            else:
                label = f"{stem}  [{m['name']}]"
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

        # Resolve the selected model into a path and a name (stem/alias).
        # In router mode, the "name" (stem) is what the API uses for routing.
        # In single-model mode, the full path is needed for -m flag replacement.
        if llm_provider == "llamacpp":
            is_router = (self._llama_proc or {}).get("router_mode", False)
            model_info = next((m for m in self._llama_fs_models if m["path"] == raw_model_value), None)

            if model_info:
                model_path = model_info["path"]
                model_alias = model_info["stem"]
            elif raw_model_value.startswith("/"):
                model_path = raw_model_value
                model_alias = Path(raw_model_value).stem
            elif raw_model_value:
                # Router-mode API model (name, not path).
                model_path = raw_model_value
                model_alias = raw_model_value
            else:
                model_path = ""
                model_alias = self._initial.get("llm_model", "local")
        else:
            model_path = ""
            model_alias = raw_model_value or "llama3:latest"

        # Resolve extraction model — same logic but from the extraction Select.
        raw_extraction_value = str(self.query_one("#opt-extraction-model", Select).value or "")
        if llm_provider == "llamacpp":
            ext_info = next((m for m in self._llama_fs_models if m["path"] == raw_extraction_value), None)
            extraction_model = ext_info["stem"] if ext_info else (Path(raw_extraction_value).stem if raw_extraction_value.startswith("/") else raw_extraction_value)
        else:
            extraction_model = raw_extraction_value or model_alias

        # Inject EXTRACT_MODEL into launch env so the backend picks it up
        # automatically — no manual .env editing required.
        if extraction_model:
            env["EXTRACT_MODEL"] = extraction_model

        return {
            "read_only": read_only,
            "no_web": not web_enabled,
            "enable_rag": rag_enabled,
            "verbose": verbose,
            "profile": profile,
            "llm_provider": llm_provider,
            "llm_model": model_alias,
            "llm_model_path": model_path,
            "extraction_model": extraction_model,
            "env": env,
            "cancelled": False,
        }

    def _needs_model_switch(self, flags: dict[str, Any]) -> bool:
        """Check if the selected model differs from the currently active one."""
        if flags["llm_provider"] != "llamacpp" or not self._llama_proc:
            return False

        is_router = self._llama_proc.get("router_mode", False)

        if is_router:
            # In router mode: compare model stem name against loaded models.
            new_name = flags.get("llm_model", "")
            host = _extract_arg(self._llama_proc.get("raw_args", []), ("--host",)) or "127.0.0.1"
            port = _extract_arg(self._llama_proc.get("raw_args", []), ("--port",)) or "8001"
            api_key = _extract_arg(self._llama_proc.get("raw_args", []), ("--api-key",))
            loaded = [m["name"] for m in list_models_api(host, port, api_key) if m["state"] == "loaded"]
            return new_name not in loaded
        else:
            # Single-model mode: compare paths.
            model_changed = (
                flags.get("llm_model_path")
                and self._llama_proc.get("model_path") != flags["llm_model_path"]
            )
            current_no_mmap = has_no_mmap(self._llama_proc.get("raw_args", []))
            mmap_disabled = self.query_one("#opt-mmap-off", Checkbox).value
            mmap_changed = mmap_disabled != current_no_mmap
            return bool(model_changed or mmap_changed)

    def action_launch(self) -> None:
        flags = self._collect_flags()
        if self._needs_model_switch(flags):
            asyncio.create_task(self._switch_and_launch(flags))
            return
        if self._on_launch:
            result = self._on_launch(flags)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

    async def _switch_and_launch(self, flags: dict[str, Any]) -> None:
        """Switch the model (via router API or restart), then launch the cockpit."""
        log = self.query_one("#health-log", RichLog)
        btn = self.query_one("#btn-launch", Button)
        btn.disabled = True

        model_path = flags["llm_model_path"]
        model_name = flags["llm_model"]

        is_router = (self._llama_proc or {}).get("router_mode", False)
        if is_router:
            log.write(f"\n  Hot-switching model → {model_name}  (zero downtime)")
        else:
            log.write(f"\n  Switching model → {model_name}")
            log.write("  (this may take several minutes for large models)")

        host = _extract_arg((self._llama_proc or {}).get("raw_args", []), ("--host",)) or "127.0.0.1"
        port = _extract_arg((self._llama_proc or {}).get("raw_args", []), ("--port",)) or "8001"
        api_key = _extract_arg((self._llama_proc or {}).get("raw_args", []), ("--api-key",))

        def _status(msg: str) -> None:
            self.call_from_thread(log.write, f"  {msg}")

        success = await asyncio.to_thread(
            switch_model,
            self._llama_proc,
            model_name,
            model_path,
            api_key,
            host,
            port,
            600.0,
            _status,
            self.query_one("#opt-mmap-off", Checkbox).value,
        )

        if success:
            log.write(f"  Ready — {model_name} loaded. Launching cockpit...")
        else:
            log.write("  Failed to switch model. Re-enable Launch to retry or pick a different model.")
            btn.disabled = False
            return

        btn.disabled = False
        if self._on_launch:
            result = self._on_launch(flags)
            if asyncio.iscoroutine(result):
                await result

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
        llamacpp_url: str = "http://localhost:8001",
        initial_flags: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self._backend_url = backend_url
        self._ollama_url = ollama_url
        self._llamacpp_url = llamacpp_url
        self._initial = initial_flags or {}

    def on_mount(self) -> None:
        self.push_screen(
            PreBootScreen(
                backend_url=self._backend_url,
                ollama_url=self._ollama_url,
                llamacpp_url=self._llamacpp_url,
                initial_flags=self._initial,
                on_launch=lambda flags: self.exit(flags),
                on_cancel=lambda: self.exit({"cancelled": True}),
            )
        )
