import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "scripts" / "log_change_impact.py"

spec = importlib.util.spec_from_file_location("log_change_impact", str(MOD_PATH))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestLogChangeImpactCli(unittest.TestCase):
    def test_main_rejects_defaults_before_creating_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "change_impact_log.md"
            stdout = io.StringIO()
            with (
                mock.patch.object(mod, "LOG_PATH", log_path),
                mock.patch.object(sys, "argv", [str(MOD_PATH)]),
                mock.patch.object(mod, "_changed_files") as changed_files,
                redirect_stdout(stdout),
            ):
                result = mod.main()

            self.assertEqual(result, 2)
            self.assertFalse(log_path.exists())
            changed_files.assert_not_called()
            self.assertIn("Missing required change-impact fields", stdout.getvalue())

    def test_validate_required_detects_missing(self):
        parser = mod.build_parser()
        args = parser.parse_args([])
        ok, missing = mod._validate_required(args)
        self.assertFalse(ok)
        self.assertIn("scope", missing)

    def test_validate_required_passes_when_supplied(self):
        parser = mod.build_parser()
        args = parser.parse_args(
            [
                "--change-id", "20260223-main-impact",
                "--scope", "backend",
                "--why", "stability",
                "--expected-impact", "better reliability",
                "--validation", "python3 -m unittest",
                "--rollback", "revert commit",
            ]
        )
        ok, missing = mod._validate_required(args)
        self.assertTrue(ok)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
