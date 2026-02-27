import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import health_guard as hg


class TestHealthGuard(unittest.TestCase):
    def test_degraded_snapshot_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "health.json"
            path.write_text(json.dumps({"overall_status": "degraded"}), encoding="utf-8")
            snapshot = hg.load_health_snapshot(str(path))
            with self.assertRaises(RuntimeError) as ctx:
                hg.assert_healthy(snapshot, allow_warning=False)
            self.assertIn("system degraded", str(ctx.exception))

    def test_warning_snapshot_blocks_when_not_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "health.json"
            path.write_text(json.dumps({"overall_status": "warning"}), encoding="utf-8")
            snapshot = hg.load_health_snapshot(str(path))
            with self.assertRaises(RuntimeError) as ctx:
                hg.assert_healthy(snapshot, allow_warning=False)
            self.assertIn("warning state", str(ctx.exception))

    def test_warning_snapshot_allowed_when_flag_enabled(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "health.json"
            path.write_text(json.dumps({"overall_status": "warning"}), encoding="utf-8")
            snapshot = hg.load_health_snapshot(str(path))
            hg.assert_healthy(snapshot, allow_warning=True)

    def test_healthy_snapshot_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "health.json"
            path.write_text(json.dumps({"overall_status": "healthy"}), encoding="utf-8")
            snapshot = hg.load_health_snapshot(str(path))
            hg.assert_healthy(snapshot, allow_warning=False)

    def test_missing_file_does_not_block(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "missing_health.json"
            snapshot = hg.load_health_snapshot(str(path))
            self.assertEqual(hg.get_overall_status(snapshot), "missing")
            hg.assert_healthy(snapshot, allow_warning=False)


if __name__ == "__main__":
    unittest.main()
