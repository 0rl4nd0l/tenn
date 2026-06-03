import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConfigApiKeyAliasTests(unittest.TestCase):
    def test_tenn_api_key_env_is_backend_fallback(self):
        env = os.environ.copy()
        env.pop("API_KEY", None)
        env["TENN_API_KEY"] = "alias-key"
        env["PYTHONPATH"] = str(ROOT / "backend")
        code = "from app.core.config import settings; print(settings.api_key)"
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(ROOT),
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "alias-key")


if __name__ == "__main__":
    unittest.main()
