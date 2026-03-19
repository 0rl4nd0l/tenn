import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = load_module(str(ROOT / "scripts" / "runtime_python.py"), "runtime_python")


class TestRuntimePython(unittest.TestCase):
    def test_resolve_python_prefers_env_var(self):
        with mock.patch.dict("os.environ", {"DOCILING_PYTHON": "/tmp/docling-python"}, clear=True):
            self.assertEqual(RUNTIME.resolve_python(), "/tmp/docling-python")

    def test_resolve_python_falls_back_to_repo_venv_then_python3(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            venv_python = root / ".venv-docling-gpu" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(RUNTIME, "ROOT", root):
                self.assertEqual(RUNTIME.resolve_python(), str(venv_python))

            venv_python.unlink()
            with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(RUNTIME, "ROOT", root):
                self.assertEqual(RUNTIME.resolve_python(), "python3")

    def test_print_runtime_info_emits_selected_interpreter(self):
        stdout = io.StringIO()
        with mock.patch.object(RUNTIME, "resolve_python", return_value="/tmp/docling-python"), redirect_stdout(stdout):
            resolved = RUNTIME.print_runtime_info()

        self.assertEqual(resolved, "/tmp/docling-python")
        self.assertIn("[runtime] using python interpreter: /tmp/docling-python", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
