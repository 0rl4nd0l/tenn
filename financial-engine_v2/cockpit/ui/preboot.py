from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
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
from textual.widgets import (
    Button,
    Checkbox,
    Collapsible,
    Label,
    RichLog,
    Select,
    Static,
)

from cockpit.integrations.llamacpp_manager import (
    _extract_arg,
    discover_models,
    discover_ollama_models,
    find_all_llama_server_processes,
    list_models_api,
    models_dir_from_process,
    probe_router_capability,
    resolve_llama_server_topology,
)
from cockpit.ui.help_modal import HelpScreen

from cockpit.core.config import (
    compute_effective_cockpit_config,
    format_llm_backend_tasks_from_cfg,
    llm_task_summary_lines_from_cfg,
    load_env,
    preboot_service_probe_legend,
    verify_chat_model_matches_llamacpp_runtime,
    verify_effective_config_for_preboot,
)


# ---------------------------------------------------------------------------
# Service health probes
# ---------------------------------------------------------------------------


@dataclass
class _ServiceCheck:
    name: str
    url: str  # HTTP URL, or "tcp://host:port" for raw TCP
    status: str = "checking"  # checking | ok | warn | error
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


def _ollama_tags_url(ollama_url: str) -> str:
    base = (ollama_url or "").strip() or "http://localhost:11434"
    if "://" not in base:
        base = f"http://{base}"
    return base.rstrip("/") + "/api/tags"


def _build_service_checks(
    backend_url: str,
    ollama_url: str = "",
    llamacpp_url: str = "http://localhost:8001",
) -> list[_ServiceCheck]:
    backend_health = backend_url.rstrip("/") + "/api/health"
    return [
        _ServiceCheck("Backend API", backend_health),
        _ServiceCheck("llama.cpp", _llamacpp_models_url(llamacpp_url)),
        _ServiceCheck("Ollama", _ollama_tags_url(ollama_url)),
        _ServiceCheck("Qdrant", "http://localhost:6333/readyz"),
        _ServiceCheck("Redis", "tcp://localhost:6379"),
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
    ("Full", "full"),
    ("Testing", "testing"),
]

PROFILE_FLAGS: dict[str, dict[str, Any]] = {
    "full": {
        "read_only": False,
        "no_web": False,
        "verbose": False,
        "enable_rag": True,
        "env": {},
    },
    "testing": {
        "read_only": True,
        "no_web": False,
        "verbose": True,
        "enable_rag": False,
        "env": {
            "COCKPIT_LOG_LEVEL": "DEBUG",
            "COCKPIT_VERBOSE_LOGGING": "1",
            "COCKPIT_LOG_TO_STDERR": "1",
            "COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS": "15",
        },
    },
}


