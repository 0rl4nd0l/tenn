import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "scripts" / "log_change_impact.py"

spec = importlib.util.spec_from_file_location("log_change_impact", str(MOD_PATH))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestLogChangeImpactCli(unittest.TestCase):
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
