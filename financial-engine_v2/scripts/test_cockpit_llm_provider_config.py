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
                "provider": "llamacpp",
                "ollama_url": "",
                "llamacpp_url": "http://localhost:8001",
                "model": "qwen2.5-coder-14b",
                "timeout_seconds": 300,
            },
            "db": {},
            "backend": {},
            "rag": {},
        }

    def _flags(self) -> RuntimeFlags:
        return RuntimeFlags(config_path="config/cockpit.yaml", profile="test", read_only=False, no_web=False)

    def test_cockpit_llm_env_overrides_take_precedence(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "COCKPIT_LLM_PROVIDER": "ollama",
                "COCKPIT_OLLAMA_URL": "http://example.invalid:11434",
                "COCKPIT_LLM_MODEL": "phi4:latest",
            },
            clear=False,
        ):
            cfg = apply_runtime_flags(self._base_config(), self._flags())
        self.assertEqual(cfg["llm"]["provider"], "ollama")
        self.assertEqual(cfg["llm"]["ollama_url"], "http://example.invalid:11434")
        self.assertEqual(cfg["llm"]["model"], "phi4:latest")

    def test_invalid_provider_raises(self) -> None:
        with mock.patch.dict(os.environ, {"COCKPIT_LLM_PROVIDER": "anthropic"}, clear=False):
            with self.assertRaises(ValueError):
                apply_runtime_flags(self._base_config(), self._flags())


if __name__ == "__main__":
    unittest.main()