def _resolve_initial_option_state(
    initial_flags: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = dict(initial_flags or {})
    valid_profiles = {value for _, value in LAUNCH_PROFILES}
    profile = raw.get("profile")
    if profile not in valid_profiles:
        profile = LAUNCH_PROFILES[0][1]
    defaults = PROFILE_FLAGS.get(profile, {})
    return {
        "profile": profile,
        "read_only": bool(raw["read_only"])
        if "read_only" in raw
        else bool(defaults.get("read_only", False)),
        "no_web": bool(raw["no_web"])
        if "no_web" in raw
        else bool(defaults.get("no_web", False)),
        "verbose": bool(raw["verbose"])
        if "verbose" in raw
        else bool(defaults.get("verbose", False)),
        "enable_rag": bool(raw["enable_rag"]) if "enable_rag" in raw else True,
        "hybrid_router_policy": raw.get("hybrid_router_policy"),
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
        Binding("?", "show_help", "Help"),
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
    #health-legend {
        height: auto;
        color: $text-muted;
        margin-bottom: 1;
    }
    #health-log { height: 6; }
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
    #llm-backend-section {
        border: round $panel;
        padding: 0 1;
        height: auto;
        margin-bottom: 1;
        width: 1fr;
    }
    #llm-backend-label { text-style: bold; }
    #llm-backend-body { margin-top: 1; height: auto; color: $text; max-height: 22; }
    #llm-runtime-row { height: 3; margin-top: 1; width: 1fr; }
    #llm-runtime-label { width: 28; padding-top: 1; }
    #provider-status { width: 1fr; padding-top: 1; color: $text-muted; }
    #capability-section {
        border: round $success;
        padding: 0 1;
        height: auto;
        margin-bottom: 1;
        width: 1fr;
    }
    #capability-label { text-style: bold; }
    #capability-legend {
        height: auto;
        color: $text-muted;
        margin-bottom: 1;
    }
    #capability-log { height: 14; }
    #btn-row { height: 3; margin-top: 1; margin-bottom: 1; width: 1fr; }
    #btn-spacer { width: 1fr; }
    #btn-cancel { margin-right: 1; width: auto; }
    #btn-repair { margin-right: 1; width: auto; display: none; }
    #btn-repair.-visible { display: block; }
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
        repo_root: Path | None = None,
        config_path: str | None = None,
    ) -> None:
        # Load financial-engine_v2/.env before reading COCKPIT_* / ANTHROPIC_* for defaults.
        load_env(Path(__file__).resolve().parents[2])
        super().__init__()
        self._repo_root = repo_root or Path(__file__).resolve().parents[2]
        rp = (
            Path(config_path)
            if config_path
            else (self._repo_root / "config" / "cockpit.yaml")
        )
        self._config_path = str(rp.resolve())
        self._backend_url = backend_url
        self._ollama_url = ollama_url
        self._llamacpp_url = llamacpp_url
        self._initial = _resolve_initial_option_state(initial_flags)
        self._checks = _build_service_checks(backend_url, ollama_url, llamacpp_url)
        self._on_launch = on_launch
        self._on_cancel = on_cancel
        # Guard: Select fires Changed on mount; block on_select_changed until
        # initial widget values are set and the first refresh has passed.
        self._selects_active = False
        # Same dict pipeline as Launch: load_config(cockpit.yaml) → apply_runtime_flags
        self._effective_cfg: dict[str, Any] | None = None
        self._preboot_config_errors: list[str] = []
        self._runtime_model_mismatch: str | None = None
        self._health_started = False
        # llama.cpp process info + discovered models (populated after health checks).
        self._llama_proc: dict | None = None
        self._llama_fs_models: list[dict] = []
        self._router_capability: dict[str, Any] | None = None
        self._llama_topology: dict[str, Any] | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="preboot-root"):
            yield Label("Cockpit  —  Pre-Boot Setup", id="preboot-title")
            with Vertical(id="health-section"):
                yield Label("Service Health", id="health-label")
                yield Static(preboot_service_probe_legend(), id="health-legend")
                yield RichLog(id="health-log", wrap=False, markup=False, max_lines=12)
            with Vertical(id="capability-section"):
                yield Label("Capabilities & routing preview", id="capability-label")
                yield Static(
                    "Same probe icons as above. Keys: “set” means the variable is present in this process "
                    "(not a guarantee of quota or that the service will succeed).",
                    id="capability-legend",
                )
                yield RichLog(
                    id="capability-log", wrap=False, markup=False, max_lines=20
                )
            with Vertical(id="options-section"):
                yield Label("Launch Options", id="options-label")
                yield Checkbox(
                    "Read-only mode  (block mutating actions)", id="opt-readonly"
                )
                yield Checkbox("Enable web fetch", id="opt-web")
                yield Checkbox(
                    "Enable embedding + RAG  (qualitative_context, news_context)",
                    id="opt-rag",
                )
                yield Checkbox(
                    "Verbose logging  (DEBUG level + stderr)", id="opt-verbose"
                )
                with Horizontal(id="profile-row"):
                    yield Label("Profile:", id="profile-label")
                    yield Select(
                        LAUNCH_PROFILES,
                        value=self._initial.get("profile", LAUNCH_PROFILES[0][1]),
                        id="opt-profile",
                    )
                with Horizontal(id="routing-row"):
                    yield Label(
                        "Routing:", id="profile-label"
                    )  # Use profile-label style for alignment
                    from cockpit.core.config import VALID_HYBRID_ROUTER_POLICIES

                    policy_options = [
                        (p, p) for p in sorted(VALID_HYBRID_ROUTER_POLICIES)
                    ]
                    yield Select(
                        policy_options,
                        id="opt-routing",
                        prompt="Profile policy (YAML default)",
                    )
            with Vertical(id="llm-backend-section"):
                yield Label(
                    "LLM & routing (read-only) — from config/cockpit_llm.yaml + this host",
                    id="llm-backend-label",
                )
                yield Static(
                    "Resolving configuration (load_config → apply_runtime_flags)…",
                    id="llm-backend-body",
                )
                with Horizontal(id="llm-runtime-row"):
                    yield Label("llama.cpp endpoint (probe):", id="llm-runtime-label")
                    yield Static("", id="provider-status")
            with Horizontal(id="btn-row"):
                yield Static("", id="btn-spacer")
                yield Button("Help", id="btn-help", variant="default")
                yield Button("Repair", id="btn-repair", variant="primary")
                yield Button("Cancel", id="btn-cancel", variant="warning")
                yield Button("Launch  [Enter]", id="btn-launch", variant="success")

    def on_mount(self) -> None:
        self.query_one("#opt-readonly", Checkbox).value = self._initial["read_only"]
        self.query_one("#opt-web", Checkbox).value = not self._initial["no_web"]
        self.query_one("#opt-rag", Checkbox).value = self._initial["enable_rag"]
        self.query_one("#opt-verbose", Checkbox).value = self._initial["verbose"]
        if self._initial.get("hybrid_router_policy"):
            try:
                self.query_one("#opt-routing", Select).value = self._initial[
                    "hybrid_router_policy"
                ]
            except Exception:
                pass
        self._sync_effective_config_from_ui()
        log = self.query_one("#health-log", RichLog)
        for svc in self._checks:
            log.write(f"  {_STATUS_ICON['checking']}  {svc.name}")
        self._health_started = True
        asyncio.create_task(self._run_health_checks())
        self.call_after_refresh(self._activate_selects)

    def _activate_selects(self) -> None:
        self._selects_active = True

    def _selected_routing_policy(self) -> str | None:
        try:
            routing_val = self.query_one("#opt-routing", Select).value
        except Exception:
            return None
        if routing_val is None or str(routing_val) == "Select.BLANK":
            return None
        return str(routing_val)

    def _sync_effective_config_from_ui(self) -> None:
        """Recompute the same cfg Launch will use; refresh probes and LLM panel."""
        old_llama, old_ollama = self._llamacpp_url, self._ollama_url
        self._preboot_config_errors = []
        self._effective_cfg = None
        try:
            profile = str(
                self.query_one("#opt-profile", Select).value or LAUNCH_PROFILES[0][1]
            )
            policy = self._selected_routing_policy()
            read_only = self.query_one("#opt-readonly", Checkbox).value
            no_web = not self.query_one("#opt-web", Checkbox).value
            cfg = compute_effective_cockpit_config(
                self._repo_root,
                self._config_path,
                profile=profile,
                read_only=read_only,
                no_web=no_web,
                hybrid_router_policy=policy,
            )
            self._effective_cfg = cfg
            self._preboot_config_errors = verify_effective_config_for_preboot(cfg)
        except FileNotFoundError as exc:
            self._preboot_config_errors = [f"Config file missing: {exc}"]
        except ValueError as exc:
            self._preboot_config_errors = [str(exc)]

        if self._effective_cfg:
            llm = self._effective_cfg.get("llm") or {}
            self._llamacpp_url = str(llm.get("llamacpp_url") or self._llamacpp_url)
            self._ollama_url = str(llm.get("ollama_url") or self._ollama_url)

        urls_changed = (old_llama, old_ollama) != (self._llamacpp_url, self._ollama_url)
        # Only rebuild the checks list when URLs actually changed — otherwise
        # we discard completed probe results and revert icons to "[ ] checking".
        if urls_changed:
            self._checks = _build_service_checks(
                self._backend_url, self._ollama_url, self._llamacpp_url
            )

        self._update_launch_button()
        try:
            self.query_one("#llm-backend-body", Static).update(
                self._format_llm_backend_body()
            )
        except Exception:
            pass

        if urls_changed and self._health_started:
            asyncio.create_task(self._run_health_checks())
        try:
            self._render_capabilities()
        except Exception:
            pass

    def _update_launch_button(self) -> None:
        blocked = bool(self._preboot_config_errors) or bool(
            self._runtime_model_mismatch
        )
        try:
            self.query_one("#btn-launch", Button).disabled = blocked
        except Exception:
            pass

    def _render_capabilities(self) -> None:
        """Fill capability log: keys, service checks, routing preview."""
        log = self.query_one("#capability-log", RichLog)
        log.clear()
        api_ok = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
        brave_ok = bool(os.environ.get("BRAVE_SEARCH_API_KEY", "").strip())
        lines: list[str] = [
            "  How to read this block",
            "    Rows below match Service Health probes (Backend, llama.cpp, Ollama, Qdrant, Redis).",
            "    Anthropic: used when hybrid_router_policy allows API and the agent stack is configured.",
            "    Brave: optional web search; unrelated to local llama.cpp chat.",
            "",
            "  Keys & agents",
            f"    Anthropic:  {'set' if api_ok else 'not set'}  (API key present — enables cloud leg when policy allows)",
            f"    Brave:      {'set' if brave_ok else 'not set'}  (optional web search key)",
            "",
            "  Infrastructure",
        ]
        svc_map = {s.name: s for s in self._checks}
        for name, label in [
            ("Backend API", "Backend API (FastAPI tools / analysis)"),
            ("llama.cpp", "llama.cpp (chat)"),
            ("Ollama", "Ollama (embeddings)"),
            ("Qdrant", "Qdrant"),
            ("Redis", "Redis"),
        ]:
            s = svc_map.get(name)
            if not s:
                continue
            ic = _STATUS_ICON.get(s.status, "[?]")
            lines.append(f"    {ic}  {label}: {s.detail}")
        if self._effective_cfg:
            lines.extend(llm_task_summary_lines_from_cfg(self._effective_cfg))
        else:
            lines.extend(["", "  LLM tasks:  (config not loaded — fix errors below)"])
        if self._preboot_config_errors:
            lines.extend(["", "  Config verification (errors block Launch)"])
            for e in self._preboot_config_errors:
                lines.append(f"    [!!]  {e}")
        if self._runtime_model_mismatch:
            lines.extend(["", "  Runtime verification"])
            lines.append(f"    [!!]  {self._runtime_model_mismatch}")
        log.write("\n".join(lines))

    async def _run_health_checks(self) -> None:
        # Run HTTP/TCP probes and llama-server process discovery in parallel.
        probe_tasks = [asyncio.to_thread(_probe, svc) for svc in self._checks]
        proc_task = asyncio.to_thread(find_all_llama_server_processes)

        results = await asyncio.gather(*probe_tasks, proc_task, return_exceptions=True)
        processes = results[-1] if isinstance(results[-1], list) else []
        topology = resolve_llama_server_topology(processes)
        self._llama_topology = topology.as_dict()
        self._llama_proc = (
            dict(topology.selected_process) if topology.selected_process else None
        )

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
                host = (
                    _extract_arg(self._llama_proc.get("raw_args", []), ("--host",))
                    or "127.0.0.1"
                )
                port = (
                    _extract_arg(self._llama_proc.get("raw_args", []), ("--port",))
                    or "8001"
                )
                api_key = _extract_arg(
                    self._llama_proc.get("raw_args", []), ("--api-key",)
                )
                api_models = await asyncio.to_thread(
                    list_models_api, host, port, api_key
                )
                seen_stems = {m["stem"] for m in merged}
                for am in api_models:
                    if am["name"] not in seen_stems:
                        merged.append(
                            {
                                "path": am["name"],  # router mode uses name, not path
                                "name": am["name"],
                                "stem": am["name"],
                            }
                        )

            self._llama_fs_models = merged

            host = (
                _extract_arg(self._llama_proc.get("raw_args", []), ("--host",))
                or "127.0.0.1"
            )
            port = (
                _extract_arg(self._llama_proc.get("raw_args", []), ("--port",))
                or "8001"
            )
            api_key = _extract_arg(self._llama_proc.get("raw_args", []), ("--api-key",))
            self._router_capability = probe_router_capability(
                self._llama_proc,
                host=host,
                port=port,
                api_key=api_key,
                candidate_processes=processes,
            ).as_dict()
        else:
            self._router_capability = probe_router_capability(
                None,
                candidate_processes=processes,
            ).as_dict()

        self._render_health()
        self._render_capabilities()

    def _router_mode_tag(self) -> str:
        capability = dict(self._router_capability or {})
        topology = dict(self._llama_topology or {})
        if bool(topology.get("ambiguous")):
            reason = str(topology.get("reason") or "").strip().replace("_", " ")
            return f"  (topology blocked: {reason})"
        active_mode = str(capability.get("active_mode") or "").strip()
        if active_mode == "router_mode_active":
            return "  (router active)"
        if active_mode == "router_mode_available_not_active":
            return "  (router available)"
        if active_mode == "router_mode_degraded":
            return "  (router degraded)"
        if active_mode == "router_mode_unavailable":
            return "  (router unavailable)"
        if self._llama_proc:
            return "  (single-model)"
        return ""

    def _topology_blocks_router_mode(self) -> bool:
        topology = dict(self._llama_topology or {})
        return bool(topology.get("ambiguous"))

    def _render_health(self) -> None:
        log = self.query_one("#health-log", RichLog)
        log.clear()
        any_down = False
        active_mode = str((self._router_capability or {}).get("active_mode") or "")
        for svc in self._checks:
            mode_tag = ""
            if svc.name == "llama.cpp":
                mode_tag = self._router_mode_tag()
            log.write(
                f"  {_STATUS_ICON[svc.status]}  {svc.name:<16} {svc.detail}{mode_tag}"
            )
            if svc.status in ("error", "warn") and svc.name in (
                "llama.cpp",
                "Backend API",
            ):
                any_down = True
            # Also treat router_mode_unavailable as "down" — the server
            # process was not found even if the HTTP probe hasn't finished
            # or returned an ambiguous result.
            if svc.name == "llama.cpp" and active_mode == "router_mode_unavailable":
                any_down = True
        self.query_one("#btn-repair", Button).set_class(any_down, "-visible")
        self._refresh_llm_widgets()

    def _probe_runtime_model_note(self) -> str:
        """Append host probe: loaded model when discoverable."""
        if not self._llama_proc:
            return "\n\n--- This host ---\n  llama.cpp process: (none detected)"
        loaded = ""
        if self._llama_proc.get("router_mode") and self._llama_fs_models:
            loaded = self._find_router_loaded_model()
        elif self._llama_proc.get("model_path"):
            loaded = str(self._llama_proc.get("model_path") or "")
        if loaded:
            return f"\n\n--- This host ---\n  Loaded / active on llama.cpp:  {loaded}"
        return "\n\n--- This host ---\n  (loaded model not resolved from probe)"

    def _format_llm_backend_body(self) -> str:
        if not self._effective_cfg:
            err = (
                "\n".join(self._preboot_config_errors)
                if self._preboot_config_errors
                else "Configuration not loaded."
            )
            return f"[!!]  {err}"
        base = format_llm_backend_tasks_from_cfg(
            self._effective_cfg,
            self._repo_root,
            cockpit_config_path=self._config_path,
        )
        extra: list[str] = []
        if self._preboot_config_errors:
            extra.append("")
            extra.append("CONFIG VERIFICATION — Launch disabled until fixed:")
            for e in self._preboot_config_errors:
                extra.append(f"  • {e}")
        if self._runtime_model_mismatch:
            extra.append("")
            extra.append("RUNTIME VERIFICATION — Launch disabled:")
            extra.append(f"  • {self._runtime_model_mismatch}")
        return (
            base
            + ("\n".join(extra) if extra else "")
            + self._probe_runtime_model_note()
        )

    def _refresh_llm_widgets(self) -> None:
        """Refresh read-only LLM task text + llama.cpp probe line; verify loaded model vs cfg."""
        svc_map = {s.name: s for s in self._checks}
        llamacpp = svc_map.get("llama.cpp")
        label = _llamacpp_provider_label(self._llamacpp_url)
        if llamacpp:
            icon = "[OK]" if llamacpp.status == "ok" else "[!!]"
            detail = f"{label}  {llamacpp.detail}  {icon}"
        else:
            detail = f"{label}  [??]"
        self.query_one("#provider-status", Static).update(detail)

        self._runtime_model_mismatch = None
        if (
            self._effective_cfg
            and llamacpp
            and llamacpp.status == "ok"
            and not self._preboot_config_errors
        ):
            loaded = ""
            if (
                self._llama_proc
                and self._llama_proc.get("router_mode")
                and self._llama_fs_models
            ):
                loaded = self._find_router_loaded_model()
            elif self._llama_proc and self._llama_proc.get("model_path"):
                loaded = str(self._llama_proc.get("model_path") or "")
            if loaded:
                self._runtime_model_mismatch = (
                    verify_chat_model_matches_llamacpp_runtime(
                        self._effective_cfg,
                        loaded,
                    )
                )
            # else: probe OK but could not resolve loaded id — do not block (ambiguous topology)
        self._update_launch_button()

        try:
            self.query_one("#llm-backend-body", Static).update(
                self._format_llm_backend_body()
            )
        except Exception:
            pass

    def _find_router_loaded_model(self) -> str:
        """Return the path/name of the currently loaded model in router mode."""
        host = (
            _extract_arg((self._llama_proc or {}).get("raw_args", []), ("--host",))
            or "127.0.0.1"
        )
        port = (
            _extract_arg((self._llama_proc or {}).get("raw_args", []), ("--port",))
            or "8001"
        )
        api_key = _extract_arg(
            (self._llama_proc or {}).get("raw_args", []), ("--api-key",)
        )
        for m in list_models_api(host, port, api_key):
            if m["state"] == "loaded":
                # Match against fs_models by stem name → return the path
                for fm in self._llama_fs_models:
                    if fm["stem"] == m["name"]:
                        return fm["path"]
                return m["name"]
        return ""

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
        elif event.select.id == "opt-routing":
            pass  # Handled by generic _sync_effective_config_from_ui call below
        self._sync_effective_config_from_ui()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id in ("opt-readonly", "opt-web"):
            self._sync_effective_config_from_ui()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-launch":
            self.action_launch()
        elif event.button.id == "btn-help":
            self.action_show_help()
        elif event.button.id == "btn-cancel":
            self.action_cancel_boot()
        elif event.button.id == "btn-repair":
            asyncio.create_task(self._action_repair())

    async def _action_repair(self) -> None:
        """Attempt to start missing critical services (llama.cpp, Backend)."""
        log = self.query_one("#health-log", RichLog)
        svc_map = {s.name: s for s in self._checks}

        btn = self.query_one("#btn-repair", Button)
        btn.disabled = True
        btn.label = "Repairing..."

        if svc_map.get("llama.cpp") and svc_map["llama.cpp"].status != "ok":
            log.write(
                "  [ ]  Repairing llama.cpp: launching scripts/run_llama_server.sh..."
            )
            # Use the project-standard script; it handles port 8001 and respects LLAMA_SERVER_ROUTER_MODE.
            try:
                subprocess.Popen(
                    ["bash", str(self._repo_root / "scripts" / "run_llama_server.sh")],
                    cwd=str(self._repo_root),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                log.write("  [OK]  llama.cpp start command issued.")
            except Exception as exc:
                log.write(f"  [!!]  Failed to launch llama.cpp: {exc}")

        if svc_map.get("Backend API") and svc_map["Backend API"].status != "ok":
            log.write(
                "  [ ]  Repairing Backend API: launching scripts/run_local_backend.sh..."
            )
            # Launch in 'full' profile by default if RAG is enabled, else 'isolated'.
            profile = (
                "full" if self.query_one("#opt-rag", Checkbox).value else "isolated"
            )
            env = dict(os.environ)
            env["LOCAL_BACKEND_PROFILE"] = profile
            try:
                subprocess.Popen(
                    ["bash", "financial-engine_v2/scripts/run_local_backend.sh"],
                    cwd=str(self._repo_root),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                log.write(
                    f"  [OK]  Backend API start command issued (profile={profile})."
                )
            except Exception as exc:
                log.write(f"  [!!]  Failed to launch Backend API: {exc}")

        log.write("  [ ]  Waiting for services to settle before re-probing...")
        await asyncio.sleep(5)

        btn.disabled = False
        btn.label = "Repair"

        # Trigger re-probe
        await self._run_health_checks()

    def _collect_flags(self) -> dict[str, Any]:
        read_only = self.query_one("#opt-readonly", Checkbox).value
        web_enabled = self.query_one("#opt-web", Checkbox).value
        rag_enabled = self.query_one("#opt-rag", Checkbox).value
        verbose = self.query_one("#opt-verbose", Checkbox).value
        profile = str(
            self.query_one("#opt-profile", Select).value or LAUNCH_PROFILES[0][1]
        )
        policy = self._selected_routing_policy()
        env = dict(PROFILE_FLAGS.get(profile, {}).get("env", {}))
        if verbose:
            env.setdefault("COCKPIT_LOG_LEVEL", "DEBUG")
            env.setdefault("COCKPIT_VERBOSE_LOGGING", "1")
            env.setdefault("COCKPIT_LOG_TO_STDERR", "1")

        return {
            "read_only": read_only,
            "no_web": not web_enabled,
            "enable_rag": rag_enabled,
            "verbose": verbose,
            "profile": profile,
            "hybrid_router_policy": policy,
            "env": env,
            "cancelled": False,
        }

    def action_launch(self) -> None:
        self._sync_effective_config_from_ui()
        if self._preboot_config_errors or self._runtime_model_mismatch:
            return
        flags = self._collect_flags()
        if self._on_launch:
            result = self._on_launch(flags)
            if asyncio.iscoroutine(result):
                asyncio.create_task(result)

    def action_cancel_boot(self) -> None:
        if self._on_cancel:
            self._on_cancel()

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen(title="Cockpit Pre-Boot Help"))


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
        rr = Path(__file__).resolve().parents[2]
        self.push_screen(
            PreBootScreen(
                backend_url=self._backend_url,
                ollama_url=self._ollama_url,
                llamacpp_url=self._llamacpp_url,
                repo_root=rr,
                config_path=str((rr / "config" / "cockpit.yaml").resolve()),
                initial_flags=self._initial,
                on_launch=lambda flags: self.exit(flags),
                on_cancel=lambda: self.exit({"cancelled": True}),
            )
        )
