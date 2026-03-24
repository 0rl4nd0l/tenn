#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from textual.app import App


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.ui.preboot import (  # noqa: E402
    PreBootScreen,
    _build_service_checks,
    _llamacpp_models_url,
    _llamacpp_provider_label,
)
from scripts.cockpit_tui import _build_preboot_initial_flags, _merge_preboot_flags  # noqa: E402


class _PreBootTestApp(App[None]):
    def __init__(self, initial_flags: dict[str, object]) -> None:
        super().__init__()
        self._initial_flags = initial_flags

    def on_mount(self) -> None:
        self.push_screen(PreBootScreen(initial_flags=self._initial_flags))


class PreBootScreenTests(unittest.IsolatedAsyncioTestCase):
    def test_llamacpp_health_check_uses_effective_configured_url(self) -> None:
        checks = _build_service_checks(
            "http://localhost:8000",
            "http://localhost:11434",
            "http://127.0.0.1:8080",
        )
        llama = next(check for check in checks if check.name == "llama.cpp")
        self.assertEqual(llama.url, "http://127.0.0.1:8080/v1/models")

    def test_llamacpp_health_check_normalizes_v1_suffixes(self) -> None:
        self.assertEqual(_llamacpp_models_url("http://localhost:8080"), "http://localhost:8080/v1/models")
        self.assertEqual(_llamacpp_models_url("http://localhost:8080/v1"), "http://localhost:8080/v1/models")
        self.assertEqual(_llamacpp_models_url("http://localhost:8080/v1/models"), "http://localhost:8080/v1/models")

    def test_provider_label_reflects_configured_port(self) -> None:
        self.assertEqual(_llamacpp_provider_label("http://127.0.0.1:8080"), "llama.cpp  (127.0.0.1:8080)")

    async def test_explicit_initial_flags_survive_profile_initialization(self) -> None:
        initial_flags = {
            "profile": "testing",
            "read_only": False,
            "no_web": False,
            "verbose": False,
        }
        app = _PreBootTestApp(initial_flags)
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.query_one(PreBootScreen)
            self.assertEqual(screen.query_one("#opt-profile").value, "testing")
            self.assertFalse(screen.query_one("#opt-readonly").value)
            self.assertTrue(screen.query_one("#opt-web").value)
            self.assertTrue(screen.query_one("#opt-rag").value)   # default True when not in initial_flags
            self.assertFalse(screen.query_one("#opt-verbose").value)
            self.assertEqual(
                screen._collect_flags(),
                {
                    "read_only": False,
                    "no_web": False,
                    "enable_rag": True,
                    "verbose": False,
                    "profile": "testing",
                    "llm_provider": "llamacpp",
                    "llm_model": "qwen2.5-coder-14b",
                    "llm_model_path": "",
                    "env": {
                        "COCKPIT_LOG_LEVEL": "DEBUG",
                        "COCKPIT_VERBOSE_LOGGING": "1",
                        "COCKPIT_LOG_TO_STDERR": "1",
                        "COCKPIT_CONTEXT_GATHER_TIMEOUT_SECONDS": "15",
                    },
                    "cancelled": False,
                },
            )

    def test_build_preboot_initial_flags_seeds_llm_from_effective_config(self) -> None:
        initial = _build_preboot_initial_flags(REPO_ROOT, ["--config", "config/cockpit.local.yaml"], "config/cockpit.yaml")
        self.assertEqual(initial["llm_provider"], "ollama")
        self.assertEqual(initial["llm_model"], "qwen2.5:32b")

    def test_merge_preboot_flags_exports_llm_choice(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            argv = _merge_preboot_flags(
                [],
                {
                    "profile": "default",
                    "read_only": False,
                    "no_web": False,
                    "llm_provider": "ollama",
                    "llm_model": "qwen2.5:32b",
                    "env": {},
                },
            )
        self.assertEqual(argv, ["--profile", "default"])
        self.assertEqual(os.environ["COCKPIT_LLM_PROVIDER"], "ollama")
        self.assertEqual(os.environ["COCKPIT_LLM_MODEL"], "qwen2.5:32b")


if __name__ == "__main__":
    unittest.main()
