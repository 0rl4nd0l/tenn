import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "local_coding_router.py"

spec = importlib.util.spec_from_file_location("local_coding_router", str(SCRIPT_PATH))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class TestRouteSelection(unittest.TestCase):
    def test_explicit_route(self):
        d = mod.choose_route("any prompt", "deep")
        self.assertEqual(d.route, "deep")
        self.assertIn("explicit", d.reason)

    def test_auto_simple_hint(self):
        d = mod.choose_route("Please summarize and reformat this diff.", "auto")
        self.assertEqual(d.route, "simple")

    def test_auto_deep_hint(self):
        d = mod.choose_route("Need root cause and threat model for this architecture.", "auto")
        self.assertEqual(d.route, "deep")

    def test_auto_long_prompt_defaults_simple(self):
        long_prompt = "x" * 6000
        d = mod.choose_route(long_prompt, "auto")
        self.assertEqual(d.route, "simple")

    def test_auto_short_prompt_defaults_standard(self):
        d = mod.choose_route("Write a Python function that adds two numbers.", "auto")
        self.assertEqual(d.route, "standard")


class TestModelResolution(unittest.TestCase):
    def setUp(self):
        self.model_map = {
            "simple": "qwen2.5-coder:14b",
            "standard": "llama3.1:8b",
            "deep": "qwen2.5:32b",
            "fallback": "phi3:mini",
        }

    def test_resolve_uses_preferred_when_present(self):
        model, reason, effective_route = mod.resolve_model(
            route="simple",
            model_map=self.model_map,
            explicit_model=None,
            available_models={"qwen2.5-coder:14b", "phi3:mini"},
        )
        self.assertEqual(model, "qwen2.5-coder:14b")
        self.assertEqual(effective_route, "simple")
        self.assertIn("preferred", reason)

    def test_resolve_downgrades_when_preferred_missing(self):
        model, reason, effective_route = mod.resolve_model(
            route="deep",
            model_map=self.model_map,
            explicit_model=None,
            available_models={"llama3.1:8b", "phi3:mini"},
        )
        self.assertEqual(model, "llama3.1:8b")
        self.assertEqual(effective_route, "standard")
        self.assertIn("downgraded", reason)

    def test_explicit_model_missing_can_downgrade(self):
        model, reason, effective_route = mod.resolve_model(
            route="simple",
            model_map=self.model_map,
            explicit_model="not-installed:latest",
            available_models={"phi3:mini"},
        )
        self.assertEqual(model, "phi3:mini")
        self.assertEqual(effective_route, "fallback")
        self.assertIn("explicit missing", reason)

    def test_explicit_model_infers_effective_route(self):
        model, _, effective_route = mod.resolve_model(
            route="standard",
            model_map=self.model_map,
            explicit_model="qwen2.5-coder:14b",
            available_models={"qwen2.5-coder:14b"},
        )
        self.assertEqual(model, "qwen2.5-coder:14b")
        self.assertEqual(effective_route, "simple")


class TestFallbackHelpers(unittest.TestCase):
    def setUp(self):
        self.model_map = {
            "simple": "qwen2.5-coder:14b",
            "standard": "llama3.1:8b",
            "deep": "qwen2.5:32b",
            "fallback": "phi3:mini",
        }

    def test_retryable_runner_error_detection(self):
        self.assertTrue(mod.is_retryable_runner_error(RuntimeError("runner process has terminated: exit status 2")))
        self.assertTrue(mod.is_retryable_runner_error(RuntimeError("timed out waiting for llama runner to start")))
        self.assertFalse(mod.is_retryable_runner_error(RuntimeError("HTTP 404 model not found")))

    def test_candidate_chain_includes_selected_then_fallbacks(self):
        chain = mod.build_candidate_chain(
            selected_route="simple",
            selected_model="qwen2.5-coder:14b",
            model_map=self.model_map,
            available_models={"qwen2.5-coder:14b", "phi3:mini"},
            explicit_model=None,
        )
        self.assertEqual(
            chain,
            [
                ("simple", "qwen2.5-coder:14b"),
                ("fallback", "phi3:mini"),
            ],
        )

    def test_candidate_chain_respects_explicit_model(self):
        chain = mod.build_candidate_chain(
            selected_route="simple",
            selected_model="qwen2.5-coder:14b",
            model_map=self.model_map,
            available_models={"qwen2.5-coder:14b", "phi3:mini"},
            explicit_model="qwen2.5-coder:14b",
        )
        self.assertEqual(chain, [("simple", "qwen2.5-coder:14b")])


class TestPayload(unittest.TestCase):
    def test_default_ctx_for_route(self):
        payload = mod.build_payload(
            model="qwen2.5-coder:14b",
            prompt="hi",
            route="simple",
            keep_alive="45m",
            temperature=0.2,
            num_ctx=None,
            num_predict=None,
        )
        self.assertEqual(payload["options"]["num_ctx"], mod.DEFAULT_NUM_CTX["simple"])
        self.assertEqual(payload["options"]["temperature"], 0.2)

    def test_num_ctx_override(self):
        payload = mod.build_payload(
            model="qwen2.5-coder:14b",
            prompt="hi",
            route="simple",
            keep_alive="45m",
            temperature=0.2,
            num_ctx=2048,
            num_predict=128,
        )
        self.assertEqual(payload["options"]["num_ctx"], 2048)
        self.assertEqual(payload["options"]["num_predict"], 128)

    def test_openai_payload_uses_messages(self):
        payload = mod.build_payload(
            model="qwen2.5-coder-14b",
            prompt="hi",
            route="simple",
            keep_alive="45m",
            temperature=0.2,
            num_ctx=2048,
            num_predict=128,
            provider="openai",
        )
        self.assertEqual(payload["model"], "qwen2.5-coder-14b")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "hi"}])
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["max_tokens"], 128)
        self.assertNotIn("options", payload)

    def test_tokens_per_second(self):
        tps = mod.tokens_per_second({"eval_count": 200, "eval_duration": 4_000_000_000})
        self.assertAlmostEqual(tps, 50.0)

    def test_tokens_per_second_openai_returns_none(self):
        self.assertIsNone(mod.tokens_per_second({"usage": {"completion_tokens": 32}}, provider="openai"))


class TestParseArgs(unittest.TestCase):
    def test_parse_args_defaults_to_openai_llamacpp(self):
        args = mod.parse_args(["hello"])
        self.assertEqual(args.provider, "openai")
        self.assertEqual(args.base_url, "http://127.0.0.1:8001/v1")
        self.assertEqual(args.api_key, "local-openai-key")
        self.assertEqual(args.simple_model, "qwen2.5-coder-14b")

    def test_parse_args_ollama_keeps_legacy_defaults(self):
        args = mod.parse_args(["--provider", "ollama", "hello"])
        self.assertEqual(args.provider, "ollama")
        self.assertEqual(args.base_url, "http://127.0.0.1:11434")
        self.assertEqual(args.simple_model, "qwen2.5-coder:14b")
        self.assertEqual(args.api_key, "")


if __name__ == "__main__":
    unittest.main()
