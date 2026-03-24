"""CockpitWebApp — combined pre-boot + cockpit app for browser/web delivery.

Shows PreBootScreen first. When the user clicks Launch, applies the chosen
flags, initialises all cockpit services, and transitions to the main UI.

Intended entrypoint: scripts/cockpit_web.py (module-level `app` instance
that `textual serve` or direct `app.run()` can consume).
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from cockpit.core.config import (
    DEFAULT_BACKEND_URL,
    DEFAULT_LLAMACPP_URL,
    DEFAULT_OLLAMA_URL,
    RuntimeFlags,
    apply_runtime_flags,
    load_config,
)
from cockpit.ui.app import CockpitApp
from cockpit.ui.preboot import PreBootScreen


class CockpitWebApp(CockpitApp):
    """Textual app that shows the pre-boot setup screen before the main cockpit.

    Bypasses CockpitApp.__init__ so that service initialisation is deferred
    until after the user has chosen their launch profile and options.
    """

    def __init__(
        self,
        repo_root: Path,
        config_path: str,
        backend_url: str = DEFAULT_BACKEND_URL,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        llamacpp_url: str = DEFAULT_LLAMACPP_URL,
    ) -> None:
        # Bypass CockpitApp.__init__ — _init_services() is called later, after
        # the pre-boot screen collects the user's flags.
        App.__init__(self)
        self._repo_root = repo_root
        self._config_path = config_path
        self._backend_url = backend_url
        self._ollama_url = ollama_url
        self._llamacpp_url = llamacpp_url

        # Sentinel: signals that _init_services() has not yet run.
        self._services_ready = False

        # Attrs normally set by CockpitApp.__init__ — must exist for on_unmount
        # even if services are never initialised (e.g. user cancels at pre-boot).
        self._model_status_timer = None
        self._chat_tasks: set = set()

    # ------------------------------------------------------------------
    # Compose: provide the standard chrome (Header + Footer) up-front so
    # the pre-boot screen renders inside a consistent shell.
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Mount: push the pre-boot screen immediately — all service wiring
    # is deferred until _on_preboot_launch() fires.
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        cfg = load_config(self._config_path)
        cfg = apply_runtime_flags(
            cfg,
            RuntimeFlags(
                config_path=self._config_path,
                profile="default",
                read_only=False,
                no_web=False,
            ),
        )
        llm_cfg = cfg.get("llm", {})
        self.push_screen(
            PreBootScreen(
                backend_url=self._backend_url,
                ollama_url=self._ollama_url,
                llamacpp_url=str(llm_cfg.get("llamacpp_url") or self._llamacpp_url),
                initial_flags={
                    "profile": "default",
                    "read_only": False,
                    "no_web": False,
                    "llm_provider": str(llm_cfg.get("provider") or "llamacpp"),
                    "llm_model": str(llm_cfg.get("model") or "qwen2.5-coder-14b"),
                },
                on_launch=self._on_preboot_launch,
                on_cancel=lambda: self.exit({"cancelled": True}),
            )
        )

    # ------------------------------------------------------------------
    # Pre-boot callback: wires services then transitions to cockpit UI.
    # ------------------------------------------------------------------

    async def _on_preboot_launch(self, flags: dict[str, Any]) -> None:
        """Called when the user clicks Launch on the pre-boot screen.

        Runs as a coroutine so that _init_services (blocking I/O: DB, file
        indexer, qual-context network calls) executes in a thread pool rather
        than on the Textual event loop.  Without this the browser UI stalls
        until service initialisation completes.
        """
        # Apply any env vars chosen by the user (e.g. verbose logging).
        for key, value in flags.get("env", {}).items():
            os.environ[key] = value

        # Load and apply config + runtime flags.
        cfg = load_config(self._config_path)
        cfg = apply_runtime_flags(
            cfg,
            RuntimeFlags(
                config_path=self._config_path,
                profile=flags.get("profile", "full"),
                read_only=flags.get("read_only", False),
                no_web=flags.get("no_web", False),
            ),
        )

        # Apply LLM backend choice from the pre-boot screen.
        llm_provider = flags.get("llm_provider", "ollama")
        llm_model = flags.get("llm_model", "")
        cfg.setdefault("llm", {})
        cfg["llm"]["provider"] = llm_provider
        if llm_model:
            cfg["llm"]["model"] = llm_model

        # Apply RAG/embedding toggle from the pre-boot checkbox.
        # The checkbox is the authoritative control; it overrides any YAML value.
        rag_enabled = bool(flags.get("enable_rag", False))
        cfg.setdefault("rag", {})
        for ctx_key in ("qualitative_context", "news_context"):
            cfg["rag"].setdefault(ctx_key, {})
            cfg["rag"][ctx_key]["enabled"] = rag_enabled

        # Initialise all cockpit services off the event loop so the UI stays
        # responsive during DB init, file indexing, and qual-context setup.
        await asyncio.to_thread(
            self._init_services, self._repo_root, cfg, flags.get("read_only", False)
        )
        self._services_ready = True

        # Pop the pre-boot screen if there is a screen beneath it.
        # In textual serve mode the default screen may not be on the stack
        # (stack=[PreBootScreen] only), so guard against the ScreenStackError
        # that pop_screen() raises when len(stack) <= 1.
        if len(self._screen_stack) > 1:
            self.pop_screen()

        self._finish_mount()

    def _activate_initial_screen(self) -> None:
        """Override: always push chat — PreBootScreen guarantees we want it."""
        try:
            self.push_screen("chat")
        except Exception:
            pass
