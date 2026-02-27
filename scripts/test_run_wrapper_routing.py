import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
RUN_PATH = ROOT / "run.py"

spec = importlib.util.spec_from_file_location("root_run", str(RUN_PATH))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestRunWrapperRouting(unittest.TestCase):
    def test_main_delegates_to_engine_run(self):
        with mock.patch("subprocess.run") as run_mock:
            run_mock.return_value.returncode = 0
            rc = mod.main()

        self.assertEqual(rc, 0)
        run_mock.assert_called_once()
        cmd = run_mock.call_args.args[0]
        self.assertTrue(str(cmd[1]).endswith("financial-engine_v2/run.py"))


if __name__ == "__main__":
    unittest.main()
