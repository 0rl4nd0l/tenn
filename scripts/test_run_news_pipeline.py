import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
RUN = load_module(ROOT / "scripts" / "run_news_pipeline.py", "news_pipeline_run_news_pipeline")


class RunNewsPipelineTests(unittest.TestCase):
    def _run_dry(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = RUN.main(argv + ["--dry-run"])
        return rc, buf.getvalue()

    def _parse_payload(self, output: str) -> dict:
        start = output.rfind("\n{")
        if start >= 0:
            payload_text = output[start + 1 :].strip()
        else:
            payload_text = output.strip()
        self.assertTrue(payload_text, "expected payload text")
        return json.loads(payload_text)

    def test_default_run_includes_newspaper4k_collect_step(self):
        rc, output = self._run_dry([])
        self.assertEqual(rc, 0)
        self.assertIn("newspaper4k_collect", output)
        self.assertIn("au_finance_news_orchestrated.jsonl", output)
        payload = self._parse_payload(output)
        step_names = [step.get("step") for step in payload.get("steps", [])]
        self.assertIn("newspaper4k_collect", step_names)

    def test_skip_newspaper4k_disables_default_collect_step(self):
        rc, output = self._run_dry(["--skip-newspaper4k"])
        self.assertEqual(rc, 0)
        self.assertNotIn("newspaper4k_collect", output)
        payload = self._parse_payload(output)
        step_names = [step.get("step") for step in payload.get("steps", [])]
        self.assertNotIn("newspaper4k_collect", step_names)


if __name__ == "__main__":
    unittest.main()
