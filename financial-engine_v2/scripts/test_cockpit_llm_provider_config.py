#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.config import DEFAULT_LLAMACPP_URL, RuntimeFlags, apply_runtime_flags  # noqa: E402

_COCKPIT_LLM_ALLOW_ENV = """allow_env_override: true
hybrid_router_policy: local_preferred
llm_profile_label: ops
tool_debug: failures
llm:
  provider: llamacpp
  model: qwen2.5-coder-14b
  ollama_url: http://localhost:11434
  router_mode_opt_in: false
"""


class CockpitLlmProviderConfigTests(unittest.TestCase):
    def _base_config(self) -> dict:
        return {
            "llm": {
                "provider": "llamacpp",
                "ollama_url": "",
                "llamacpp_url": "http://localhost:8080",
                "model": "qwen2.5-coder-14b",
                "timeout_seconds": 300,
            },
            "db": {},
            "backend": {},
            "rag": {},
        }

    def _write_allow_env_repo(self) -> Path:
        td = Path(tempfile.mkdtemp())
        (td / "config").mkdir()
        (td / "config" / "cockpit_llm.yaml").write_text(_COCKPIT_LLM_ALLOW_ENV, encoding="utf-8")
        self.addCleanup(lambda: __import__("shutil").rmtree(td, ignore_errors=True))
        return td

    def _flags(self, repo_root: Path) -> RuntimeFlags:
        return RuntimeFlags(
            config_path="config/cockpit.yaml",
            profile="test",
            read_only=False,
            no_web=False,
            repo_root=repo_root,
        )

    def test_cockpit_llm_env_overrides_take_precedence(self) -> None:
        root = self._write_allow_env_repo()
        with mock.patch.dict(
            os.environ,
            {
                "COCKPIT_LLM_PROVIDER": "ollama",
                "COCKPIT_OLLAMA_URL": "http://example.invalid:11434",
                "COCKPIT_LLM_MODEL": "phi4:latest",
            },
            clear=False,
        ):
            cfg = apply_runtime_flags(self._base_config(), self._flags(root))
        self.assertEqual(cfg["llm"]["provider"], "ollama")
        self.assertEqual(cfg["llm"]["ollama_url"], "http://example.invalid:11434")
        self.assertEqual(cfg["llm"]["model"], "phi4:latest")

    def test_invalid_provider_raises(self) -> None:
        root = self._write_allow_env_repo()
        with mock.patch.dict(os.environ, {"COCKPIT_LLM_PROVIDER": "anthropic"}, clear=False):
            with self.assertRaises(ValueError):
                apply_runtime_flags(self._base_config(), self._flags(root))

    def test_llamacpp_url_uses_runtime_env_override(self) -> None:
        root = self._write_allow_env_repo()
        with mock.patch.dict(os.environ, {"LLAMACPP_URL": "http://127.0.0.1:8080"}, clear=False):
            cfg = apply_runtime_flags(self._base_config(), self._flags(root))
        self.assertEqual(cfg["llm"]["llamacpp_url"], "http://127.0.0.1:8080")

    def test_llamacpp_url_falls_back_to_single_default(self) -> None:
        root = self._write_allow_env_repo()
        base = self._base_config()
        base["llm"].pop("llamacpp_url")
        old_ll = os.environ.pop("LLAMACPP_URL", None)
        old_cl = os.environ.pop("COCKPIT_LLAMACPP_URL", None)
        try:
            cfg = apply_runtime_flags(base, self._flags(root))
            self.assertEqual(cfg["llm"]["llamacpp_url"], DEFAULT_LLAMACPP_URL)
        finally:
            if old_ll is not None:
                os.environ["LLAMACPP_URL"] = old_ll
            if old_cl is not None:
                os.environ["COCKPIT_LLAMACPP_URL"] = old_cl


if __name__ == "__main__":
    unittest.main()
