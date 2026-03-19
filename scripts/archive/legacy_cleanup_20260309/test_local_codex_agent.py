import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "local_codex_agent.py"

spec = importlib.util.spec_from_file_location("local_codex_agent", str(SCRIPT_PATH))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class TestModelSelection(unittest.TestCase):
    def test_extract_available_models(self):
        payload = {
            "models": [
                {"name": "qwen2.5-coder:14b"},
                {"model": "phi3:mini"},
                {"name": " "},
                "invalid",
            ]
        }
        self.assertEqual(mod.extract_available_models(payload), {"qwen2.5-coder:14b", "phi3:mini"})

    def test_select_runtime_model_prefers_requested_when_present(self):
        selected, reason = mod.select_runtime_model(
            "deepseek-coder:6.7b",
            {"deepseek-coder:6.7b", "phi3:mini"},
        )
        self.assertEqual(selected, "deepseek-coder:6.7b")
        self.assertIn("requested", reason)

    def test_select_runtime_model_uses_fallback_when_requested_missing(self):
        selected, reason = mod.select_runtime_model(
            "deepseek-coder:6.7b",
            {"qwen2.5-coder:14b", "phi3:mini"},
        )
        self.assertEqual(selected, "qwen2.5-coder:14b")
        self.assertIn("fallback", reason)

    def test_select_runtime_model_uses_first_installed_as_last_resort(self):
        selected, reason = mod.select_runtime_model(
            "deepseek-coder:6.7b",
            {"custom-model:latest"},
        )
        self.assertEqual(selected, "custom-model:latest")
        self.assertIn("first installed", reason)

    def test_select_runtime_model_without_catalog_keeps_requested(self):
        selected, reason = mod.select_runtime_model("deepseek-coder:6.7b", None)
        self.assertEqual(selected, "deepseek-coder:6.7b")
        self.assertIn("catalog unavailable", reason)

    def test_is_model_not_found_error(self):
        self.assertTrue(mod.is_model_not_found_error(RuntimeError("model 'x' not found")))
        self.assertFalse(mod.is_model_not_found_error(RuntimeError("HTTP 500 internal error")))

    def test_is_retryable_runner_error(self):
        self.assertTrue(mod.is_retryable_runner_error(RuntimeError("llama runner process has terminated: exit status 2")))
        self.assertTrue(mod.is_retryable_runner_error(RuntimeError("timed out waiting for llama runner to start")))
        self.assertFalse(mod.is_retryable_runner_error(RuntimeError("HTTP 404 model not found")))

    def test_build_runtime_model_candidates_with_catalog(self):
        candidates = mod.build_runtime_model_candidates(
            "qwen2.5-coder:14b",
            {"qwen2.5-coder:14b", "phi3:mini"},
        )
        self.assertEqual(candidates, ["qwen2.5-coder:14b", "phi3:mini"])

    def test_build_runtime_model_candidates_without_catalog(self):
        candidates = mod.build_runtime_model_candidates("qwen2.5-coder:14b", None)
        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0], "qwen2.5-coder:14b")
        self.assertIn("phi3:mini", candidates)


class TestToolErrorHandling(unittest.TestCase):
    def test_run_tool_returns_error_for_outside_workspace_path(self):
        with TemporaryDirectory() as td:
            result = mod.run_tool(
                {"tool": "read_file", "path": "/dev/null"},
                workspace=Path(td),
                allow_outside=False,
            )
        self.assertFalse(result.get("ok", True))
        self.assertIn("outside workspace", str(result.get("error", "")))


if __name__ == "__main__":
    unittest.main()
