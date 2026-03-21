"""CockpitWebApp — combined pre-boot + cockpit app for browser/web delivery.

Shows PreBootScreen first. When the user clicks Launch, applies the chosen
flags, initialises all cockpit services, and transitions to the main UI.

Intended entrypoint: scripts/cockpit_web.py (module-level `app` instance
that `textual serve` or direct `app.run()` can consume).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from cockpit.core.config import RuntimeFlags, apply_runtime_flags, load_config
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
        backend_url: str = "http://localhost:8000",
        ollama_url: str = "http://localhost:11434",
    ) -> None:
        # Bypass CockpitApp.__init__ — _init_services() is called later, after
        # the pre-boot screen collects the user's flags.
        App.__init__(self)
        self._repo_root = repo_root
        self._config_path = config_path
        self._backend_url = backend_url
        self._ollama_url = ollama_url

        # Sentinel: signals that _init_services() has not yet run.
        self._services_ready = False

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
        self.push_screen(
            PreBootScreen(
                backend_url=self._backend_url,
                ollama_url=self._ollama_url,
                on_launch=self._on_preboot_launch,
                on_cancel=lambda: self.exit({"cancelled": True}),
            )
        )

    # ------------------------------------------------------------------
    # Pre-boot callback: wires services then transitions to cockpit UI.
    # ------------------------------------------------------------------

    def _on_preboot_launch(self, flags: dict[str, Any]) -> None:
        """Called when the user clicks Launch on the pre-boot screen."""
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

        # Initialise all cockpit services now that we have the final config.
        self._init_services(self._repo_root, cfg, flags.get("read_only", False))
        self._services_ready = True

        # Pop the pre-boot screen, then run the standard cockpit mount sequence.
        self.pop_screen()
        self._finish_mount()
