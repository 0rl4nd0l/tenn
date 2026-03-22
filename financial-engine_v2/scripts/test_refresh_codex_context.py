import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "scripts" / "refresh_codex_context.py"

spec = importlib.util.spec_from_file_location("refresh_codex_context", str(MOD_PATH))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestRefreshCodexContext(unittest.TestCase):
    def test_update_marked_block_replaces_existing_section_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(
                "model = \"gpt-5\"\n\n"
                "# BEGIN TENN_AGENT_CONTEXT\n"
                "old = true\n"
                "# END TENN_AGENT_CONTEXT\n",
                encoding="utf-8",
            )

            mod._update_marked_block(
                config_path,
                mod.CONTEXT_BEGIN_MARKER,
                mod.CONTEXT_END_MARKER,
                "# BEGIN TENN_AGENT_CONTEXT\nnew = true\n# END TENN_AGENT_CONTEXT\n",
            )

            text = config_path.read_text(encoding="utf-8")
            self.assertIn("model = \"gpt-5\"", text)
            self.assertIn("new = true", text)
            self.assertNotIn("old = true", text)

    def test_developer_instructions_block_embeds_prompt_and_digest(self):
        digest = {
            "branch": "feature/test",
            "commit": "abc123",
            "mode": "workspace",
            "changed_files_count": 2,
            "significant_change": True,
            "significance_reasons": ["entrypoint/orchestration changed"],
            "capability_impact": {"runtime_orchestration": 1, "docs_and_governance": 1},
        }

        block = mod._developer_instructions_block(
            "SYSTEM\nUse care.",
            digest,
            ROOT / "codex_prompts" / "tenn-default.md",
        )

        self.assertIn(mod.INSTRUCTIONS_BEGIN_MARKER, block)
        self.assertIn("developer_instructions = '''", block)
        self.assertIn("SYSTEM\nUse care.", block)
        self.assertIn("Current workspace context", block)
        self.assertIn("entrypoint/orchestration changed", block)

    def test_repo_prompt_profiles_exist(self):
        for name in [
            "tenn-default.md",
            "tenn-bug.md",
            "tenn-review.md",
            "tenn-extraction.md",
        ]:
            prompt_path = ROOT / "codex_prompts" / name
            self.assertTrue(prompt_path.exists(), msg=f"missing prompt profile: {name}")
            text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("SYSTEM", text)
            self.assertIn("VALIDATION", text)


if __name__ == "__main__":
    unittest.main()
