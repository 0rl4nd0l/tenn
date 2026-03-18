#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.config import RuntimeFlags, apply_runtime_flags  # noqa: E402


class CockpitLlmProviderConfigTests(unittest.TestCase):
    def _base_config(self) -> dict:
        return {
            "llm": {
                "provider": "ollama",
                "ollama_url": "http://localhost:11434",
                "openai_base_url": "https://api.openai.com/v1",
                "openai_api_key_env": "OPENAI_API_KEY",
                "model": "llama3:latest",
                "timeout_seconds": 300,
            },
            "db": {},
            "backend": {},
            "rag": {},
        }

    def _flags(self) -> RuntimeFlags:
        return RuntimeFlags(config_path="config/cockpit.yaml", profile="test", read_only=False, no_web=False)

    def test_openai_provider_override(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "COCKPIT_LLM_PROVIDER": "openai",
                "COCKPIT_OPENAI_BASE_URL": "https://example.invalid/v1",
            },
            clear=False,
        ):
            cfg = apply_runtime_flags(self._base_config(), self._flags())
        self.assertEqual(cfg["llm"]["provider"], "openai")
        self.assertEqual(cfg["llm"]["openai_base_url"], "https://example.invalid/v1")

    def test_invalid_provider_raises(self) -> None:
        with mock.patch.dict(os.environ, {"COCKPIT_LLM_PROVIDER": "anthropic"}, clear=False):
            with self.assertRaises(ValueError):
                apply_runtime_flags(self._base_config(), self._flags())


if __name__ == "__main__":
    unittest.main()
