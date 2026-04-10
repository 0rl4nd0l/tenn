import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_real_extraction_eval.py"

spec = importlib.util.spec_from_file_location(
    "run_real_extraction_eval", str(SCRIPT_PATH)
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class TestPersistLocalLlmApiKey(unittest.TestCase):
    def test_preserves_existing_llm_api_key(self):
        with mock.patch.dict(os.environ, {"LLM_API_KEY": "configured-key"}, clear=True):
            with mock.patch.object(mod, "_discover_local_llamacpp_api_key") as detect:
                self.assertEqual(mod._persist_local_llm_api_key(), "configured-key")
                self.assertEqual(os.environ["LLM_API_KEY"], "configured-key")
                detect.assert_not_called()

    def test_ignores_openai_api_key_and_uses_detected_local_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "openai-key"}, clear=True):
            with mock.patch.object(
                mod,
                "_discover_local_llamacpp_api_key",
                return_value="detected-key",
            ) as detect:
                self.assertEqual(mod._persist_local_llm_api_key(), "detected-key")
                self.assertEqual(os.environ["LLM_API_KEY"], "detected-key")
                detect.assert_called_once_with()

    def test_ignores_openai_api_key_and_falls_back_to_default_local_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "openai-key"}, clear=True):
            with mock.patch.object(
                mod, "_discover_local_llamacpp_api_key", return_value=""
            ):
                self.assertEqual(
                    mod._persist_local_llm_api_key(),
                    mod.DEFAULT_LOCAL_LLAMACPP_API_KEY,
                )
                self.assertEqual(
                    os.environ["LLM_API_KEY"],
                    mod.DEFAULT_LOCAL_LLAMACPP_API_KEY,
                )

    def test_uses_detected_local_llama_server_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                mod,
                "_discover_local_llamacpp_api_key",
                return_value="detected-key",
            ):
                self.assertEqual(mod._persist_local_llm_api_key(), "detected-key")
                self.assertEqual(os.environ["LLM_API_KEY"], "detected-key")

    def test_falls_back_to_default_local_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(
                mod, "_discover_local_llamacpp_api_key", return_value=""
            ):
                self.assertEqual(
                    mod._persist_local_llm_api_key(),
                    mod.DEFAULT_LOCAL_LLAMACPP_API_KEY,
                )
                self.assertEqual(
                    os.environ["LLM_API_KEY"],
                    mod.DEFAULT_LOCAL_LLAMACPP_API_KEY,
                )


class TestDiscoverLocalLlamaCppApiKey(unittest.TestCase):
    def test_parses_api_key_from_llama_server_process(self):
        proc = SimpleNamespace(
            stdout=(
                "user 123 0.0 0.0 llama-server --host 0.0.0.0 --port 8001 "
                "--api-key local-openai-key --parallel 1\n"
            )
        )
        with mock.patch.object(mod.subprocess, "run", return_value=proc):
            self.assertEqual(mod._discover_local_llamacpp_api_key(), "local-openai-key")

    def test_returns_empty_string_when_process_scan_fails(self):
        with mock.patch.object(mod.subprocess, "run", side_effect=TimeoutError):
            self.assertEqual(mod._discover_local_llamacpp_api_key(), "")


if __name__ == "__main__":
    unittest.main()
